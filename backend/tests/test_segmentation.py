"""Tests for the split of the tracked speaker's speech into turns, utterances and words."""

from __future__ import annotations

from app.agents.segmentation import WordKind, segment_target_speech
from tests.transcripts import CLINICIAN, StubAdapter, event, transcript, word

ADAPTER = StubAdapter({})


def test_no_tracked_speaker_gives_no_turns() -> None:
    assert segment_target_speech(transcript(word("Hello.", 0.0, 0.4), target=None), ADAPTER) == ()


def test_another_speaker_closes_the_turn() -> None:
    turns = segment_target_speech(
        transcript(
            word("Tell", 0.0, 0.2, CLINICIAN),
            word("me.", 0.3, 0.5, CLINICIAN),
            word("We", 1.0, 1.1),
            word("left.", 1.2, 1.5),
            word("Right.", 2.0, 2.3, CLINICIAN),
            word("Then", 3.0, 3.2),
            word("home.", 3.3, 3.6),
        ),
        ADAPTER,
    )

    assert [[w.form for w in turn.words] for turn in turns] == [["we", "left"], ["then", "home"]]


def test_words_are_sorted_into_lexical_filler_and_cut_off() -> None:
    (turn,) = segment_target_speech(
        transcript(
            word("Well,", 0.0, 0.2),
            word("um,", 0.3, 0.5),
            word("w-", 0.6, 0.7),
            word("we", 0.8, 0.9),
            word("left", 1.0, 1.2),
        ),
        ADAPTER,
    )

    assert [(w.form, w.kind) for w in turn.words] == [
        ("well", WordKind.LEXICAL),
        ("um", WordKind.FILLER),
        ("w", WordKind.CUT_OFF),
        ("we", WordKind.LEXICAL),
        ("left", WordKind.LEXICAL),
    ]


def test_hyphenated_compound_is_not_a_cut_off_word() -> None:
    (turn,) = segment_target_speech(transcript(word("mother-in-law,", 0.0, 0.8)), ADAPTER)

    assert [(w.form, w.kind) for w in turn.words] == [("mother-in-law", WordKind.LEXICAL)]


def test_utterances_end_on_sentence_punctuation_and_turn_end() -> None:
    (turn,) = segment_target_speech(
        transcript(
            word("We", 0.0, 0.1),
            word("left.", 0.2, 0.5),
            word("Why?", 0.6, 0.9),
            word('"No!"', 1.0, 1.3),
            word("and", 1.4, 1.5),
            word("then", 1.6, 1.8),
        ),
        ADAPTER,
    )

    assert [[w.form for w in u.words] for u in turn.utterances] == [
        ["we", "left"],
        ["why"],
        ["no"],
        ["and", "then"],
    ]
    assert [u.index for u in turn.utterances] == [0, 1, 2, 3]


def test_abbreviation_does_not_end_an_utterance() -> None:
    (turn,) = segment_target_speech(
        transcript(word("Dr.", 0.0, 0.2), word("Smith", 0.3, 0.6), word("came.", 0.7, 1.0)),
        ADAPTER,
    )

    assert len(turn.utterances) == 1


def test_utterance_indices_continue_across_turns() -> None:
    turns = segment_target_speech(
        transcript(
            word("Yes.", 0.0, 0.3),
            word("No.", 0.4, 0.7),
            word("Why?", 1.0, 1.3, CLINICIAN),
            word("Because.", 2.0, 2.5),
        ),
        ADAPTER,
    )

    assert [u.index for turn in turns for u in turn.utterances] == [0, 1, 2]


def test_audio_event_is_flagged_but_keeps_the_turn_open() -> None:
    (turn,) = segment_target_speech(
        transcript(
            word("We", 0.0, 0.1),
            event("(laughs)", 0.2, 0.8),
            word("left.", 1.0, 1.3),
            event("(coughs)", 1.4, 1.6, CLINICIAN),
            word("Then", 2.0, 2.2),
        ),
        ADAPTER,
    )

    assert [(w.form, w.after_audio_event) for w in turn.words] == [
        ("we", False),
        ("left", True),
        ("then", True),
    ]


def test_token_without_letter_or_digit_is_dropped() -> None:
    (turn,) = segment_target_speech(
        transcript(word("We", 0.0, 0.1), word("—", 0.2, 0.3), word("left", 0.4, 0.6)),
        ADAPTER,
    )

    assert [w.form for w in turn.words] == ["we", "left"]


def test_form_is_lowercase_with_straight_apostrophe() -> None:
    (turn,) = segment_target_speech(transcript(word("\u201cDon\u2019t,\u201d", 0.0, 0.3)), ADAPTER)

    assert turn.words[0].form == "don't"
