"""Step 0 of the pipeline, after transcription: transcript and quality control.

The call to ElevenLabs Scribe itself needs the network and an API key and lives
elsewhere. This module is the deterministic part of step 0 (docs/specs/pipeline.md):
it turns a Scribe response into a SessionTranscript, picks the tracked speaker and
decides whether the session is usable, partial or rejected.

Scribe response format: docs/tech/elevenlabs-scribe.md, section 4.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence
from math import log
from statistics import fmean
from typing import Literal

import langcodes
from pydantic import BaseModel, ConfigDict

from app.agents.segmentation import WordKind, segment_target_speech, speaking_time_s
from app.language.base import LanguageAdapter
from app.schemas import (
    QualityReason,
    QualityReport,
    QualityStatus,
    RecordingMetadata,
    SessionTranscript,
    TokenKind,
    TranscriptToken,
)

MIN_LEXICAL_WORDS = 150
"""Below this, a session is partial: minimum sample cited by Mueller et al. 2018 (note 08)."""

MIN_SPEAKING_TIME_S = 120.0
"""Below this, a session is partial. Design choice validated on 2026-11-12 (Q33),
not backed by a study; Petti et al. 2023 found 5-minute samples better than 1-minute ones."""

MIN_MEAN_LOGPROB = log(0.5)
"""Below this mean word confidence (50 %), a session is partial.
PROVISIONAL: to be calibrated on real Scribe output (elevenlabs-scribe.md, section 9)."""

DEFAULT_SPEAKER = "speaker_0"
UNDETERMINED_LANGUAGE = "und"


class ScribeWord(BaseModel):
    """One item of the ``words`` array of a Scribe response."""

    model_config = ConfigDict(extra="ignore")

    text: str
    type: Literal["word", "spacing", "audio_event"]
    start: float | None = None
    end: float | None = None
    speaker_id: str | None = None
    logprob: float | None = None


class ScribeTranscription(BaseModel):
    """The fields of a Scribe transcription that ChronoVoice uses."""

    model_config = ConfigDict(extra="ignore")

    language_code: str
    language_probability: float
    text: str
    words: list[ScribeWord]
    transcription_id: str | None = None
    audio_duration_secs: float | None = None


def build_transcript(
    session_id: str, metadata: RecordingMetadata, scribe: ScribeTranscription
) -> SessionTranscript:
    """Keep the timed words and audio events of a Scribe response, in time order.

    Scribe ``spacing`` items are dropped: they do not cover the silences between
    words (elevenlabs-scribe.md, section 5).
    """
    tokens = sorted(
        (
            TranscriptToken(
                text=item.text.strip(),
                kind=TokenKind.WORD if item.type == "word" else TokenKind.AUDIO_EVENT,
                start_s=item.start,
                end_s=max(item.end, item.start),
                speaker_id=item.speaker_id or DEFAULT_SPEAKER,
                logprob=None if item.logprob is None else min(item.logprob, 0.0),
            )
            for item in scribe.words
            if item.type != "spacing"
            and item.start is not None
            and item.end is not None
            and item.text.strip()
        ),
        key=lambda token: token.start_s,
    )
    return SessionTranscript(
        session_id=session_id,
        person_id=metadata.person_id,
        synthetic=metadata.synthetic,
        language=_iso_639_3(scribe.language_code),
        language_probability=min(max(scribe.language_probability, 0.0), 1.0),
        audio_duration_s=scribe.audio_duration_secs or max((t.end_s for t in tokens), default=0.0),
        target_speaker_id=_target_speaker(tokens, metadata.target_speaker_hint),
        tokens=tuple(tokens),
    )


def assess_quality(
    transcript: SessionTranscript, metadata: RecordingMetadata, adapter: LanguageAdapter
) -> QualityReport:
    """Classify a session as usable, partial or rejected (docs/specs/pipeline.md, step 0)."""
    turns = segment_target_speech(transcript, adapter)
    lexical_words = sum(word.kind is WordKind.LEXICAL for turn in turns for word in turn.words)
    speaking_time = speaking_time_s(turns)

    words = [token for token in transcript.tokens if token.kind is TokenKind.WORD]
    target_words = [t for t in words if t.speaker_id == transcript.target_speaker_id]
    confidences = [t.logprob for t in target_words if t.logprob is not None]
    mean_logprob = fmean(confidences) if confidences else None

    rejection = [
        reason
        for reason, failed in (
            (QualityReason.NO_TARGET_SPEECH, lexical_words == 0),
            (QualityReason.LANGUAGE_MISMATCH, transcript.language != metadata.language),
        )
        if failed
    ]
    partial = [
        reason
        for reason, failed in (
            (QualityReason.TOO_FEW_WORDS, lexical_words < MIN_LEXICAL_WORDS),
            (QualityReason.TOO_SHORT, speaking_time < MIN_SPEAKING_TIME_S),
            (
                QualityReason.LOW_CONFIDENCE,
                mean_logprob is not None and mean_logprob < MIN_MEAN_LOGPROB,
            ),
        )
        if failed
    ]

    if rejection:
        status, reasons = QualityStatus.REJECTED, rejection
    elif partial:
        status, reasons = QualityStatus.PARTIAL, partial
    else:
        status, reasons = QualityStatus.USABLE, []

    return QualityReport(
        session_id=transcript.session_id,
        person_id=transcript.person_id,
        synthetic=transcript.synthetic,
        status=status,
        reasons=tuple(reasons),
        target_word_count=lexical_words,
        target_speaking_time_s=speaking_time,
        target_speech_share=len(target_words) / len(words) if words else 0.0,
        mean_logprob=mean_logprob,
    )


def _target_speaker(tokens: Sequence[TranscriptToken], hint: str | None) -> str | None:
    """The speaker to analyse: the integration's hint, else whoever says the most words.

    In a consultation the person speaks far more than the clinician (design choice
    validated on 2026-11-12, Q34). Ties go to the speaker heard first.
    """
    word_counts = Counter(t.speaker_id for t in tokens if t.kind is TokenKind.WORD)
    if not word_counts:
        return None
    if hint in word_counts:
        return hint
    return word_counts.most_common(1)[0][0]


def _iso_639_3(code: str) -> str:
    """Scribe gives "en" or "eng" depending on the endpoint: always return three letters."""
    try:
        return langcodes.Language.get(code).to_alpha3()
    except (LookupError, ValueError):
        code = code.strip().lower()
        return code if re.fullmatch(r"[a-z]{3}", code) else UNDETERMINED_LANGUAGE
