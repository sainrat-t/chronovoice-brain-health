"""Tests for step 4 (clinical summary), on the synthetic personas.

The model is scripted. What is tested is everything around it: the facts it is given,
the checks on its draft, the retry, and the fixed wording used when it fails.
"""

from __future__ import annotations

from functools import cache

import pytest

from app.agents.drift import compare_trajectory
from app.agents.passages import Passage, select_passages
from app.agents.segmentation import segment_target_speech
from app.agents.summary import (
    FindingDraft,
    SummaryDraft,
    check_draft,
    write_summary,
)
from app.demo_data import analyse_sessions, load_sessions
from app.language import get_adapter
from app.llm import LLMError
from app.schemas import (
    AnalysedSession,
    ClinicalSummaryReport,
    GenerationMode,
    LongitudinalComparisonResult,
    MarkerId,
    OrientationLevel,
    ReviewStatus,
    SessionTranscript,
    StudyRef,
    SuggestedAction,
    find_diagnostic_terms,
)
from tests.llm_doubles import ScriptedLLM

ADAPTER = get_adapter("eng")
PERSONAS = ("margaret-hale", "rajesh-menon", "grace-santos")

Session = tuple[SessionTranscript, AnalysedSession, LongitudinalComparisonResult]


@cache
def _persona(person_id: str) -> tuple[Session, ...]:
    pairs = analyse_sessions(load_sessions(person_id))
    results = {r.session_id: r for r in compare_trajectory([a for _, a in pairs])}
    return tuple((t, a, results[a.session_id]) for t, a in pairs)


def _margaret(number: int) -> Session:
    return _persona("margaret-hale")[number - 1]


def _shown(session: Session) -> tuple[Passage, ...]:
    """The passages chosen by computation, which the model may point to."""
    transcript, _, _ = session
    utterances = [u for t in segment_target_speech(transcript, ADAPTER) for u in t.utterances]
    return select_passages(utterances, ADAPTER)


def _passages(session: Session) -> dict[int, str]:
    return {passage.utterance_index: passage.text for passage in _shown(session)}


FLUENCY = (MarkerId.MAZE_INDEX, MarkerId.SPEECH_RATE_WPM)


def _draft(session: Session, **overrides: object) -> SummaryDraft:
    """A draft that passes for Margaret's session 10: every marker beyond range is reported."""
    _, _, comparison = session
    assert comparison.change_index is not None
    others = [m for m in comparison.change_index.significant_markers if m not in FLUENCY]
    fields: dict[str, object] = {
        "findings": [
            FindingDraft(
                text="Hesitations and repetitions were more frequent than in earlier sessions, "
                "and speech was slower.",
                beyond_usual_range=True,
                marker_ids=list(FLUENCY),
                passage_numbers=[_shown(session)[0].utterance_index],
                study_refs=[StudyRef.MUELLER_2018],
            ),
            FindingDraft(
                text="Words were shorter and more common than in earlier sessions, "
                "with fewer nouns.",
                beyond_usual_range=True,
                marker_ids=others,
                passage_numbers=[],
                study_refs=[],
            ),
        ],
        "person_observation": "Your last sessions were a little different from your usual ones.",
    }
    return SummaryDraft.model_validate(fields | overrides)


def _write(session: Session, llm: ScriptedLLM | None):
    transcript, analysed, comparison = session
    return write_summary(
        transcript=transcript,
        analysed=analysed,
        comparison=comparison,
        llm=llm,
        adapter=ADAPTER,
    )


# --- A draft that passes ----------------------------------------------------


def test_accepted_draft_becomes_the_summary_with_the_level_decided_by_step_3() -> None:
    session = _margaret(10)
    llm = ScriptedLLM(_draft(session))

    report = _write(session, llm)

    assert report.generation_mode is GenerationMode.LLM
    assert report.model_id == "claude-opus-5-5"
    assert report.orientation_level is OrientationLevel.REVIEW_RECOMMENDED
    assert report.clinician_summary.suggested_action is SuggestedAction.PROFESSIONAL_REVIEW
    finding, _ = report.clinician_summary.findings
    assert finding.marker_ids == FLUENCY
    # The passage is given by its number and shown in the transcript's own words.
    assert finding.passages == (_shown(session)[0].text,)
    assert finding.study_refs == (StudyRef.MUELLER_2018,)
    # Human oversight: a summary is a draft until a clinician validates it.
    assert report.review.status is ReviewStatus.DRAFT
    assert (report.session_id, report.synthetic) == ("margaret-hale-s10", True)
    assert len(llm.prompts) == 1


def test_model_is_given_the_decided_level_the_markers_and_real_passages() -> None:
    session = _margaret(10)
    llm = ScriptedLLM(_draft(session))

    _write(session, llm)

    (facts,) = llm.prompts
    assert "orientation_level: review_recommended" in facts
    assert "suggested_action: Review by a qualified professional" in facts
    assert "baseline_sessions: 5" in facts
    assert "adverse_context: none reported" in facts
    assert "- id: speech_rate_wpm | label: Speech rate" in facts
    assert "beyond the usual range, in the direction linked to decline: yes" in facts
    # The direction of a change is spelled out, only beyond the usual range.
    speech_rate, maze, pronouns = (
        next(line for line in facts.splitlines() if line.startswith(f"- id: {marker}"))
        for marker in ("speech_rate_wpm", "maze_index", "pronoun_index")
    )
    assert "compared with usual: lower" in speech_rate
    assert "compared with usual: higher" in maze
    assert "compared with usual: within the usual range" in pronouns
    assert "allowed study_refs: 08-mueller-2018" in facts
    assert "(hesitations)" in facts
    # The risk profile is never sent to the model.
    assert "Blood pressure" not in facts and "Genomic" not in facts


def test_headline_uncertainty_and_next_step_are_written_by_code_not_by_the_model() -> None:
    session = _margaret(10)

    report = _write(session, ScriptedLLM(_draft(session)))

    summary = report.clinician_summary
    assert summary.headline == (
        "Change from personal baseline: review by a qualified professional recommended"
    )
    assert summary.uncertainty_statement.startswith(
        "Based on a personal baseline of 5 sessions. Session quality: usable."
    )
    # What the model noticed, then the fixed sentences on what happens next.
    assert report.person_explanation == (
        "Your last sessions were a little different from your usual ones. "
        "This does not tell us why, and it is not a medical conclusion. "
        "We suggest talking it through with a health professional, "
        "who can look at the whole picture with you."
    )


# --- Drafts that do not pass ------------------------------------------------


def test_rejected_draft_is_retried_once_with_the_problems_found() -> None:
    session = _margaret(10)
    bad = _draft(session, person_observation="A pattern suggesting early dementia.")
    llm = ScriptedLLM(bad, _draft(session))

    report = _write(session, llm)

    assert report.generation_mode is GenerationMode.LLM
    assert len(llm.prompts) == 2
    assert "<problems_in_your_previous_draft>" not in llm.prompts[0]
    assert "Forbidden vocabulary: dementia" in llm.prompts[1]


def test_two_rejected_drafts_fall_back_to_the_fixed_wording() -> None:
    session = _margaret(10)
    bad = _draft(session, person_observation="This is a diagnosis.")
    llm = ScriptedLLM(bad, bad)

    report = _write(session, llm)

    assert report.generation_mode is GenerationMode.TEMPLATE_FALLBACK
    assert report.model_id is None
    assert report.clinician_summary.headline.startswith("Change from personal baseline")
    # One finding per marker beyond the usual range, each with its sources.
    _, _, comparison = session
    assert comparison.change_index is not None
    significant = comparison.change_index.significant_markers
    assert [f.marker_ids for f in report.clinician_summary.findings] == [(m,) for m in significant]
    assert all(f.study_refs for f in report.clinician_summary.findings)
    assert all(f.beyond_usual_range for f in report.clinician_summary.findings)
    assert len(llm.prompts) == 2


def test_unavailable_model_falls_back_without_retrying() -> None:
    llm = ScriptedLLM(LLMError("Claude API could not be reached"))

    report = _write(_margaret(10), llm)

    assert report.generation_mode is GenerationMode.TEMPLATE_FALLBACK
    assert len(llm.prompts) == 1


@pytest.mark.parametrize(
    ("overrides", "problem"),
    [
        ({"person_observation": "Signs consistent with MCI."}, "Forbidden vocabulary: mci"),
        ({"person_observation": "You said 12 hesitations."}, "must not contain numbers"),
        (
            {"person_observation": "Nothing to worry about today."},
            "reassure or alarm: remove worry",
        ),
        ({"person_observation": "This is a concerning change."}, "remove concerning"),
        ({"person_observation": "The person spoke more slowly."}, 'write "you"'),
        ({"person_observation": "  "}, "Every text field must be filled in"),
        ({"findings": []}, "At least one finding is required"),
    ],
)
def test_text_problems_are_reported(overrides: dict[str, object], problem: str) -> None:
    session = _margaret(10)
    _, _, comparison = session

    problems = check_draft(_draft(session, **overrides), comparison, _passages(session))

    assert any(problem in found for found in problems), problems


def test_forbidden_vocabulary_is_caught_in_a_finding_too() -> None:
    session = _margaret(10)
    _, _, comparison = session
    draft = _draft(session)
    draft.findings[1].text = "This is not diagnostic."

    problems = check_draft(draft, comparison, _passages(session))

    assert any("Forbidden vocabulary: diagnostic" in found for found in problems), problems


def test_finding_text_does_not_mention_passage_numbers() -> None:
    session = _margaret(10)
    _, _, comparison = session
    draft = _draft(session)
    draft.findings[0].text = "Hesitations were more frequent, as passages [1] and [30] show."

    problems = check_draft(draft, comparison, _passages(session))

    assert any("mentions a passage number in its text" in found for found in problems), problems


def test_marker_beyond_the_usual_range_cannot_go_unmentioned() -> None:
    session = _margaret(10)
    _, _, comparison = session
    draft = _draft(session)
    silent = draft.findings[1].marker_ids
    del draft.findings[1]

    problems = check_draft(draft, comparison, _passages(session))

    assert problems == [
        "These markers are beyond the usual range and no finding reports them: "
        f"{', '.join(marker.value for marker in silent)}."
    ]


@pytest.mark.parametrize(
    ("finding", "problem"),
    [
        ({"marker_ids": []}, "must list the ids of the markers it is about"),
        ({"marker_ids": [MarkerId.MATTR_50]}, "cites markers not measured here: mattr_50"),
        ({"study_refs": [StudyRef.SNOWDON_1996]}, "outside its markers' list: 01-snowdon-1996"),
        ({"passage_numbers": [9999]}, "points to passages that were not provided: 9999"),
        # The pronoun index stayed within the usual range: there is no change to report.
        (
            {"marker_ids": [MarkerId.PRONOUN_INDEX]},
            "=true but these markers are not beyond the usual range: pronoun_index",
        ),
        # Speech rate did leave the usual range: a finding cannot say it did not.
        (
            {"beyond_usual_range": False, "marker_ids": [MarkerId.SPEECH_RATE_WPM]},
            "=false but these markers are beyond the usual range: speech_rate_wpm",
        ),
    ],
)
def test_finding_problems_are_reported(finding: dict[str, object], problem: str) -> None:
    session = _margaret(10)
    _, _, comparison = session
    # Only the first six markers were compared in this variant of the session.
    comparison = comparison.model_copy(update={"markers": comparison.markers[:6]})
    base = _draft(session).findings[0].model_dump()
    draft = _draft(session, findings=[FindingDraft.model_validate(base | finding)])

    problems = check_draft(draft, comparison, _passages(session))

    assert any(problem in found for found in problems), problems


def test_good_draft_has_no_problem() -> None:
    session = _margaret(10)
    _, _, comparison = session

    assert check_draft(_draft(session), comparison, _passages(session)) == []


# --- Fixed wording ----------------------------------------------------------


def test_no_model_is_called_while_the_baseline_is_being_built() -> None:
    llm = ScriptedLLM()

    report = _write(_margaret(2), llm)

    assert report.generation_mode is GenerationMode.TEMPLATE
    assert report.orientation_level is OrientationLevel.BUILDING_BASELINE
    assert report.clinician_summary.findings == ()
    assert "1 of 3 baseline sessions recorded" in report.clinician_summary.uncertainty_statement
    assert llm.prompts == []


def test_without_a_model_every_synthetic_session_still_gets_a_safe_summary() -> None:
    reports: list[ClinicalSummaryReport] = []
    for person_id in PERSONAS:
        for session in _persona(person_id):
            report = _write(session, None)
            reports.append(report)
            _, _, comparison = session
            assert report.orientation_level is comparison.orientation.level
            assert not any(char.isdigit() for char in report.person_explanation)
            texts = [report.clinician_summary.headline, report.person_explanation]
            assert not any(find_diagnostic_terms(text) for text in texts)

    assert len(reports) == 30
    assert {r.generation_mode for r in reports} == {
        GenerationMode.TEMPLATE,
        GenerationMode.TEMPLATE_FALLBACK,
    }
    assert {r.orientation_level for r in reports} == set(OrientationLevel)


def test_fixed_wording_of_a_stable_and_of_a_partial_session() -> None:
    grace = _persona("grace-santos")

    stable = _write(grace[5], None)
    partial = _write(grace[6], None)

    assert stable.clinician_summary.headline == "Within this person's usual range"
    (finding,) = stable.clinician_summary.findings
    assert finding.text == "All the markers tested stayed within this person's usual range."
    assert not finding.beyond_usual_range
    assert "This session is partial" in partial.clinician_summary.findings[0].text
    assert "adverse context was reported" in partial.clinician_summary.uncertainty_statement
    assert "Session quality: partial" in partial.clinician_summary.uncertainty_statement
