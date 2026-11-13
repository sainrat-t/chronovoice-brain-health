"""Tests for the English adapter, run against the real spaCy model and wordfreq list."""

from __future__ import annotations

import pytest
from wordfreq import zipf_frequency

from app.agents.markers import compute_session_metrics
from app.language import UnsupportedLanguageError, get_adapter
from app.language.base import CONTENT_POS, Pos
from app.schemas import MarkerId
from tests.test_markers import STORY

ADAPTER = get_adapter("eng")


def test_adapter_is_shared_and_declares_english() -> None:
    assert get_adapter("eng") is ADAPTER
    assert ADAPTER.language == "eng"
    assert "um" in ADAPTER.fillers


def test_unsupported_language_is_refused() -> None:
    with pytest.raises(UnsupportedLanguageError):
        get_adapter("fra")


def test_one_analysis_per_transcribed_word() -> None:
    words = ["I'm", "sure", "my", "mother-in-law", "didn't", "like", "Dr.", "Smith's", "car."]

    analyses = dict(zip(words, ADAPTER.analyse_utterance(words), strict=True))

    # "I'm" is split by the tagger into "I" + "'m": the word carries both tags.
    assert analyses["I'm"].pos == {Pos.PRON, Pos.AUX}
    assert Pos.NOUN in analyses["mother-in-law"].pos
    assert Pos.NOUN in analyses["car."].pos
    assert Pos.PUNCT not in analyses["car."].pos
    # A proper noun is a noun, but not a content word for the frequency marker.
    assert Pos.PROPN in analyses["Smith's"].pos
    assert CONTENT_POS.isdisjoint(analyses["Smith's"].pos)


def test_empty_utterance() -> None:
    assert ADAPTER.analyse_utterance([]) == ()


def test_frequency_is_looked_up_on_the_content_part_of_a_word() -> None:
    (possessive,) = ADAPTER.analyse_utterance(["dog's"])

    assert possessive.zipf_frequency == zipf_frequency("dog", "en")


def test_common_words_are_more_frequent_than_rare_ones() -> None:
    thing, stethoscope = ADAPTER.analyse_utterance(["thing", "stethoscope"])

    assert thing.zipf_frequency is not None
    assert stethoscope.zipf_frequency is not None
    assert thing.zipf_frequency > stethoscope.zipf_frequency


def test_unknown_word_has_no_frequency() -> None:
    (unknown,) = ADAPTER.analyse_utterance(["xqzvk"])

    assert unknown.zipf_frequency is None


def test_story_markers_with_the_real_tagger() -> None:
    """Same story as in test_markers, tagged by spaCy instead of a hand-written lexicon."""
    metrics = compute_session_metrics(STORY, ADAPTER)

    # Pronouns: I, It, We. Nouns: market, fish.
    assert metrics.value_of(MarkerId.PRONOUN_INDEX) == pytest.approx(3 / 5)
    assert metrics.value_of(MarkerId.NOUN_RATIO) == pytest.approx(2 / 12)
    # Content words: went, market, busy, bought, fish.
    expected = sum(zipf_frequency(w, "en") for w in ("went", "market", "busy", "bought", "fish"))
    assert metrics.value_of(MarkerId.MEAN_WORD_FREQUENCY) == pytest.approx(expected / 5)
