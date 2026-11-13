"""The committed demo personas, run through the real pipeline (steps 0, 1 and 3).

These tests lock the story told in the demo (docs/specs/synthetic-data.md): if a
change in the pipeline moves a persona off its designed trajectory, they fail.
"""

from __future__ import annotations

import json
from datetime import timedelta
from functools import cache
from itertools import pairwise

import pytest

from app.agents.drift import compare_trajectory
from app.demo_data import (
    DATA_ROOT,
    SyntheticSession,
    analyse_sessions,
    load_personas,
    load_sessions,
)
from app.schemas import (
    AnalysedSession,
    LongitudinalComparisonResult,
    MarkerFamily,
    QualityReason,
    QualityStatus,
)
from scripts.generate_synthetic_data import generate_all

PERSONAS = ("margaret-hale", "rajesh-menon", "grace-santos")

BUILDING = ("building_baseline", "insufficient_baseline")
STABLE = ("stable", "not_significant")
EXPECTED_LEVELS = {
    # Baseline of 5 sessions, then a progressive decline from session 6.
    "margaret-hale": [
        *[BUILDING] * 3,
        *[STABLE] * 3,
        ("monitor", "single_significant"),
        *[("review_recommended", "persistent_two_sessions")] * 3,
    ],
    "rajesh-menon": [*[BUILDING] * 3, *[STABLE] * 7],
    # Session 7 is cut short after a poor night: partial, so the level is carried over.
    "grace-santos": [
        *[BUILDING] * 3,
        *[STABLE] * 3,
        ("stable", "carried_over"),
        *[STABLE] * 3,
    ],
}


@cache
def _sessions(person_id: str) -> tuple[SyntheticSession, ...]:
    return load_sessions(person_id)


@cache
def _analysed(person_id: str) -> tuple[AnalysedSession, ...]:
    return tuple(analysed for _, analysed in analyse_sessions(_sessions(person_id)))


@cache
def _trajectory(person_id: str) -> tuple[LongitudinalComparisonResult, ...]:
    return compare_trajectory(_analysed(person_id))


def test_committed_files_are_what_the_generator_produces() -> None:
    generated = generate_all()

    assert len(generated) == 30
    for path, content in generated.items():
        assert path.read_text() == content, f"{path.name} is out of date: regenerate the data"


def test_three_personas_with_their_profiles() -> None:
    personas = load_personas()

    assert tuple(p.person_id for p in personas) == PERSONAS
    for persona in personas:
        assert persona.risk_profile.synthetic
        genomic = next(e for e in persona.risk_profile.entries if e.factor == "Genomic data")
        assert (genomic.shared, genomic.value) == (False, None)


@pytest.mark.parametrize("person_id", PERSONAS)
def test_ten_synthetic_sessions_two_weeks_apart(person_id: str) -> None:
    sessions = _sessions(person_id)
    dates = [s.metadata.recorded_at for s in sessions]
    prompts = {p["id"] for p in json.loads((DATA_ROOT / "prompts.json").read_text())["prompts"]}

    assert len(sessions) == 10
    assert all(s.synthetic and s.metadata.synthetic for s in sessions)
    assert all(s.metadata.person_id == person_id and s.metadata.consent for s in sessions)
    assert {later - earlier for earlier, later in pairwise(dates)} == {timedelta(days=14)}
    assert dates[0].date().isoformat() == "2026-06-29"
    assert dates[-1].date().isoformat() == "2026-11-02"
    # A different theme at every session, all from the shared prompt bank.
    themes = [s.metadata.prompt_id for s in sessions]
    assert len(set(themes)) == 10
    assert set(themes) <= prompts


@pytest.mark.parametrize("person_id", PERSONAS)
def test_persona_follows_its_designed_trajectory(person_id: str) -> None:
    levels = [(r.orientation.level.value, r.orientation.rule.value) for r in _trajectory(person_id)]

    assert levels == EXPECTED_LEVELS[person_id]


def test_sessions_are_about_five_minutes_of_usable_speech() -> None:
    for person_id in PERSONAS:
        for analysed in _analysed(person_id):
            if analysed.quality.status is not QualityStatus.USABLE:
                continue
            assert 560 <= analysed.quality.target_word_count <= 680
            assert 230 <= analysed.quality.target_speaking_time_s <= 330
            assert analysed.quality.target_speech_share > 0.95


def test_margaret_declines_in_both_marker_families() -> None:
    last = _trajectory("margaret-hale")[-1]

    assert last.change_index is not None
    assert last.baseline is not None
    assert len(last.baseline.session_ids) == 5
    assert len(last.change_index.significant_markers) >= 4
    scores = {f.family: f.value for f in last.family_scores}
    assert scores[MarkerFamily.SEMANTIC] > 2
    assert scores[MarkerFamily.FLUENCY] > 2


def test_margaret_retells_the_same_anecdote_in_her_last_three_sessions() -> None:
    told = ["bird" in s.scribe_response.text for s in _sessions("margaret-hale")]

    # First told in session 3 (the wooden sparrow), then retold in sessions 8, 9 and 10.
    assert [number for number, bird in enumerate(told, start=1) if bird][-3:] == [8, 9, 10]
    assert "sparrow" in _sessions("margaret-hale")[2].scribe_response.text


def test_grace_has_one_partial_session_after_a_poor_night() -> None:
    analysed = _analysed("grace-santos")
    partial = [a for a in analysed if a.quality.status is not QualityStatus.USABLE]

    assert [a.session_id for a in partial] == ["grace-santos-s07"]
    (session,) = partial
    assert session.quality.status is QualityStatus.PARTIAL
    assert set(session.quality.reasons) == {
        QualityReason.TOO_FEW_WORDS,
        QualityReason.TOO_SHORT,
        QualityReason.LOW_CONFIDENCE,
    }
    assert session.metadata.context.is_adverse
    # The partial session never joins the personal baseline.
    last = _trajectory("grace-santos")[-1]
    assert last.baseline is not None
    assert "grace-santos-s07" not in last.baseline.session_ids


def test_rajesh_never_leaves_his_usual_range() -> None:
    tested = [r for r in _trajectory("rajesh-menon") if r.change_index is not None]

    assert len(tested) == 7
    assert all(len(r.change_index.significant_markers) < 2 for r in tested if r.change_index)
