"""Step 4 of the pipeline: the clinical summary (constrained LLM).

The orientation level and the suggested action are decided by step 3. The model only
puts the measurements into words: the findings, and what the person is told was
noticed. The headline, the statement of uncertainty and the next step are written by
code from the same facts. The model's draft is untrusted: it is checked against the
facts of the session, retried once with the problems found, then replaced by a fixed
wording (docs/specs/pipeline.md, step 4).
"""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping, Sequence

from pydantic import BaseModel, ValidationError

from app.agents.markers import MARKER_SPECS
from app.agents.passages import Passage, select_passages
from app.agents.segmentation import segment_target_speech
from app.language.base import LanguageAdapter
from app.llm import LLMClient, LLMError
from app.schemas import (
    LEVEL_ACTIONS,
    MIN_BASELINE_SESSIONS,
    AnalysedSession,
    ClinicalSummaryReport,
    ClinicianSummary,
    Finding,
    GenerationMode,
    LongitudinalComparisonResult,
    MarkerDeviation,
    MarkerId,
    OrientationLevel,
    OrientationRule,
    SessionTranscript,
    StudyRef,
    SuggestedAction,
    find_diagnostic_terms,
)

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 2
"""One draft, then one retry with the problems found (docs/specs/pipeline.md, step 4)."""

RULE_TEXT: dict[OrientationRule, str] = {
    OrientationRule.INSUFFICIENT_BASELINE: "The personal baseline is not complete yet.",
    OrientationRule.NOT_SIGNIFICANT: "Fewer than two index markers are beyond the usual range.",
    OrientationRule.SINGLE_SIGNIFICANT: (
        "At least two index markers are beyond the usual range in this session, "
        "and the previous usable session was within range."
    ),
    OrientationRule.ADVERSE_CONTEXT_CAPPED: (
        "At least two index markers are beyond the usual range, but an adverse context "
        "was reported, so this session only counts as a first signal."
    ),
    OrientationRule.PERSISTENT_TWO_SESSIONS: (
        "At least two index markers are beyond the usual range in two consecutive usable sessions."
    ),
    OrientationRule.RAPID_DROP: (
        "At least four index markers are beyond the usual range in this single session."
    ),
    OrientationRule.CARRIED_OVER: (
        "This session is partial: it is shown, but the previous level is kept."
    ),
}

ACTION_TEXT: dict[SuggestedAction, str] = {
    SuggestedAction.CONTINUE_BASELINE: "Continue the sessions to complete the personal baseline.",
    SuggestedAction.ROUTINE_FOLLOW_UP: "Next session at the usual rhythm.",
    SuggestedAction.REPEAT_WITHIN_TWO_WEEKS: "Repeat a session within two weeks.",
    SuggestedAction.PROFESSIONAL_REVIEW: (
        "Review by a qualified professional; a memory clinic consultation may be useful."
    ),
}

SYSTEM_PROMPT = """\
You write short summaries for primary-care clinicians who use ChronoVoice, a tool that \
follows how a person's spoken language changes over time. It compares each recorded \
life-story session with that same person's earlier sessions, never with other people.

The tool supports screening only. Its measurements can show that a person's speech \
differs from their own usual range; they cannot show why. Many everyday things move \
these markers: a poor night, the topic of the story, mood, a cold. So never name or \
hint at a disease or condition, and never use the words diagnosis, diagnose, \
diagnostic, Alzheimer's, dementia, or cognitive impairment, not even to rule them out.

You are given the facts of one session: the orientation level and the suggested \
action, both already decided by fixed statistical rules; the markers with the \
person's usual range; and passages of what the person said. Your job is to put these \
facts into words. The level and the action are settled: do not restate them \
differently, soften or strengthen them, or add recommendations of your own.

Write, in English:
- findings: one to four findings. Each states one observation in one or two sentences \
and lists the ids of the markers it rests on. A marker within the usual range is \
reported as such, without saying it was higher or lower. Set beyond_usual_range to \
true when the \
finding reports markers that are beyond the usual range, and to false when it reports \
markers that stayed within it or were not tested; never mix the two kinds in one \
finding. Start with the markers beyond the usual range; when none is, say so in a \
single finding. Every marker that is beyond the usual range and counted in the change \
index must appear in a finding. marker_ids is never empty: a finding saying that all \
markers stayed within the usual range lists the ids of all those markers. A finding \
may point to passages that illustrate it, by their numbers: passage_numbers holds the \
numbers shown between square brackets under passages, never the text itself, and the \
text of a finding does not mention these numbers. It may \
cite studies, taken only from the allowed study_refs of the markers it rests on.
- person_observation: one or two short sentences said to the person themselves, as \
"you", in plain everyday words, with no numbers and no technical terms. Say only what \
was noticed in this session. Do not say what happens next, and do not reassure or \
alarm: avoid words such as "worry" or "concern".

The headline, the statement of uncertainty and the sentences telling the person what \
happens next are written separately from the same facts: do not write them."""

_HEADLINES = {
    OrientationLevel.BUILDING_BASELINE: "Personal baseline in progress",
    OrientationLevel.STABLE: "Within this person's usual range",
    OrientationLevel.MONITOR: "Signals to monitor: one session outside the usual range",
    OrientationLevel.REVIEW_RECOMMENDED: (
        "Change from personal baseline: review by a qualified professional recommended"
    ),
}

_PERSON_OBSERVATIONS = {
    OrientationLevel.BUILDING_BASELINE: (
        "We are still getting to know your usual way of telling stories. "
        "There is nothing to report yet."
    ),
    OrientationLevel.STABLE: (
        "Your way of telling this story was in line with your usual sessions. Nothing stands out."
    ),
    OrientationLevel.MONITOR: "This session was a little different from your usual ones.",
    OrientationLevel.REVIEW_RECOMMENDED: (
        "Your recent sessions were different from your usual ones in several ways."
    ),
}
"""What the person is told was noticed, when no model wrote it."""

_PERSON_NEXT_STEPS = {
    OrientationLevel.BUILDING_BASELINE: (
        "A few more sessions will give us a reliable starting point."
    ),
    OrientationLevel.STABLE: "We will simply continue as planned.",
    OrientationLevel.MONITOR: (
        "One session on its own can vary for many everyday reasons, such as a short night. "
        "We suggest another session within two weeks to see how things go."
    ),
    OrientationLevel.REVIEW_RECOMMENDED: (
        "This does not tell us why, and it is not a medical conclusion. "
        "We suggest talking it through with a health professional, "
        "who can look at the whole picture with you."
    ),
}
"""What happens next, always in these words: the level is decided by step 3, and the
person must be told the same thing whichever model wrote the rest."""

_PASSAGE_NUMBER = re.compile(r"\[\d+\]")
"""A passage number left in the text of a finding: it means nothing to the reader."""

_THIRD_PERSON = re.compile(r"\bthe (?:person|patient|speaker|participant)\b", re.IGNORECASE)
"""The sentences for the person are said to them, not about them."""

_JUDGEMENT_WORDS = re.compile(r"\b(?:worr|concern)\w*", re.IGNORECASE)
"""Words that reassure or alarm. The tool cannot tell whether a change is serious or
harmless, so the sentences for the person may not say either (design choice,
docs/specs/pipeline.md, step 4)."""


class FindingDraft(BaseModel):
    text: str
    beyond_usual_range: bool
    marker_ids: list[MarkerId]
    passage_numbers: list[int]
    study_refs: list[StudyRef]


class SummaryDraft(BaseModel):
    """What the model is asked to return, before any check."""

    findings: list[FindingDraft]
    person_observation: str


def write_summary(
    *,
    transcript: SessionTranscript,
    analysed: AnalysedSession,
    comparison: LongitudinalComparisonResult,
    llm: LLMClient | None,
    adapter: LanguageAdapter,
) -> ClinicalSummaryReport:
    """Write the non-diagnostic summary of one session.

    The narrative analysis of step 2 is not an input: it is experimental, outside the
    change index, and shown apart (docs/specs/pipeline.md, step 4).

    No model is called while the baseline is being built: there is nothing to put
    into words yet. Without a model, or when its drafts are rejected, the summary
    falls back to a fixed wording, so a session always has one.
    """
    if comparison.orientation.level is OrientationLevel.BUILDING_BASELINE:
        return _template(comparison, GenerationMode.TEMPLATE)
    if llm is None:
        return _template(comparison, GenerationMode.TEMPLATE_FALLBACK)

    utterances = [u for turn in segment_target_speech(transcript, adapter) for u in turn.utterances]
    shown = select_passages(utterances, adapter)
    # The model points to a passage by its number; the text shown is the transcript's.
    passages = {passage.utterance_index: passage.text for passage in shown}
    facts = build_facts(analysed, comparison, shown)

    problems: list[str] = []
    for _ in range(MAX_ATTEMPTS):
        try:
            reply = llm.generate(
                system=SYSTEM_PROMPT, user=facts + _feedback(problems), output=SummaryDraft
            )
        except LLMError as error:
            logger.warning(
                "summary of %s falls back to the template: %s", comparison.session_id, error
            )
            break
        problems = check_draft(reply.output, comparison, passages)
        if not problems:
            try:
                return _from_draft(reply.output, comparison, passages, reply.model_id)
            except ValidationError as error:
                problems = [
                    f"The summary does not fit the expected format: {error.error_count()} error(s)."
                ]
        logger.info("summary draft of %s rejected: %s", comparison.session_id, problems)
    return _template(comparison, GenerationMode.TEMPLATE_FALLBACK)


def build_facts(
    analysed: AnalysedSession,
    comparison: LongitudinalComparisonResult,
    passages: Sequence[Passage],
) -> str:
    """Everything the model may rely on, as plain structured text."""
    orientation = comparison.orientation
    adverse = analysed.metadata.context.adverse_items
    lines = [
        "<session>",
        f"orientation_level: {orientation.level.value}",
        f"reason: {RULE_TEXT[orientation.rule]}",
        f"suggested_action: {ACTION_TEXT[orientation.suggested_action]}",
        f"baseline_sessions: {comparison.uncertainty.baseline_session_count}",
        f"session_quality: {analysed.quality.status.value}",
        f"adverse_context: {', '.join(adverse) if adverse else 'none reported'}",
        "</session>",
        "<markers>",
    ]
    for deviation in comparison.markers:
        spec = MARKER_SPECS[deviation.marker]
        beyond = (
            "not tested"
            if deviation.test is None
            else ("yes" if deviation.test.significant else "no")
        )
        lines.append(
            f"- id: {spec.marker.value} | label: {spec.label} | what it measures: {spec.definition}"
            f" | this session: {_number(deviation.value)}"
            f" | usual: {_number(deviation.baseline_mean)} +/- {_number(deviation.baseline_sd)}"
            f" | compared with usual: {_direction(deviation)}"
            f" | beyond the usual range, in the direction linked to decline: {beyond}"
            f" | counted in the change index: {'yes' if spec.in_change_index else 'no'}"
            f" | allowed study_refs: {', '.join(ref.value for ref in spec.sources)}"
        )
    lines.append("</markers>")

    lines.append("<passages>")
    lines.extend(f'[{p.utterance_index}] ({p.reason}) "{p.text}"' for p in passages)
    lines.append("</passages>")
    return "\n".join(lines)


def check_draft(
    draft: SummaryDraft, comparison: LongitudinalComparisonResult, passages: Mapping[int, str]
) -> list[str]:
    """Problems that make a draft unusable; an empty list means it can be shown."""
    problems: list[str] = []
    texts = [draft.person_observation, *(finding.text for finding in draft.findings)]
    forbidden = sorted({term.lower() for text in texts for term in find_diagnostic_terms(text)})
    if forbidden:
        problems.append(f"Forbidden vocabulary: {', '.join(forbidden)}. Do not name any condition.")
    if any(not text.strip() for text in texts):
        problems.append("Every text field must be filled in.")
    if any(char.isdigit() for char in draft.person_observation):
        problems.append("person_observation must not contain numbers.")
    if _THIRD_PERSON.search(draft.person_observation):
        problems.append('person_observation is said to the person: write "you", not "the person".')
    judgements = sorted(
        {word.lower() for word in _JUDGEMENT_WORDS.findall(draft.person_observation)}
    )
    if judgements:
        problems.append(
            f"person_observation must not reassure or alarm: remove {', '.join(judgements)}."
        )
    if not draft.findings:
        problems.append("At least one finding is required.")

    compared = {deviation.marker for deviation in comparison.markers}
    beyond = {d.marker for d in comparison.markers if d.test is not None and d.test.significant}
    for number, finding in enumerate(draft.findings, start=1):
        if not finding.marker_ids:
            problems.append(
                f"Finding {number} must list the ids of the markers it is about; "
                "a finding about all the markers within range lists them all."
            )
        unknown = [m.value for m in finding.marker_ids if m not in compared]
        if unknown:
            problems.append(
                f"Finding {number} cites markers not measured here: {', '.join(unknown)}."
            )
        # The text may not report a change the measurements do not show, nor hide one.
        cited = set(finding.marker_ids) & compared
        wrong = cited - beyond if finding.beyond_usual_range else cited & beyond
        if wrong:
            claim = str(finding.beyond_usual_range).lower()
            state = "not beyond" if finding.beyond_usual_range else "beyond"
            names = ", ".join(sorted(marker.value for marker in wrong))
            problems.append(
                f"Finding {number} has beyond_usual_range={claim} "
                f"but these markers are {state} the usual range: {names}."
            )
        allowed = {ref for m in finding.marker_ids for ref in MARKER_SPECS[m].sources}
        extra = [ref.value for ref in finding.study_refs if ref not in allowed]
        if extra:
            problems.append(
                f"Finding {number} cites studies outside its markers' list: {', '.join(extra)}."
            )
        if _PASSAGE_NUMBER.search(finding.text):
            problems.append(
                f"Finding {number} mentions a passage number in its text: "
                "give the numbers in passage_numbers only."
            )
        unknown_passages = [str(n) for n in finding.passage_numbers if n not in passages]
        if unknown_passages:
            problems.append(
                f"Finding {number} points to passages that were not provided: "
                f"{', '.join(unknown_passages)}. Use only the numbers shown under passages."
            )

    # A marker the level rests on may not go unmentioned.
    index = comparison.change_index
    reported = {
        m for finding in draft.findings if finding.beyond_usual_range for m in finding.marker_ids
    }
    missing = [m.value for m in (index.significant_markers if index else ()) if m not in reported]
    if missing:
        problems.append(
            "These markers are beyond the usual range and no finding reports them: "
            f"{', '.join(missing)}."
        )
    return problems


def _feedback(problems: Sequence[str]) -> str:
    if not problems:
        return ""
    listed = "\n".join(f"- {problem}" for problem in problems)
    return (
        f"\n<problems_in_your_previous_draft>\n{listed}\n</problems_in_your_previous_draft>\n"
        "Write the summary again and fix these problems."
    )


def _from_draft(
    draft: SummaryDraft,
    comparison: LongitudinalComparisonResult,
    passages: Mapping[int, str],
    model_id: str,
) -> ClinicalSummaryReport:
    level = comparison.orientation.level
    return _report(
        comparison,
        findings=tuple(
            Finding(
                text=finding.text.strip(),
                beyond_usual_range=finding.beyond_usual_range,
                marker_ids=tuple(dict.fromkeys(finding.marker_ids)),
                passages=tuple(passages[n] for n in dict.fromkeys(finding.passage_numbers)),
                study_refs=tuple(dict.fromkeys(finding.study_refs)),
            )
            for finding in draft.findings
        ),
        person_explanation=f"{draft.person_observation.strip()} {_PERSON_NEXT_STEPS[level]}",
        mode=GenerationMode.LLM,
        model_id=model_id,
    )


def _template(
    comparison: LongitudinalComparisonResult, mode: GenerationMode
) -> ClinicalSummaryReport:
    """Fixed wording, built from the measurements alone."""
    level = comparison.orientation.level
    index = comparison.change_index

    findings: list[Finding] = []
    if comparison.orientation.rule is OrientationRule.CARRIED_OVER and index is not None:
        findings.append(
            Finding(
                text="This session is partial (too short, or transcribed with low confidence). "
                "It is shown for information and does not change the level.",
                beyond_usual_range=False,
                marker_ids=index.tested_markers,
            )
        )
    elif index is not None and index.significant_markers:
        findings.extend(
            Finding(
                text=f"{MARKER_SPECS[marker].label} moved beyond this person's usual range, "
                "in the direction the literature associates with decline.",
                beyond_usual_range=True,
                marker_ids=(marker,),
                study_refs=MARKER_SPECS[marker].sources,
            )
            for marker in index.significant_markers
        )
    elif index is not None:
        findings.append(
            Finding(
                text="All the markers tested stayed within this person's usual range.",
                beyond_usual_range=False,
                marker_ids=index.tested_markers,
            )
        )

    return _report(
        comparison,
        findings=tuple(findings),
        person_explanation=f"{_PERSON_OBSERVATIONS[level]} {_PERSON_NEXT_STEPS[level]}",
        mode=mode,
        model_id=None,
    )


def _uncertainty_statement(comparison: LongitudinalComparisonResult) -> str:
    """How much weight the session can bear, from the figures of step 3 alone."""
    uncertainty = comparison.uncertainty
    if comparison.orientation.level is OrientationLevel.BUILDING_BASELINE:
        return (
            f"{uncertainty.baseline_session_count} of {MIN_BASELINE_SESSIONS} baseline sessions "
            "recorded. No assessment is made before the personal baseline exists."
        )
    statement = (
        f"Based on a personal baseline of {uncertainty.baseline_session_count} sessions. "
        f"Session quality: {uncertainty.quality_status.value}. "
    )
    if uncertainty.adverse_context:
        statement += "An adverse context was reported, which makes this session less reliable. "
    return statement + (
        "With few baseline sessions, moderate changes can go unnoticed and a single session "
        "can deviate by chance. This is screening support, not a medical conclusion."
    )


def _report(
    comparison: LongitudinalComparisonResult,
    *,
    findings: tuple[Finding, ...],
    person_explanation: str,
    mode: GenerationMode,
    model_id: str | None,
) -> ClinicalSummaryReport:
    level = comparison.orientation.level
    return ClinicalSummaryReport(
        session_id=comparison.session_id,
        person_id=comparison.person_id,
        synthetic=comparison.synthetic,
        orientation_level=level,
        clinician_summary=ClinicianSummary(
            # Both are facts already settled by step 3: never left to the model.
            headline=_HEADLINES[level],
            findings=findings,
            uncertainty_statement=_uncertainty_statement(comparison),
            suggested_action=LEVEL_ACTIONS[level],
        ),
        person_explanation=person_explanation,
        generation_mode=mode,
        model_id=model_id,
    )


def _direction(deviation: MarkerDeviation) -> str:
    """Spelled out for the model, which otherwise sometimes states the wrong direction.

    Given only beyond the usual range: for a marker within it, "higher than usual" would
    read as a change the measurements do not show.
    """
    if deviation.test is None or not deviation.test.significant or deviation.value is None:
        return "within the usual range" if deviation.test is not None else "not tested"
    return "higher" if deviation.value > deviation.baseline_mean else "lower"


def _number(value: float | None) -> str:
    return "not available" if value is None else f"{value:.3g}"
