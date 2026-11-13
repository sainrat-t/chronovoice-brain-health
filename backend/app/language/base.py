"""Language adapter contract.

Everything that depends on the language of the recording sits behind a
LanguageAdapter, so that markers stay language-agnostic (CLAUDE.md, product
decisions of 2026-11-12; docs/specs/pipeline.md, step 1).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class Pos(StrEnum):
    """Universal POS tags, identical across languages (universaldependencies.org/u/pos)."""

    ADJ = "ADJ"
    ADP = "ADP"
    ADV = "ADV"
    AUX = "AUX"
    CCONJ = "CCONJ"
    DET = "DET"
    INTJ = "INTJ"
    NOUN = "NOUN"
    NUM = "NUM"
    PART = "PART"
    PRON = "PRON"
    PROPN = "PROPN"
    PUNCT = "PUNCT"
    SCONJ = "SCONJ"
    SYM = "SYM"
    VERB = "VERB"
    X = "X"


NOUN_POS = frozenset({Pos.NOUN, Pos.PROPN})
"""Tags counted as nouns by the markers (docs/specs/pipeline.md, step 1)."""

CONTENT_POS = frozenset({Pos.NOUN, Pos.VERB, Pos.ADJ, Pos.ADV})
"""Tags of content words. Proper nouns are left out: their frequency reflects the
person's life, not their vocabulary (design choice, not backed by a study)."""


@dataclass(frozen=True, slots=True)
class WordAnalysis:
    """Language-specific analysis of one transcribed word.

    A transcribed word may be split by the tagger ("I'm" -> "I" + "'m"): ``pos`` holds
    the tags of all its parts, punctuation excluded.
    """

    pos: frozenset[Pos]
    zipf_frequency: float | None
    """Frequency on the Zipf scale (about 1 = very rare, 8 = very common); None if unknown."""


class LanguageAdapter(Protocol):
    """What step 1 needs to know about a language."""

    @property
    def language(self) -> str:
        """ISO 639-3 code of the language handled by this adapter."""
        ...

    @property
    def fillers(self) -> frozenset[str]:
        """Lowercase filled pauses ("um", "uh"...), counted in the maze index only."""
        ...

    @property
    def non_terminal_abbreviations(self) -> frozenset[str]:
        """Lowercase abbreviations whose final period does not end an utterance ("dr.")."""
        ...

    def analyse_utterance(self, words: Sequence[str]) -> tuple[WordAnalysis, ...]:
        """Analyse the words of one utterance, as transcribed (case and punctuation kept).

        Returns exactly one WordAnalysis per input word, in the same order.
        """
        ...
