"""Tests for the HTTP API, with a stand-in for Scribe and a scripted model.

The database lives in a temporary folder; background processing runs when the test
client returns, so the status can be read right after a request.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.agents.capture import ScribeTranscription
from app.agents.narrative import EpisodeDraft, NarrativeDraft
from app.agents.transcription import TranscriptionError
from app.api.models import SessionStatus
from app.demo import seed_demo
from app.demo_data import load_sessions
from app.llm import LLMError
from app.main import AppConfig, create_app
from app.schemas import (
    GenerationMode,
    LifePeriod,
    OrientationLevel,
    QualityReason,
    RecordingMetadata,
    RecordingSource,
    TaskType,
)
from app.store import SessionRecord, Store
from tests.llm_doubles import ScriptedLLM

MARGARET = "margaret-hale"


def _scribe(
    person_id: str = "rajesh-menon", number: int = 2, **changes: Any
) -> ScribeTranscription:
    """A Scribe answer taken from a synthetic session."""
    answer = load_sessions(person_id)[number - 1].scribe_response
    return answer.model_copy(update={"transcription_id": "tr-1", **changes})


class FakeTranscriber:
    """Gives its answers in order (the last one is repeated) and records the calls."""

    def __init__(self, *answers: ScribeTranscription | Exception) -> None:
        self._answers = list(answers) or [_scribe()]
        self.calls: list[tuple[str, str | None, int | None]] = []
        self.deleted: list[str] = []

    def transcribe(
        self, audio: Path, *, language: str | None, num_speakers: int | None
    ) -> ScribeTranscription:
        assert audio.exists(), "the audio must still be there while it is transcribed"
        self.calls.append((audio.suffix, language, num_speakers))
        answer = self._answers.pop(0) if len(self._answers) > 1 else self._answers[0]
        if isinstance(answer, Exception):
            raise answer
        return answer

    def delete(self, transcription_id: str) -> None:
        self.deleted.append(transcription_id)


@pytest.fixture(scope="module")
def seeded_db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A database holding Margaret, built once and copied for each test."""
    path = tmp_path_factory.mktemp("seed") / "demo.sqlite3"
    store = Store(path)
    store.initialise()
    seed_demo(store, only={MARGARET})
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    return path


@pytest.fixture
def config(tmp_path: Path, seeded_db: Path) -> AppConfig:
    db_path = tmp_path / "db.sqlite3"
    shutil.copy(seeded_db, db_path)
    return AppConfig(
        db_path=db_path,
        audio_dir=tmp_path / "audio",
        seed_demo=False,
        frontend_dist=None,
        transcriber=FakeTranscriber(),
        llm=None,
    )


@pytest.fixture
def client(config: AppConfig) -> Iterator[TestClient]:
    with TestClient(create_app(config)) as test_client:
        yield test_client


def _new_person(client: TestClient, name: str = "Leila Haddad") -> str:
    response = client.post("/api/people", json={"display_name": name, "birth_year": 1950})
    assert response.status_code == 201, response.text
    person_id: str = response.json()["person_id"]
    return person_id


def _upload(
    client: TestClient, person_id: str, metadata: dict[str, Any] | None = None
) -> dict[str, Any]:
    response = client.post(
        f"/api/people/{person_id}/sessions",
        files={"audio": ("recording.webm", b"opus bytes", "audio/webm")},
        data={"metadata": json.dumps(metadata or {"consent": True, "prompt_id": "first_job"})},
    )
    assert response.status_code == 202, response.text
    body: dict[str, Any] = response.json()
    return body


def _status(client: TestClient, session_id: str) -> dict[str, Any]:
    body: dict[str, Any] = client.get(f"/api/sessions/{session_id}/status").json()
    return body


# --- People -----------------------------------------------------------------


def test_list_puts_the_people_who_need_attention_first(client: TestClient) -> None:
    newcomer = _new_person(client)

    rows = client.get("/api/people").json()

    assert [row["person_id"] for row in rows] == [MARGARET, newcomer]
    margaret, new = rows
    assert margaret["orientation_level"] == "review_recommended"
    assert (margaret["session_count"], margaret["baseline_session_count"]) == (10, 5)
    assert margaret["synthetic"] and margaret["age"] == datetime.now(UTC).year - 1948
    assert new["orientation_level"] == "building_baseline"
    assert (new["session_count"], new["last_session_at"]) == (0, None)


@pytest.mark.parametrize(
    ("body", "problem"),
    [
        ({"display_name": "Amira", "language": "fra"}, "not supported yet"),
        ({"display_name": ""}, "string_too_short"),
        ({"display_name": "Amira", "birth_year": 1800}, "greater_than_equal"),
    ],
)
def test_person_creation_is_checked(client: TestClient, body: dict[str, Any], problem: str) -> None:
    response = client.post("/api/people", json=body)

    assert response.status_code == 422
    assert problem in response.text


def test_person_detail_of_a_persona(client: TestClient) -> None:
    detail = client.get(f"/api/people/{MARGARET}").json()

    orientation = detail["orientation"]
    assert orientation["level"] == "review_recommended"
    assert orientation["rule_text"] and orientation["action_text"]
    assert orientation["uncertainty"]["baseline_session_count"] == 5
    points = detail["trajectory"]["points"]
    assert len(points) == 10
    assert all(point["comparison"] is not None for point in points)
    assert {spec["marker"] for spec in detail["trajectory"]["marker_specs"]} >= {
        "maze_index",
        "speech_rate_wpm",
    }
    assert detail["latest_summary"]["session_id"] == "margaret-hale-s10"
    assert detail["sessions"][0]["theme"] == "Childhood home"
    genomic = next(e for e in detail["risk_profile"]["entries"] if e["factor"] == "Genomic data")
    assert genomic == {"factor": "Genomic data", "value": None, "shared": False}
    assert client.get(f"/api/people/{MARGARET}/trajectory").json() == detail["trajectory"]


def test_unknown_ids_are_not_found(client: TestClient) -> None:
    assert client.get("/api/people/nobody").status_code == 404
    assert client.get("/api/sessions/nothing").status_code == 404
    assert client.get("/api/sessions/nothing/status").status_code == 404
    assert client.get("/api/prompts", params={"person_id": "nobody"}).status_code == 404


# --- A new session ----------------------------------------------------------


def test_new_session_goes_through_the_pipeline_and_its_audio_is_deleted(
    client: TestClient, config: AppConfig
) -> None:
    person_id = _new_person(client)

    accepted = _upload(client, person_id)

    session_id = accepted["session_id"]
    assert accepted["status_url"] == f"/api/sessions/{session_id}/status"
    assert _status(client, session_id) == {
        "session_id": session_id,
        "status": "done",
        "step": "Done",
        "error": None,
    }
    transcriber = config.transcriber
    assert isinstance(transcriber, FakeTranscriber)
    # Two voices in a consultation; the person's language; then the copy is deleted.
    assert transcriber.calls == [(".webm", "eng", 2)]
    assert transcriber.deleted == ["tr-1"]
    assert list(config.audio_dir.iterdir()) == []

    detail = client.get(f"/api/sessions/{session_id}").json()
    assert detail["session"]["theme"] == "First job"
    assert detail["metadata"]["source"] == "clinician_ui"
    assert detail["quality"]["status"] == "usable"
    assert detail["metrics"] is not None
    # A first session only starts the personal baseline: fixed wording, no model.
    assert detail["comparison"]["orientation"]["level"] == "building_baseline"
    assert detail["summary"]["generation_mode"] == "template"
    turns = detail["transcript"]["turns"]
    assert any(turn["is_tracked_speaker"] for turn in turns)
    assert any(not turn["is_tracked_speaker"] for turn in turns)
    kinds = {item["kind"] for turn in turns for item in turn["items"]}
    assert {"word", "filler", "pause"} <= kinds


def test_session_of_a_followed_person_runs_the_model_steps(config: AppConfig) -> None:
    episode = EpisodeDraft(
        episode_id="e1",
        summary="He describes a working day.",
        life_period=LifePeriod.MIDDLE_ADULTHOOD,
        people=[],
        places=[],
        time_references=[],
        utterance_indices=[0, 1],
    )
    # Step 2 answers; step 4 cannot reach the model and falls back to the fixed wording.
    config.llm = ScriptedLLM(
        NarrativeDraft(episodes=[episode], repetitions=[]), LLMError("down"), model_id="m-1"
    )
    with TestClient(create_app(config)) as client:
        session_id = _upload(client, MARGARET)["session_id"]

        detail = client.get(f"/api/sessions/{session_id}").json()

    assert detail["narrative"]["model_id"] == "m-1"
    assert detail["narrative"]["episodes"][0]["summary"] == "He describes a working day."
    assert detail["comparison"]["orientation"]["level"] != "building_baseline"
    assert detail["summary"]["generation_mode"] == GenerationMode.TEMPLATE_FALLBACK.value
    assert detail["metadata"]["synthetic"] is True  # a persona's sessions stay marked


def test_session_without_consent_is_refused(client: TestClient) -> None:
    person_id = _new_person(client)

    response = client.post(
        f"/api/people/{person_id}/sessions",
        files={"audio": ("recording.webm", b"opus bytes", "audio/webm")},
        data={"metadata": json.dumps({"consent": False})},
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["metadata", "consent"]
    assert client.get(f"/api/people/{person_id}").json()["sessions"] == []


def test_empty_audio_is_refused(client: TestClient) -> None:
    person_id = _new_person(client)

    response = client.post(
        f"/api/people/{person_id}/sessions",
        files={"audio": ("recording.webm", b"", "audio/webm")},
        data={"metadata": json.dumps({"consent": True})},
    )

    assert response.status_code == 422


def test_failed_transcription_keeps_the_audio_until_a_retry(config: AppConfig) -> None:
    down = TranscriptionError("Scribe returned status 503")
    config.transcriber = FakeTranscriber(down, down, _scribe())
    with TestClient(create_app(config)) as client:
        person_id = _new_person(client)
        session_id = _upload(client, person_id)["session_id"]

        failed = _status(client, session_id)
        kept = list(config.audio_dir.iterdir())
        retried = client.post(f"/api/sessions/{session_id}/retry")
        done = _status(client, session_id)
        again = client.post(f"/api/sessions/{session_id}/retry")

    assert failed["status"] == "failed"
    assert failed["error"] == "transcription: Scribe returned status 503"
    assert len(kept) == 1
    assert retried.status_code == 202
    assert done["status"] == "done"
    assert list(config.audio_dir.iterdir()) == []
    assert again.status_code == 409


def test_session_heard_in_another_language_is_rejected(config: AppConfig) -> None:
    config.transcriber = FakeTranscriber(_scribe(language_code="fra"))
    with TestClient(create_app(config)) as client:
        session_id = _upload(client, _new_person(client))["session_id"]

        detail = client.get(f"/api/sessions/{session_id}").json()

    assert detail["session"]["status"] == "rejected"
    assert detail["quality"]["reasons"] == [QualityReason.LANGUAGE_MISMATCH.value]
    assert (detail["comparison"], detail["summary"]) == (None, None)
    assert detail["transcript"] is not None


def test_without_transcription_no_session_is_accepted(config: AppConfig) -> None:
    config.transcriber = None
    with TestClient(create_app(config)) as client:
        response = client.post(
            f"/api/people/{MARGARET}/sessions",
            files={"audio": ("recording.webm", b"opus bytes", "audio/webm")},
            data={"metadata": json.dumps({"consent": True})},
        )

    assert response.status_code == 503


def test_session_interrupted_by_a_restart_is_marked_failed(config: AppConfig) -> None:
    store = Store(config.db_path)
    store.add_session(
        SessionRecord(
            session_id="s-stuck",
            metadata=RecordingMetadata(
                person_id=MARGARET,
                task_type=TaskType.LIFE_STORY,
                language="eng",
                consent=True,
                recorded_at=datetime.now(UTC),
                source=RecordingSource.CLINICIAN_UI,
            ),
            status=SessionStatus.TRANSCRIBING,
            created_at=datetime.now(UTC),
        )
    )

    with TestClient(create_app(config)) as client:
        status = _status(client, "s-stuck")

    assert status["status"] == "failed"
    assert status["error"].startswith("interrupted")


# --- Review and prompts -----------------------------------------------------


def test_clinician_validates_the_latest_summary_once(client: TestClient) -> None:
    response = client.post(
        f"/api/people/{MARGARET}/summary/review", json={"reviewed_by": "Dr Amal Nasser"}
    )

    assert response.status_code == 200
    review = response.json()["review"]
    assert (review["status"], review["reviewed_by"]) == ("validated", "Dr Amal Nasser")
    assert client.get(f"/api/people/{MARGARET}").json()["latest_summary"]["review"] == review
    again = client.post(f"/api/people/{MARGARET}/summary/review", json={"reviewed_by": "X"})
    assert again.status_code == 409
    newcomer = _new_person(client)
    missing = client.post(f"/api/people/{newcomer}/summary/review", json={"reviewed_by": "X"})
    assert missing.status_code == 404


def test_prompt_is_a_theme_never_asked_then_the_oldest(client: TestClient) -> None:
    detail = client.get(f"/api/people/{MARGARET}").json()
    asked = [s["prompt_id"] for s in detail["sessions"]]
    bank = json.loads(Path("data/prompts.json").read_text())["prompts"]
    never = [p["id"] for p in bank if p["id"] not in asked]

    prompt = client.get("/api/prompts", params={"person_id": MARGARET}).json()
    oldest = client.get(
        "/api/prompts", params=[("person_id", MARGARET), *(("exclude", p) for p in never)]
    ).json()

    assert never and prompt["prompt_id"] in never
    assert prompt["follow_ups"] == ["What happened next?", "Can you tell me more about that?"]
    assert oldest["prompt_id"] == asked[0]


# --- Integration ------------------------------------------------------------


def _integration_upload(client: TestClient, key: str | None) -> Any:
    metadata = {
        "source_app": "mymemoires",
        "external_person_id": "mm-42",
        "language": "eng",
        "consent": True,
        "recorded_at": "2026-11-14T09:00:00+04:00",
        "display_name": "Samir Khoury",
    }
    return client.post(
        "/api/integrations/recordings",
        files={"audio": ("memory.m4a", b"aac bytes", "audio/mp4")},
        data={"metadata": json.dumps(metadata)},
        headers={} if key is None else {"X-Integration-Key": key},
    )


def test_integration_is_closed_without_a_configured_key(client: TestClient) -> None:
    assert _integration_upload(client, "anything").status_code == 503


def test_integration_creates_the_person_once_and_processes_recordings(config: AppConfig) -> None:
    config.integration_key = "shared-secret"
    with TestClient(create_app(config)) as client:
        refused = [_integration_upload(client, key).status_code for key in (None, "wrong")]
        first = _integration_upload(client, "shared-secret")
        second = _integration_upload(client, "shared-secret")
        people = [
            p for p in client.get("/api/people").json() if p["display_name"] == "Samir Khoury"
        ]
        detail = client.get(f"/api/sessions/{first.json()['session_id']}").json()

    assert refused == [401, 401]
    assert (first.status_code, second.status_code) == (202, 202)
    (person,) = people
    assert person["session_count"] == 2
    assert detail["metadata"]["source"] == "integration"
    assert detail["session"]["status"] == "done"
    transcriber = config.transcriber
    assert isinstance(transcriber, FakeTranscriber)
    # An integration does not say how many voices it holds.
    assert transcriber.calls[0] == (".m4a", "eng", None)


# --- Demo data --------------------------------------------------------------


def test_persona_texts_come_from_the_snapshot_only_when_the_level_still_matches(
    tmp_path: Path,
) -> None:
    from app.demo import LLMSnapshot, load_snapshot

    # A snapshot made of fixed wordings, presented as model texts, with one mistake.
    store = Store(tmp_path / "plain.sqlite3")
    store.initialise()
    seed_demo(store, only={MARGARET}, snapshot_root=tmp_path / "none")
    ids = [s.session_id for s in store.sessions_of(MARGARET)]
    plain = store.summaries_of(ids)
    as_model = {
        sid: report.model_copy(update={"generation_mode": GenerationMode.LLM, "model_id": "m-1"})
        for sid, report in plain.items()
    }
    # Session 10 gets the summary of session 4, written for another level.
    as_model["margaret-hale-s10"] = as_model["margaret-hale-s04"].model_copy(
        update={"session_id": "margaret-hale-s10"}
    )
    snapshot = LLMSnapshot(
        synthetic=True,
        person_id=MARGARET,
        generated_at=datetime.now(UTC),
        narratives=(),
        summaries=tuple(as_model.values()),
    )
    root = tmp_path / "snapshot"
    root.mkdir()
    (root / f"{MARGARET}.json").write_text(snapshot.model_dump_json())
    assert load_snapshot(MARGARET, root) == snapshot

    seeded = Store(tmp_path / "seeded.sqlite3")
    seeded.initialise()
    seed_demo(seeded, only={MARGARET}, snapshot_root=root)
    summaries = seeded.summaries_of(ids)

    assert summaries["margaret-hale-s09"].generation_mode is GenerationMode.LLM
    assert summaries["margaret-hale-s10"].generation_mode is GenerationMode.TEMPLATE_FALLBACK
    assert summaries["margaret-hale-s10"].orientation_level is OrientationLevel.REVIEW_RECOMMENDED


# --- Built interface --------------------------------------------------------


def test_built_interface_is_served_outside_the_api(config: AppConfig, tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>ChronoVoice</html>")
    (dist / "assets" / "app.js").write_text("console.log('app')")
    (dist / "favicon.svg").write_text("<svg/>")
    config.frontend_dist = dist
    with TestClient(create_app(config)) as client:
        page = client.get("/people/margaret-hale")
        asset = client.get("/assets/app.js")
        icon = client.get("/favicon.svg")
        api_miss = client.get("/api/unknown")
        escape = client.get("/..%2F..%2Fetc%2Fpasswd")

    assert (page.status_code, page.text) == (200, "<html>ChronoVoice</html>")
    assert asset.text == "console.log('app')"
    assert icon.text == "<svg/>"
    assert api_miss.status_code == 404
    assert escape.text == "<html>ChronoVoice</html>"
