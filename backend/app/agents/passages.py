"""Passages of a transcript: checking quotes and choosing what to show.

The LLM steps may only quote what the person actually said. A quote is accepted when
its words appear, in the same order, in the tracked speaker's speech. Case and
punctuation are ignored, and so are hesitations the model left out, because models
tend to tidy them away. What is kept and shown is always the transcript's own
wording, never the model's (docs/specs/pipeline.md, steps 2 and 4).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import islice
from typing import Literal

from app.agents.markers import count_immediate_repetitions
from app.agents.segmentation import Utterance, WordKind
from app.language.base import NOUN_POS, LanguageAdapter, Pos

_CURLY_APOSTROPHE = "\u2019"
_WORD = re.compile(r"[^\W_]+(?:['\u2019-][^\W_]+)*")

Reason = Literal["hesitations", "pronouns"]

MIN_DISFLUENCIES = 2
MIN_PRONOUNS = 3
"""An utterance is shown as an example only above these counts (design choices)."""


def _words(text: str) -> list[str]:
    return [word.casefold().replace(_CURLY_APOSTROPHE, "'") for word in _WORD.findall(text)]


class SpokenText:
    """Everything the tracked speaker said, ready for verbatim checks."""

    def __init__(self, utterances: Sequence[Utterance]) -> None:
        self._raw: list[str] = []
        # One entry per token: the token, the position of its word, is it a hesitation.
        self._tokens: list[tuple[str, int, bool]] = []
        for utterance in utterances:
            for word in utterance.words:
                hesitation = word.kind is not WordKind.LEXICAL
                position = len(self._raw)
                self._raw.append(word.raw)
                self._tokens.extend((token, position, hesitation) for token in _words(word.raw))

    def locate(self, passage: str) -> str | None:
        """The transcript's own wording of ``passage``, or None when it was not said.

        The passage must give the person's words in order. It may leave out filled
        pauses and cut-off words, nothing else. The wording returned runs from the
        first to the last matched word, hesitations included.
        """
        wanted = _words(passage)
        if not wanted:
            return None
        for start, (token, first, _) in enumerate(self._tokens):
            if token != wanted[0]:
                continue
            last = self._match_from(start, wanted)
            if last is not None:
                return " ".join(self._raw[first : last + 1])
        return None

    def contains(self, passage: str) -> bool:
        """True when ``passage`` was said, hesitations aside."""
        return self.locate(passage) is not None

    def _match_from(self, start: int, wanted: Sequence[str]) -> int | None:
        """Position of the word that completes the match begun at ``start``, if any."""
        matched = 0
        for token, position, hesitation in islice(self._tokens, start, None):
            if token == wanted[matched]:
                matched += 1
                if matched == len(wanted):
                    return position
            elif not hesitation:
                return None
        return None


@dataclass(frozen=True, slots=True)
class Passage:
    utterance_index: int
    text: str
    reason: Reason


def select_passages(
    utterances: Sequence[Utterance], adapter: LanguageAdapter, *, per_reason: int = 2
) -> tuple[Passage, ...]:
    """Pick, by computation, the utterances that best illustrate the session.

    The most disfluent utterances (hesitations, repetitions, cut-off words), then the
    ones where pronouns most outnumber nouns. The LLM never chooses what to show.
    """
    disfluency: list[tuple[int, Utterance]] = []
    pronouns: list[tuple[int, Utterance]] = []
    for utterance in utterances:
        lexical = utterance.lexical_words
        mazes = sum(word.kind is not WordKind.LEXICAL for word in utterance.words)
        mazes += count_immediate_repetitions([word.form for word in lexical])
        if mazes >= MIN_DISFLUENCIES:
            disfluency.append((mazes, utterance))

        if lexical:
            analyses = adapter.analyse_utterance([word.raw for word in lexical])
            pronoun_count = sum(Pos.PRON in analysis.pos for analysis in analyses)
            noun_count = sum(not NOUN_POS.isdisjoint(analysis.pos) for analysis in analyses)
            if pronoun_count >= MIN_PRONOUNS and pronoun_count > noun_count:
                pronouns.append((pronoun_count - noun_count, utterance))

    by_reason: tuple[tuple[Reason, list[tuple[int, Utterance]]], ...] = (
        ("hesitations", disfluency),
        ("pronouns", pronouns),
    )
    chosen: dict[int, Passage] = {}
    for reason, scored in by_reason:
        # Highest score first; the earliest utterance wins a tie.
        ranked = sorted(scored, key=lambda item: (-item[0], item[1].index))
        fresh = [utterance for _, utterance in ranked if utterance.index not in chosen]
        for utterance in fresh[:per_reason]:
            chosen[utterance.index] = Passage(utterance.index, utterance.text, reason)
    return tuple(chosen[index] for index in sorted(chosen))
