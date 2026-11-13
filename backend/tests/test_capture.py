"""Tests for the deterministic part of step 0: transcript building and quality control."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from app.agents.capture import (
    MIN_LEXICAL_WORDS,
    ScribeTranscription,
    assess_quality,
    build_transcript,
)
from app.agents.pipeline import analyse_transcription
from app.schemas import (
    QualityReason,
    QualityStatus,
    RecordingMetadata,
    RecordingSource,
    TaskType,
    TokenKind,
)
from tests.transcripts import StubAdapter

ADAPTER = StubAdapter({})


def _metadata(**overrides: Any) -> RecordingMetadata:
    fields: dict[str, Any] = {
        "person_id": "p-1",
        "task_type": TaskType.LIFE_STORY,
        "language": "eng",
        "consent": True,
        "recorded_at": datetime(2026, 11, 13, 10, 0, tzinfo=UTC),
        "source": RecordingSource.CLINICIAN_UI,
        "synthetic": True,
    }
    fields.update(overrides)
    return RecordingMetadata.model_validate(fields)


def _item(
    text: str,
    start: float,
    end: float,
    speaker: str | None = "speaker_0",
    kind: str = "word",
    logprob: float | None = -0.05,
) -> dict[str, Any]:
    return {
        "text": text,
        "start": start,
        "end": end,
        "type": kind,
        "speaker_id": speaker,
        "logprob": logprob,
    }


def _scribe(*items: dict[str, Any], language: str = "en") -> ScribeTranscription:
    return ScribeTranscription.model_validate(
        {
            "language_code": language,
            "language_probability": 0.98,
            "text": " ".join(item["text"] for item in items),
            "words": list(items),
            "transcription_id": "tr-1",
            "unknown_field": "ignored",
        }
    )


def _monologue(word_count: int, *, word_s: float = 0.5, gap_s: float = 0.3, logprob: float = -0.05):
    """The clinician asks a question, then the person says ``word_count`` words."""
    question = [_item("Tell", 0.0, 0.2, "speaker_1"), _item("me.", 0.3, 0.5, "speaker_1")]
    step = word_s + gap_s
    answer = [
        _item(f"word{i}", 1.0 + i * step, 1.0 + i * step + word_s, logprob=logprob)
        for i in range(word_count)
    ]
    return _scribe(*question, *answer)


# --- Transcript -------------------------------------------------------------


def test_spacing_items_are_dropped_and_language_is_three_letters() -> None:
    # Shape of the example in the ElevenLabs documentation.
    scribe = _scribe(
        _item("With", 0.119, 0.259),
        _item(" ", 0.239, 0.299, kind="spacing"),
        _item("a", 0.279, 0.359),
        _item(" ", 0.339, 0.499, kind="spacing"),
        _item("soft", 0.479, 1.039),
    )

    transcript = build_transcript("s-1", _metadata(), scribe)

    assert [t.text for t in transcript.tokens] == ["With", "a", "soft"]
    assert transcript.language == "eng"
    assert (transcript.session_id, transcript.person_id, transcript.synthetic) == (
        "s-1",
        "p-1",
        True,
    )
    assert transcript.audio_duration_s == pytest.approx(1.039)


@pytest.mark.parametrize(
    ("code", "expected"), [("en", "eng"), ("eng", "eng"), ("fr", "fra"), ("??", "und")]
)
def test_language_codes_are_normalised(code: str, expected: str) -> None:
    transcript = build_transcript(
        "s-1", _metadata(), _scribe(_item("Hi.", 0.0, 0.3), language=code)
    )

    assert transcript.language == expected


def test_tracked_speaker_is_the_one_who_says_the_most_words() -> None:
    scribe = _scribe(
        _item("Tell", 0.0, 0.2, "speaker_0"),
        _item("me.", 0.3, 0.5, "speaker_0"),
        _item("We", 1.0, 1.1, "speaker_1"),
        _item("left", 1.2, 1.4, "speaker_1"),
        _item("early.", 1.5, 1.9, "speaker_1"),
    )

    assert build_transcript("s-1", _metadata(), scribe).target_speaker_id == "speaker_1"


def test_integration_can_name_the_tracked_speaker() -> None:
    scribe = _scribe(
        _item("Yes.", 0.0, 0.3, "speaker_0"),
        _item("We", 1.0, 1.1, "speaker_1"),
        _item("left.", 1.2, 1.4, "speaker_1"),
    )
    hinted = _metadata(target_speaker_hint="speaker_0")
    unknown = _metadata(target_speaker_hint="speaker_9")

    assert build_transcript("s-1", hinted, scribe).target_speaker_id == "speaker_0"
    assert build_transcript("s-1", unknown, scribe).target_speaker_id == "speaker_1"


def test_audio_events_are_kept_and_tokens_sorted() -> None:
    scribe = _scribe(
        _item("left.", 1.2, 1.4),
        _item("(laughs)", 0.4, 0.9, kind="audio_event"),
        _item("We", 0.0, 0.2),
        _item("untimed", 0.0, 0.0) | {"start": None},
    )

    transcript = build_transcript("s-1", _metadata(), scribe)

    assert [(t.text, t.kind) for t in transcript.tokens] == [
        ("We", TokenKind.WORD),
        ("(laughs)", TokenKind.AUDIO_EVENT),
        ("left.", TokenKind.WORD),
    ]


def test_recording_without_diarisation_has_a_single_speaker() -> None:
    scribe = _scribe(_item("We", 0.0, 0.2, speaker=None), _item("left.", 0.3, 0.6, speaker=None))

    transcript = build_transcript("s-1", _metadata(), scribe)

    assert transcript.target_speaker_id == "speaker_0"


def test_recording_without_words_has_no_tracked_speaker() -> None:
    scribe = _scribe(_item("(music)", 0.0, 5.0, kind="audio_event"))

    assert build_transcript("s-1", _metadata(), scribe).target_speaker_id is None


# --- Quality control --------------------------------------------------------


def _quality(scribe: ScribeTranscription, **metadata: Any):
    meta = _metadata(**metadata)
    return assess_quality(build_transcript("s-1", meta, scribe), meta, ADAPTER)


def test_long_confident_session_is_usable() -> None:
    # 160 words of 0.5 s every 0.8 s: 159 * 0.8 + 0.5 = 127.7 s of speaking time.
    report = _quality(_monologue(160))

    assert (report.status, report.reasons) == (QualityStatus.USABLE, ())
    assert report.target_word_count == 160
    assert report.target_speaking_time_s == pytest.approx(127.7)
    assert report.target_speech_share == pytest.approx(160 / 162)
    assert report.mean_logprob == pytest.approx(-0.05)


def test_too_few_words_makes_a_session_partial() -> None:
    # 149 words spread over more than two minutes.
    report = _quality(_monologue(MIN_LEXICAL_WORDS - 1, gap_s=0.5))

    assert (report.status, report.reasons) == (
        QualityStatus.PARTIAL,
        (QualityReason.TOO_FEW_WORDS,),
    )


def test_less_than_two_minutes_makes_a_session_partial() -> None:
    # 160 words in 159 * 0.5 + 0.3 = 79.8 s.
    report = _quality(_monologue(160, word_s=0.3, gap_s=0.2))

    assert (report.status, report.reasons) == (QualityStatus.PARTIAL, (QualityReason.TOO_SHORT,))


def test_low_transcription_confidence_makes_a_session_partial() -> None:
    report = _quality(_monologue(160, logprob=-1.2))

    assert (report.status, report.reasons) == (
        QualityStatus.PARTIAL,
        (QualityReason.LOW_CONFIDENCE,),
    )


def test_session_without_speech_from_the_person_is_rejected() -> None:
    report = _quality(_scribe(_item("(music)", 0.0, 5.0, kind="audio_event")))

    assert report.status is QualityStatus.REJECTED
    assert QualityReason.NO_TARGET_SPEECH in report.reasons
    assert report.target_speech_share == 0.0


def test_unexpected_language_is_rejected() -> None:
    report = _quality(_monologue(160, gap_s=0.5), language="fra")

    assert (report.status, report.reasons) == (
        QualityStatus.REJECTED,
        (QualityReason.LANGUAGE_MISMATCH,),
    )


# --- Steps 0 and 1 together -------------------------------------------------


def test_usable_session_gets_markers() -> None:
    transcript, analysed = analyse_transcription("s-1", _metadata(), _monologue(160), ADAPTER)

    assert analysed.quality.status is QualityStatus.USABLE
    assert analysed.metrics is not None
    assert analysed.metrics.session_id == transcript.session_id == "s-1"


def test_rejected_session_gets_no_markers() -> None:
    _, analysed = analyse_transcription("s-1", _metadata(language="fra"), _monologue(160), ADAPTER)

    assert analysed.quality.status is QualityStatus.REJECTED
    assert analysed.metrics is None
