"""Tests for step 2 (narrative analyst): the checks applied to the model's answer."""

from __future__ import annotations

from app.agents.narrative import (
    EpisodeDraft,
    NarrativeDraft,
    Relation,
    RepetitionDraft,
    analyse_narrative,
    build_prompt,
)
from app.agents.passages import SpokenText, select_passages
from app.agents.segmentation import segment_target_speech
from app.language.base import Pos
from app.llm import LLMError
from app.schemas import Episode, LifePeriod, NarrativeAnalysis, RepetitionScope
from tests.llm_doubles import ScriptedLLM
from tests.transcripts import CLINICIAN, StubAdapter, transcript, word

ADAPTER = StubAdapter(
    {
        "i": (frozenset({Pos.PRON}), None),
        "it": (frozenset({Pos.PRON}), None),
        "me": (frozenset({Pos.PRON}), None),
        "we": (frozenset({Pos.PRON}), None),
        "nurse": (frozenset({Pos.NOUN}), None),
        "patient": (frozenset({Pos.NOUN}), None),
        "bird": (frozenset({Pos.NOUN}), None),
    }
)


def _say(sentence: str, start: float, speaker: str | None = None) -> list:
    tokens = sentence.split()
    return [
        word(token, start + 0.3 * i, start + 0.3 * i + 0.2, *([speaker] if speaker else []))
        for i, token in enumerate(tokens)
    ]


# [0] nursing  [1] the carved bird  [2] the windowsill  [3] the move  [4] said before
SESSION = transcript(
    *_say("Tell me about your first job.", 0.0, CLINICIAN),
    *_say("I trained as a nurse in Leeds.", 10.0),
    *_say("A patient carved me a little wooden bird for my birthday.", 20.0),
    *_say("I still keep it, um, on my, my windowsill.", 30.0),
    *_say("Then we moved to the coast.", 40.0),
    *_say("I think I told you about the bird last time.", 50.0),
)

EARLIER = NarrativeAnalysis(
    session_id="s-0",
    person_id="p-1",
    synthetic=True,
    model_id="claude-opus-5-5",
    episodes=(
        Episode(
            episode_id="e1",
            summary="A patient carved her a wooden sparrow.",
            life_period=LifePeriod.YOUNG_ADULTHOOD,
            utterance_indices=(4,),
        ),
    ),
)


def _episode(
    episode_id: str, indices: list[int], summary: str = "Something happened."
) -> EpisodeDraft:
    return EpisodeDraft(
        episode_id=episode_id,
        summary=summary,
        life_period=LifePeriod.YOUNG_ADULTHOOD,
        people=["a patient", " "],
        places=[],
        time_references=[],
        utterance_indices=indices,
    )


def _repetition(
    episode_id: str,
    quotes: list[str],
    *,
    origin: str = "s-0/e1",
    relation: Relation = Relation.SAME_EVENT,
    acknowledgement: str | None = None,
) -> RepetitionDraft:
    return RepetitionDraft(
        episode_id=episode_id,
        retold_from=origin,
        rationale="Same event as before.",
        relation=relation,
        acknowledgement_quote=acknowledgement,
        quoted_passages=quotes,
    )


def _analyse(draft: NarrativeDraft) -> NarrativeAnalysis:
    result = analyse_narrative(SESSION, [EARLIER], ScriptedLLM(draft), ADAPTER)
    assert result is not None
    return result


def test_episodes_keep_only_real_utterances() -> None:
    result = _analyse(
        NarrativeDraft(
            episodes=[
                _episode("e1", [0]),
                _episode("e2", [2, 1, 99]),  # 99 does not exist
                _episode("e3", [50]),  # no real utterance: dropped
                _episode("e1", [3]),  # id already used: dropped
                _episode("e4", [3], summary="  "),  # no summary: dropped
            ],
            repetitions=[],
        )
    )

    assert [(e.episode_id, e.utterance_indices) for e in result.episodes] == [
        ("e1", (0,)),
        ("e2", (1, 2)),
    ]
    assert result.episodes[0].people == ("a patient",)
    assert (result.session_id, result.person_id, result.synthetic) == ("s-1", "p-1", True)
    assert result.experimental
    assert result.model_id == "claude-opus-5-5"


def test_repetition_needs_a_passage_the_person_said_and_a_known_origin() -> None:
    episodes = [_episode("e1", [0]), _episode("e2", [1, 2]), _episode("e3", [3])]
    within = RepetitionScope.WITHIN_SESSION
    result = _analyse(
        NarrativeDraft(
            episodes=episodes,
            repetitions=[
                _repetition("e1", ["I worked in a factory"]),  # never said
                _repetition("e1", ["wooden bird"], origin="s-unknown/e1"),  # unknown session
                _repetition("e1", ["wooden bird"], origin="s-0/e9"),  # unknown earlier episode
                _repetition("e1", ["wooden bird"], origin="e1"),  # told again from itself
                _repetition("e9", ["wooden bird"]),  # episode that was not kept
                # Kept, without the passage the person never said.
                _repetition("e2", ["a patient carved me a little wooden bird", "She said never"]),
                # Kept: an earlier episode of this session, given between brackets.
                _repetition("e3", ["we moved to the coast"], origin="[e1]"),
            ],
        )
    )

    across, same_session = result.repetitions
    assert across.episode_id == "e2"
    assert across.scope is RepetitionScope.ACROSS_SESSIONS
    assert (across.previous_session_id, across.previous_episode_id) == ("s-0", "e1")
    assert across.quoted_passages == ("A patient carved me a little wooden bird",)
    assert (same_session.episode_id, same_session.scope) == ("e3", within)
    assert (same_session.previous_session_id, same_session.previous_episode_id) == (None, "e1")


def test_episodes_are_renamed_and_the_references_of_the_model_follow() -> None:
    # The model named its episodes after the references of earlier sessions.
    result = _analyse(
        NarrativeDraft(
            episodes=[_episode("s-1/first", [0]), _episode("[s-1/bird]", [1, 2])],
            repetitions=[
                _repetition("s-1/bird", ["wooden bird"]),
                _repetition("first", ["a nurse in Leeds"], origin="s-1/bird"),
            ],
        )
    )

    assert [e.episode_id for e in result.episodes] == ["e1", "e2"]
    across, same_session = result.repetitions
    assert (across.episode_id, across.previous_session_id) == ("e2", "s-0")
    assert (same_session.episode_id, same_session.previous_episode_id) == ("e1", "e2")
    assert same_session.scope is RepetitionScope.WITHIN_SESSION


def test_related_theme_is_not_a_repetition() -> None:
    result = _analyse(
        NarrativeDraft(
            episodes=[_episode("e1", [0]), _episode("e2", [1, 2])],
            repetitions=[
                _repetition("e2", ["wooden bird"], relation=Relation.RELATED_THEME),
            ],
        )
    )

    assert result.repetitions == ()


def test_only_the_first_valid_repetition_of_an_episode_is_kept() -> None:
    result = _analyse(
        NarrativeDraft(
            episodes=[_episode("e1", [0]), _episode("e2", [1, 2])],
            repetitions=[
                _repetition("e2", ["wooden bird"], relation=Relation.RELATED_THEME),
                _repetition("e2", ["wooden bird"]),
                _repetition("e2", ["my windowsill"], origin="e1"),
            ],
        )
    )

    (kept,) = result.repetitions
    assert (kept.previous_session_id, kept.quoted_passages) == ("s-0", ("wooden bird",))


def test_acknowledged_only_with_words_the_person_said() -> None:
    episodes = [_episode("e1", [0]), _episode("e2", [1, 2]), _episode("e3", [3])]
    result = _analyse(
        NarrativeDraft(
            episodes=episodes,
            repetitions=[
                _repetition(
                    "e2", ["wooden bird"], acknowledgement="I told you about the bird last time"
                ),
                # Words the person never said: the repetition is kept, not the claim.
                _repetition("e3", ["moved to the coast"], acknowledgement="As I said before"),
            ],
        )
    )

    said_so, did_not = result.repetitions
    assert said_so.self_flagged
    assert said_so.acknowledgement_quote == "I told you about the bird last time."
    assert not did_not.self_flagged
    assert did_not.acknowledgement_quote is None


def test_passage_tidied_of_its_hesitations_is_kept_as_the_person_said_it() -> None:
    result = _analyse(
        NarrativeDraft(
            episodes=[_episode("e1", [0]), _episode("e2", [1, 2])],
            repetitions=[
                _repetition(
                    "e2",
                    # The second passage was copied with the number of its utterance.
                    ["I still keep it on my, my windowsill", "[1] A patient carved me"],
                    acknowledgement="[4] I think I told you about the bird last time.",
                )
            ],
        )
    )

    (kept,) = result.repetitions
    assert kept.quoted_passages == (
        "I still keep it, um, on my, my windowsill.",
        "A patient carved me",
    )
    assert kept.acknowledgement_quote == "I think I told you about the bird last time."


def test_prompt_shows_numbered_utterances_and_earlier_episodes_only() -> None:
    llm = ScriptedLLM(NarrativeDraft(episodes=[], repetitions=[]))

    analyse_narrative(SESSION, [EARLIER], llm, ADAPTER)

    (prompt,) = llm.prompts
    # An earlier episode is named by its session and its id: the model copies it back.
    assert '<session id="s-0">\n[s-0/e1] A patient carved her a wooden sparrow.' in prompt
    assert "[1] A patient carved me a little wooden bird for my birthday." in prompt
    assert "[2] I still keep it, um, on my, my windowsill." in prompt
    # The interviewer's words are not part of the person's story.
    assert "Tell me about your first job" not in prompt
    assert prompt == build_prompt(
        "s-1",
        [u for t in segment_target_speech(SESSION, ADAPTER) for u in t.utterances],
        [EARLIER],
    )


def test_unavailable_model_skips_the_step() -> None:
    assert analyse_narrative(SESSION, [], ScriptedLLM(LLMError("down")), ADAPTER) is None


def test_session_without_speech_is_not_sent_to_the_model() -> None:
    llm = ScriptedLLM()
    silent = transcript(*_say("Hello there.", 0.0, CLINICIAN), target=None)

    assert analyse_narrative(silent, [], llm, ADAPTER) is None
    assert llm.prompts == []


# --- Passages ---------------------------------------------------------------


def _utterances():
    return [u for turn in segment_target_speech(SESSION, ADAPTER) for u in turn.utterances]


def test_quote_must_be_word_for_word_whatever_the_case_and_punctuation() -> None:
    spoken = SpokenText(_utterances())

    assert spoken.contains("a patient carved me a little wooden bird")
    assert spoken.contains("I STILL keep it um on my my windowsill")
    assert not spoken.contains("a patient carved me a wooden bird")  # a word is missing
    assert not spoken.contains("wooden bir")  # part of a word
    assert not spoken.contains("Tell me about your first job")  # said by the interviewer
    assert not spoken.contains("...")


def test_quote_is_returned_in_the_words_of_the_transcript() -> None:
    spoken = SpokenText(_utterances())

    # Case and punctuation come from the transcript, not from the quote.
    assert spoken.locate("a PATIENT carved me") == "A patient carved me"
    # A hesitation left out of the quote is put back; a quote may also start on one.
    assert spoken.locate("keep it on my") == "keep it, um, on my,"
    assert spoken.locate("um on my my windowsill") == "um, on my, my windowsill."
    # Only hesitations may be left out: "my" is a word like any other.
    assert spoken.locate("on my windowsill") is None
    # A quote may run over two utterances.
    assert spoken.locate("for my birthday I still keep it") == "for my birthday. I still keep it,"
    assert spoken.locate("") is None


def test_passages_shown_are_the_most_hesitant_and_the_most_pronoun_heavy() -> None:
    passages = select_passages(_utterances(), ADAPTER)

    assert [(p.utterance_index, p.reason) for p in passages] == [(2, "hesitations")]
    assert passages[0].text == "I still keep it, um, on my, my windowsill."

    pronoun_heavy = transcript(*_say("I told me it and we left.", 0.0))
    utterances = [u for t in segment_target_speech(pronoun_heavy, ADAPTER) for u in t.utterances]
    assert [(p.utterance_index, p.reason) for p in select_passages(utterances, ADAPTER)] == [
        (0, "pronouns")
    ]
