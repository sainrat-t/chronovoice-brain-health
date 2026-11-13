"""Tests for the step 1 markers, on cases worked out by hand."""

from __future__ import annotations

import pytest

from app.agents.markers import (
    MARKER_SPECS,
    MATTR_MIN_WORDS,
    Pause,
    compute_session_metrics,
    count_immediate_repetitions,
    find_pauses,
    mattr,
)
from app.agents.segmentation import segment_target_speech
from app.language.base import Pos
from app.schemas import MarkerFamily, MarkerId, SessionMetrics, SessionTranscript
from tests.transcripts import (
    CLINICIAN,
    StubAdapter,
    evenly_spaced_words,
    event,
    transcript,
    word,
)


def _tags(*pos: Pos) -> frozenset[Pos]:
    return frozenset(pos)


# Function words carry a frequency too, to check that only content words are averaged.
LEXICON: dict[str, tuple[frozenset[Pos], float | None]] = {
    "i": (_tags(Pos.PRON), 7.0),
    "it": (_tags(Pos.PRON), 7.0),
    "we": (_tags(Pos.PRON), 7.0),
    "to": (_tags(Pos.ADP), 7.5),
    "the": (_tags(Pos.DET), 7.7),
    "was": (_tags(Pos.AUX), 7.0),
    "went": (_tags(Pos.VERB), 5.5),
    "bought": (_tags(Pos.VERB), 4.0),
    "busy": (_tags(Pos.ADJ), 4.5),
    "market": (_tags(Pos.NOUN), 5.0),
    "fish": (_tags(Pos.NOUN), None),  # not in the frequency list
}
ADAPTER = StubAdapter(LEXICON)

# The person says, in two turns:
#   "I um went to the the market. It was b- busy."   then   "We (laughs) bought fish."
# 12 lexical words, 1 filler ("um"), 1 cut-off word ("b-"), 3 utterances.
STORY = transcript(
    word("Tell", 0.00, 0.30, CLINICIAN),
    word("me.", 0.35, 0.60, CLINICIAN),
    word("I", 1.00, 1.10),
    word("um", 1.20, 1.40),
    word("went", 1.90, 2.20),  # 0.50 s after "um": pause inside the utterance
    word("to", 2.25, 2.35),
    word("the", 2.40, 2.50),
    word("the", 2.60, 2.70),  # immediate repetition
    word("market.", 2.75, 3.25),
    word("It", 4.00, 4.10),  # 0.75 s after "market.": pause between utterances
    word("was", 4.15, 4.35),
    word("b-", 4.40, 4.50),
    word("busy.", 4.60, 5.00),
    word("Right.", 5.20, 5.50, CLINICIAN),
    word("We", 6.00, 6.10),
    event("(laughs)", 6.20, 6.80),
    word("bought", 7.00, 7.30),  # 0.90 s after "We", but filled by a laugh: not a pause
    word("fish.", 7.35, 7.75),
)


def _metrics(source: SessionTranscript) -> SessionMetrics:
    return compute_session_metrics(source, ADAPTER)


def _marker(metrics: SessionMetrics, marker: MarkerId) -> tuple[float | None, int]:
    (found,) = (m for m in metrics.markers if m.marker is marker)
    return found.value, found.n_units


# --- Hand-computed session --------------------------------------------------


@pytest.mark.parametrize(
    ("marker", "expected", "n_units"),
    [
        # Pronouns: I, It, We = 3. Nouns: market, fish = 2.
        (MarkerId.PRONOUN_INDEX, 3 / 5, 5),
        (MarkerId.NOUN_RATIO, 2 / 12, 12),
        # Content words with a known frequency: went 5.5, market 5.0, busy 4.5, bought 4.0.
        (MarkerId.MEAN_WORD_FREQUENCY, 4.75, 4),
        # Letters: 1+4+2+3+3+6 + 2+3+4 + 2+6+4 = 40.
        (MarkerId.MEAN_WORD_LENGTH, 40 / 12, 12),
        # 1 filler + 1 repetition + 1 cut-off word, over 3 utterances.
        (MarkerId.MAZE_INDEX, 1.0, 3),
        # Speaking time: (5.00 - 1.00) + (7.75 - 6.00) = 5.75 s.
        (MarkerId.SPEECH_RATE_WPM, 12 / (5.75 / 60), 12),
        (MarkerId.PAUSES_BETWEEN_PER100W, 100 / 12, 12),
        (MarkerId.PAUSES_WITHIN_PER100W, 100 / 12, 12),
    ],
)
def test_markers_of_the_hand_computed_story(
    marker: MarkerId, expected: float, n_units: int
) -> None:
    value, units = _marker(_metrics(STORY), marker)

    assert value == pytest.approx(expected)
    assert units == n_units


def test_mattr_is_not_reported_on_a_short_story() -> None:
    assert _marker(_metrics(STORY), MarkerId.MATTR_50) == (None, 12)


def test_pauses_of_the_hand_computed_story() -> None:
    pauses = find_pauses(segment_target_speech(STORY, ADAPTER))

    assert pauses == (
        Pause(start_s=1.40, duration_s=0.5, between_utterances=False),
        Pause(start_s=3.25, duration_s=0.75, between_utterances=True),
    )


def test_metrics_keep_session_identity_and_synthetic_flag() -> None:
    metrics = _metrics(STORY)

    assert (metrics.session_id, metrics.person_id, metrics.synthetic) == ("s-1", "p-1", True)
    assert [m.marker for m in metrics.markers] == list(MarkerId)


# --- Properties -------------------------------------------------------------


def test_fillers_raise_the_maze_index_but_leave_semantic_markers_unchanged() -> None:
    fluent = transcript(word("We", 0.0, 0.2), word("bought", 0.3, 0.6), word("fish.", 0.7, 1.0))
    hesitant = transcript(
        word("We", 0.0, 0.2),
        word("um", 0.3, 0.5),
        word("uh", 0.6, 0.8),
        word("bought", 0.9, 1.2),
        word("fish.", 1.3, 1.6),
    )

    for marker in (MarkerId.PRONOUN_INDEX, MarkerId.NOUN_RATIO, MarkerId.MEAN_WORD_LENGTH):
        assert _marker(_metrics(hesitant), marker) == _marker(_metrics(fluent), marker)
    assert _marker(_metrics(fluent), MarkerId.MAZE_INDEX) == (0.0, 1)
    assert _marker(_metrics(hesitant), MarkerId.MAZE_INDEX) == (2.0, 1)


def test_pause_threshold_is_250_ms_inclusive() -> None:
    turns = segment_target_speech(
        transcript(
            word("one", 0.80, 1.05),
            word("two", 1.30, 1.50),  # 0.250 s after "one": counted
            word("three", 1.749, 1.90),  # 0.249 s after "two": not counted
        ),
        ADAPTER,
    )

    assert [pause.duration_s for pause in find_pauses(turns)] == [0.25]


def test_gap_across_turns_is_not_a_pause() -> None:
    turns = segment_target_speech(
        transcript(
            word("Yes.", 0.0, 0.3),
            word("Why?", 1.0, 1.3, CLINICIAN),
            word("Because.", 3.0, 3.5),
        ),
        ADAPTER,
    )

    assert find_pauses(turns) == ()


def test_session_without_tracked_speech_has_no_values() -> None:
    metrics = _metrics(transcript(word("Hello.", 0.0, 0.4, CLINICIAN), target=None))

    assert [(m.value, m.n_units) for m in metrics.markers] == [(None, 0)] * len(MarkerId)


def test_language_must_match_the_adapter() -> None:
    with pytest.raises(ValueError, match="does not match"):
        _metrics(transcript(word("Bonjour.", 0.0, 0.4), language="fra"))


# --- MATTR ------------------------------------------------------------------


def test_mattr_averages_the_type_token_ratio_of_every_window() -> None:
    # Windows of 2: [a a] = 1/2, [a b] = 2/2, [b a] = 2/2.
    assert mattr(["a", "a", "b", "a"], window=2) == pytest.approx((0.5 + 1 + 1) / 3)
    # Windows of 3: [a b a] = 2/3, [b a b] = 2/3, [a b c] = 3/3.
    assert mattr(["a", "b", "a", "b", "c"], window=3) == pytest.approx(7 / 9)


def test_mattr_needs_at_least_one_window() -> None:
    assert mattr(["a", "b"], window=3) is None
    with pytest.raises(ValueError, match="window"):
        mattr(["a", "b"], window=0)


def test_mattr_marker_is_reported_from_150_words() -> None:
    # Five distinct words in rotation: every window of 50 words holds 5 types -> 5 / 50.
    cycle = ["red", "green", "blue", "black", "white"]

    enough = _metrics(evenly_spaced_words(cycle * (MATTR_MIN_WORDS // 5)))
    too_short = _metrics(evenly_spaced_words((cycle * 30)[: MATTR_MIN_WORDS - 1]))

    assert _marker(enough, MarkerId.MATTR_50) == (pytest.approx(0.1), 150)
    assert _marker(too_short, MarkerId.MATTR_50) == (None, 149)


# --- Immediate repetitions --------------------------------------------------


@pytest.mark.parametrize(
    ("spoken", "expected"),
    [
        ("the the dog", 1),
        ("it was it was nice", 1),
        ("no no no", 2),
        ("i went to the i went to the shop", 0),  # four words: longer than a maze
        ("a b c a b c", 1),
        ("i went i saw", 0),
        ("we left", 0),
        ("", 0),
    ],
)
def test_count_immediate_repetitions(spoken: str, expected: int) -> None:
    assert count_immediate_repetitions(spoken.split()) == expected


# --- Catalogue --------------------------------------------------------------


def test_every_marker_has_a_spec() -> None:
    assert set(MARKER_SPECS) == set(MarkerId)
    assert all(spec.marker is marker for marker, spec in MARKER_SPECS.items())


def test_change_index_holds_four_semantic_and_two_fluency_markers() -> None:
    in_index = {m: spec.family for m, spec in MARKER_SPECS.items() if spec.in_change_index}

    assert in_index == {
        MarkerId.PRONOUN_INDEX: MarkerFamily.SEMANTIC,
        MarkerId.NOUN_RATIO: MarkerFamily.SEMANTIC,
        MarkerId.MEAN_WORD_FREQUENCY: MarkerFamily.SEMANTIC,
        MarkerId.MEAN_WORD_LENGTH: MarkerFamily.SEMANTIC,
        MarkerId.MAZE_INDEX: MarkerFamily.FLUENCY,
        MarkerId.SPEECH_RATE_WPM: MarkerFamily.FLUENCY,
    }
