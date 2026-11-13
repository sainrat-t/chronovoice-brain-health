"""Turns, utterances and words of the tracked speaker.

Shared by step 1 (markers), step 2 (narrative analyst) and the session detail view.
Definitions: docs/specs/pipeline.md, step 1, "Découpage".
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from app.language.base import LanguageAdapter
from app.schemas import SessionTranscript, TokenKind, TranscriptToken


class WordKind(StrEnum):
    LEXICAL = "lexical"
    """Counted by every marker."""
    FILLER = "filler"
    """Filled pause ("um"): counted in the maze index only."""
    CUT_OFF = "cut_off"
    """Word left unfinished ("w-"), the trace of a false start: maze index only."""


@dataclass(frozen=True, slots=True)
class SpokenWord:
    """One word said by the tracked speaker."""

    raw: str
    """As transcribed, with its case and punctuation."""
    form: str
    """Lowercase, without surrounding punctuation."""
    kind: WordKind
    start_s: float
    end_s: float
    after_audio_event: bool
    """A non-speech sound (laugh, cough) came just before: the gap is not silence."""
    ends_utterance: bool


@dataclass(frozen=True, slots=True)
class Utterance:
    index: int
    """Position among the tracked speaker's utterances in the session, from 0."""
    words: tuple[SpokenWord, ...]

    @property
    def lexical_words(self) -> tuple[SpokenWord, ...]:
        return tuple(word for word in self.words if word.kind is WordKind.LEXICAL)


@dataclass(frozen=True, slots=True)
class Turn:
    """Words of the tracked speaker with no word from anyone else in between."""

    utterances: tuple[Utterance, ...]

    @property
    def words(self) -> tuple[SpokenWord, ...]:
        return tuple(word for utterance in self.utterances for word in utterance.words)


_EDGE_PUNCTUATION = re.compile(r"^[\W_]+|[\W_]+$")
_CURLY_APOSTROPHE = "\u2019"
# Sentence-final punctuation, possibly followed by closing quotes or brackets.
_SENTENCE_END = re.compile(r"""[.?!]["'\u201d\u2019)\]]*$""")
# A letter followed by a hyphen, then nothing but punctuation: "w-", "w-,".
# How Scribe writes false starts is still to be checked (elevenlabs-scribe.md, section 9).
_CUT_OFF = re.compile(r"[^\W\d_]-[\W_]*$")


def segment_target_speech(
    transcript: SessionTranscript, adapter: LanguageAdapter
) -> tuple[Turn, ...]:
    """Split the tracked speaker's speech into turns, utterances and words."""
    target = transcript.target_speaker_id
    if target is None:
        return ()

    turns: list[Turn] = []
    current: list[SpokenWord] = []
    utterance_count = 0
    audio_event_pending = False

    def close_turn() -> None:
        nonlocal utterance_count
        if current:
            utterances = _split_utterances(current, first_index=utterance_count)
            utterance_count += len(utterances)
            turns.append(Turn(utterances=utterances))
            current.clear()

    for token in transcript.tokens:
        if token.kind is TokenKind.AUDIO_EVENT:
            audio_event_pending = True
        elif token.speaker_id != target:
            close_turn()
            audio_event_pending = False
        else:
            word = _spoken_word(token, adapter, after_audio_event=audio_event_pending)
            if word is not None:
                current.append(word)
                audio_event_pending = False
    close_turn()
    return tuple(turns)


def speaking_time_s(turns: Sequence[Turn]) -> float:
    """Sum, over turns, of the time from the first to the last word (fillers included)."""
    return sum(turn.words[-1].end_s - turn.words[0].start_s for turn in turns)


def _spoken_word(
    token: TranscriptToken, adapter: LanguageAdapter, *, after_audio_event: bool
) -> SpokenWord | None:
    """Build a SpokenWord, or None for a token with no letter or digit."""
    form = _EDGE_PUNCTUATION.sub("", token.text).casefold().replace(_CURLY_APOSTROPHE, "'")
    if not form:
        return None

    if form in adapter.fillers:
        kind = WordKind.FILLER
    elif _CUT_OFF.search(token.text):
        kind = WordKind.CUT_OFF
    else:
        kind = WordKind.LEXICAL

    ends_utterance = (
        _SENTENCE_END.search(token.text) is not None
        and f"{form}." not in adapter.non_terminal_abbreviations
    )
    return SpokenWord(
        raw=token.text,
        form=form,
        kind=kind,
        start_s=token.start_s,
        end_s=token.end_s,
        after_audio_event=after_audio_event,
        ends_utterance=ends_utterance,
    )


def _split_utterances(words: list[SpokenWord], *, first_index: int) -> tuple[Utterance, ...]:
    """Cut the words of one turn after each sentence end; the turn end closes the last one."""
    utterances: list[Utterance] = []
    start = 0
    for position, word in enumerate(words):
        if word.ends_utterance or position == len(words) - 1:
            utterances.append(
                Utterance(
                    index=first_index + len(utterances), words=tuple(words[start : position + 1])
                )
            )
            start = position + 1
    return tuple(utterances)
