"""English language adapter: spaCy for POS tags, wordfreq for word frequency.

Third-party licences are recorded in docs/tech/third-party-components.md.
"""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Sequence
from itertools import accumulate

import spacy
from wordfreq import zipf_frequency

from app.language.base import CONTENT_POS, Pos, WordAnalysis

SPACY_MODEL = "en_core_web_sm"
WORDFREQ_LANGUAGE = "en"

_POS_VALUES = frozenset(pos.value for pos in Pos)


class EnglishAdapter:
    """LanguageAdapter for English ("eng")."""

    language = "eng"

    # Design choice, not backed by a study: to be adjusted once we know how Scribe
    # actually writes hesitations (docs/tech/elevenlabs-scribe.md, section 9).
    fillers = frozenset({"um", "umm", "uh", "uhh", "uhm", "er", "erm", "hm", "hmm", "mm", "mmm"})

    non_terminal_abbreviations = frozenset({"mr.", "mrs.", "ms.", "dr.", "prof.", "st.", "jr."})

    def __init__(self) -> None:
        # Only the tagger is needed; the parser, NER and lemmatizer are left out.
        self._nlp = spacy.load(SPACY_MODEL, exclude=["parser", "ner", "lemmatizer"])

    def analyse_utterance(self, words: Sequence[str]) -> tuple[WordAnalysis, ...]:
        """Tag one utterance and map spaCy tokens back to the transcribed words."""
        if not words:
            return ()

        # Words are joined by single spaces, so a spaCy token never spans two words:
        # the word a token belongs to is the last one starting at or before the token.
        starts = [0, *accumulate(len(word) + 1 for word in words[:-1])]
        parts: list[list[tuple[Pos, str]]] = [[] for _ in words]
        for token in self._nlp(" ".join(words)):
            if token.is_space:
                continue
            pos = Pos(token.pos_) if token.pos_ in _POS_VALUES else Pos.X
            if pos is not Pos.PUNCT:
                parts[bisect_right(starts, token.idx) - 1].append((pos, token.text))

        return tuple(
            WordAnalysis(
                pos=frozenset(pos for pos, _ in word_parts),
                zipf_frequency=_zipf(word_parts),
            )
            for word_parts in parts
        )


def _zipf(word_parts: Sequence[tuple[Pos, str]]) -> float | None:
    """Zipf frequency of a word, looked up on its content part when it has one.

    "dog's" is looked up as "dog": the possessive form is much rarer in the wordlist
    (Zipf 3.6 against 5.1) although the speaker used a common word.
    """
    if not word_parts:
        return None
    lookup = next((text for pos, text in word_parts if pos in CONTENT_POS), word_parts[0][1])
    value = zipf_frequency(lookup.lower(), WORDFREQ_LANGUAGE)
    # wordfreq returns 0.0 for words that are not in its list.
    return value if value > 0.0 else None
