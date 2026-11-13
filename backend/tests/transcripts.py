"""Test helpers: hand-written transcripts and a language adapter with a fixed lexicon."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from app.language.base import Pos, WordAnalysis
from app.schemas import SessionTranscript, TokenKind, TranscriptToken

PERSON = "speaker_0"
CLINICIAN = "speaker_1"


def word(text: str, start: float, end: float, speaker: str = PERSON) -> TranscriptToken:
    return TranscriptToken(
        text=text, kind=TokenKind.WORD, start_s=start, end_s=end, speaker_id=speaker
    )


def event(text: str, start: float, end: float, speaker: str = PERSON) -> TranscriptToken:
    return TranscriptToken(
        text=text, kind=TokenKind.AUDIO_EVENT, start_s=start, end_s=end, speaker_id=speaker
    )


def transcript(
    *tokens: TranscriptToken, target: str | None = PERSON, language: str = "eng"
) -> SessionTranscript:
    return SessionTranscript(
        session_id="s-1",
        person_id="p-1",
        synthetic=True,
        language=language,
        language_probability=0.99,
        audio_duration_s=max((token.end_s for token in tokens), default=0.0),
        target_speaker_id=target,
        tokens=tokens,
    )


def evenly_spaced_words(forms: Sequence[str]) -> SessionTranscript:
    """One turn of the person: each word lasts 0.2 s, with 0.1 s between words."""
    return transcript(
        *(word(form, 0.3 * i, 0.3 * i + 0.2) for i, form in enumerate(forms)),
    )


class StubAdapter:
    """English-like adapter whose tags and frequencies come from a hand-written lexicon."""

    language = "eng"
    fillers = frozenset({"um", "uh"})
    non_terminal_abbreviations = frozenset({"dr."})

    def __init__(self, lexicon: Mapping[str, tuple[frozenset[Pos], float | None]]) -> None:
        self._lexicon = lexicon

    def analyse_utterance(self, words: Sequence[str]) -> tuple[WordAnalysis, ...]:
        return tuple(
            WordAnalysis(*self._lexicon.get(_form(raw), (frozenset(), None))) for raw in words
        )


def _form(raw: str) -> str:
    return re.sub(r"^\W+|\W+$", "", raw).lower()
