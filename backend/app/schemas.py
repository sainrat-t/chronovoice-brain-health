"""Pydantic v2 contracts exchanged between ChronoVoice pipeline steps.

The pipeline steps exchange only the models defined here (CLAUDE.md, "Code" rules).
The pipeline is specified in docs/specs/pipeline.md:

    RecordingMetadata
      -> step 0  capture & quality      -> SessionTranscript, QualityReport
      -> step 1  markers                -> SessionMetrics
      -> step 2  narrative analyst      -> NarrativeAnalysis              (experimental)
      -> step 3  longitudinal drift     -> LongitudinalComparisonResult
      -> step 4  clinical summary       -> ClinicalSummaryReport

Where a schema can enforce a clinical safety rule from CLAUDE.md, it does:

* rule 1: no diagnostic vocabulary in generated text (ClinicalSummaryReport);
* rule 3: synthetic data carries ``synthetic=True`` (field on every session-level model);
* rule 5: no orientation level without a personal baseline of at least
  MIN_BASELINE_SESSIONS usable sessions (LongitudinalComparisonResult).

All models are immutable and reject unknown fields.
"""

from __future__ import annotations

import re
from enum import StrEnum
from itertools import pairwise
from typing import Annotated, Literal, Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeFloat,
    NonNegativeInt,
    model_validator,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MIN_BASELINE_SESSIONS = 3
"""No orientation level below this many baseline sessions (CLAUDE.md, clinical rule 5)."""

MAX_BASELINE_SESSIONS = 5
"""The baseline grows from 3 to 5 stable usable sessions, then freezes.

Design choice validated on 2026-11-12, not backed by a study
(docs/specs/pipeline.md, step 3; docs/specs/questions.md, Q31).
"""

MIN_SIGNIFICANT_MARKERS = 2
"""A session is "in deviation" when at least this many index markers are significant."""

RAPID_DROP_MARKERS = 4
"""A session is a "rapid drop" when at least this many index markers are significant.

Both thresholds are design choices calibrated by simulation, not taken from a study:
see docs/specs/pipeline.md (step 3) and backend/scripts/simulate_orientation_rules.py.
"""

# ---------------------------------------------------------------------------
# Base model and shared field types
# ---------------------------------------------------------------------------


class ContractModel(BaseModel):
    """Base class for every contract: immutable and strict about unknown fields."""

    model_config = ConfigDict(frozen=True, extra="forbid")


Identifier = Annotated[str, Field(min_length=1, max_length=128)]
LanguageCode = Annotated[str, Field(pattern=r"^[a-z]{3}$", description="ISO 639-3 code.")]
Proportion = Annotated[float, Field(ge=0.0, le=1.0)]
LogProb = Annotated[float, Field(le=0.0)]
NonEmptyText = Annotated[str, Field(min_length=1)]


class SessionScoped(ContractModel):
    """Fields shared by every model that describes one recording session."""

    session_id: Identifier
    person_id: Identifier
    synthetic: bool = False


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class TaskType(StrEnum):
    """Kind of speech task. The personal baseline is kept per task type."""

    LIFE_STORY = "life_story"


class RecordingSource(StrEnum):
    CLINICIAN_UI = "clinician_ui"
    INTEGRATION = "integration"


class SleepQuality(StrEnum):
    GOOD = "good"
    AVERAGE = "average"
    POOR = "poor"


class Mood(StrEnum):
    GOOD = "good"
    NEUTRAL = "neutral"
    LOW = "low"


class TokenKind(StrEnum):
    """Scribe item types kept by step 0 (Scribe ``spacing`` items are dropped)."""

    WORD = "word"
    AUDIO_EVENT = "audio_event"


class QualityStatus(StrEnum):
    USABLE = "usable"
    PARTIAL = "partial"
    REJECTED = "rejected"


class QualityReason(StrEnum):
    # Rejection reasons
    NO_TARGET_SPEECH = "no_target_speech"
    LANGUAGE_MISMATCH = "language_mismatch"
    UNREADABLE_AUDIO = "unreadable_audio"
    # Partial reasons
    TOO_FEW_WORDS = "too_few_words"
    TOO_SHORT = "too_short"
    LOW_CONFIDENCE = "low_confidence"


REJECTION_REASONS = frozenset(
    {
        QualityReason.NO_TARGET_SPEECH,
        QualityReason.LANGUAGE_MISMATCH,
        QualityReason.UNREADABLE_AUDIO,
    }
)
PARTIAL_REASONS = frozenset(
    {QualityReason.TOO_FEW_WORDS, QualityReason.TOO_SHORT, QualityReason.LOW_CONFIDENCE}
)


class MarkerId(StrEnum):
    """Language markers computed by step 1 (definitions in docs/specs/pipeline.md)."""

    # In the change index
    PRONOUN_INDEX = "pronoun_index"
    NOUN_RATIO = "noun_ratio"
    MEAN_WORD_FREQUENCY = "mean_word_frequency"
    MEAN_WORD_LENGTH = "mean_word_length"
    MAZE_INDEX = "maze_index"
    SPEECH_RATE_WPM = "speech_rate_wpm"
    # Displayed for context, not in the change index
    PAUSES_BETWEEN_PER100W = "pauses_between_per100w"
    PAUSES_WITHIN_PER100W = "pauses_within_per100w"
    MATTR_50 = "mattr_50"


class MarkerFamily(StrEnum):
    SEMANTIC = "semantic"
    FLUENCY = "fluency"
    LEXICAL = "lexical"


class DeclineDirection(StrEnum):
    """Direction in which a marker moves with cognitive decline, per the literature."""

    INCREASE = "increase"
    DECREASE = "decrease"
    UNCERTAIN = "uncertain"


class StudyRef(StrEnum):
    """Study notes that generated text may cite (docs/discovery/studies/)."""

    SNOWDON_1996 = "01-snowdon-1996"
    FRASER_2016 = "02-fraser-2016"
    GARRARD_2005 = "03-garrard-2005"
    AGBAVOR_2022 = "04-agbavor-2022"
    DE_LA_FUENTE_GARCIA_2020 = "05-de-la-fuente-garcia-2020"
    PISTONO_2016 = "06-pistono-2016"
    MURPHY_2008 = "07-murphy-2008"
    MUELLER_2018 = "08-mueller-2018"
    ROBIN_2023 = "09-robin-2023"
    KEMPER_2001 = "10-kemper-2001"


class LifePeriod(StrEnum):
    CHILDHOOD = "childhood"
    ADOLESCENCE = "adolescence"
    YOUNG_ADULTHOOD = "young_adulthood"
    MIDDLE_ADULTHOOD = "middle_adulthood"
    LATER_LIFE = "later_life"
    UNSPECIFIED = "unspecified"


class RepetitionScope(StrEnum):
    WITHIN_SESSION = "within_session"
    ACROSS_SESSIONS = "across_sessions"


class OrientationLevel(StrEnum):
    BUILDING_BASELINE = "building_baseline"
    STABLE = "stable"
    MONITOR = "monitor"
    REVIEW_RECOMMENDED = "review_recommended"


class OrientationRule(StrEnum):
    """Which rule of docs/specs/pipeline.md (step 3) produced the orientation level."""

    INSUFFICIENT_BASELINE = "insufficient_baseline"
    NOT_SIGNIFICANT = "not_significant"
    SINGLE_SIGNIFICANT = "single_significant"
    ADVERSE_CONTEXT_CAPPED = "adverse_context_capped"
    PERSISTENT_TWO_SESSIONS = "persistent_two_sessions"
    RAPID_DROP = "rapid_drop"
    CARRIED_OVER = "carried_over"
    """The session is not usable: the previous level is kept unchanged."""


class SuggestedAction(StrEnum):
    CONTINUE_BASELINE = "continue_baseline"
    ROUTINE_FOLLOW_UP = "routine_follow_up"
    REPEAT_WITHIN_TWO_WEEKS = "repeat_within_two_weeks"
    PROFESSIONAL_REVIEW = "professional_review"


class ReviewStatus(StrEnum):
    DRAFT = "draft"
    VALIDATED = "validated"


class GenerationMode(StrEnum):
    LLM = "llm"
    TEMPLATE_FALLBACK = "template_fallback"


LEVEL_ACTIONS: dict[OrientationLevel, SuggestedAction] = {
    OrientationLevel.BUILDING_BASELINE: SuggestedAction.CONTINUE_BASELINE,
    OrientationLevel.STABLE: SuggestedAction.ROUTINE_FOLLOW_UP,
    OrientationLevel.MONITOR: SuggestedAction.REPEAT_WITHIN_TWO_WEEKS,
    OrientationLevel.REVIEW_RECOMMENDED: SuggestedAction.PROFESSIONAL_REVIEW,
}
"""Action attached to each level. Decided by step 3, never by an LLM."""

LEVEL_RULES: dict[OrientationLevel, frozenset[OrientationRule]] = {
    OrientationLevel.BUILDING_BASELINE: frozenset({OrientationRule.INSUFFICIENT_BASELINE}),
    OrientationLevel.STABLE: frozenset({OrientationRule.NOT_SIGNIFICANT}),
    OrientationLevel.MONITOR: frozenset(
        {OrientationRule.SINGLE_SIGNIFICANT, OrientationRule.ADVERSE_CONTEXT_CAPPED}
    ),
    OrientationLevel.REVIEW_RECOMMENDED: frozenset(
        {OrientationRule.PERSISTENT_TWO_SESSIONS, OrientationRule.RAPID_DROP}
    ),
}
"""Rules that may produce each level (CARRIED_OVER is valid for every level)."""

# ---------------------------------------------------------------------------
# Input: recording metadata
# ---------------------------------------------------------------------------


class RecordingContext(ContractModel):
    """Session context entered by the clinician (docs/specs/clinician-ui.md, screen 4).

    Context weighs the reliability of a session; it is not a risk factor (hypothesis H9).
    """

    sleep: SleepQuality | None = None
    fatigue: bool | None = None
    acute_illness: bool | None = None
    new_medication: bool | None = None
    mood: Mood | None = None

    @property
    def is_adverse(self) -> bool:
        """True when any field signals a less reliable session.

        Design choice validated on 2026-11-12, not backed by a study (H9; Q32).
        """
        return (
            self.sleep is SleepQuality.POOR
            or self.fatigue is True
            or self.acute_illness is True
            or self.new_medication is True
            or self.mood is Mood.LOW
        )


class RecordingMetadata(ContractModel):
    """Everything that comes with an audio recording, from the UI or an integration."""

    person_id: Identifier
    task_type: TaskType
    language: LanguageCode
    consent: Literal[True] = Field(description="A recording without consent is refused.")
    recorded_at: AwareDatetime
    source: RecordingSource
    context: RecordingContext = Field(default_factory=RecordingContext)
    prompt_id: Identifier | None = None
    target_speaker_hint: Identifier | None = None
    synthetic: bool = False


# ---------------------------------------------------------------------------
# Step 0: capture and quality
# ---------------------------------------------------------------------------


class TranscriptToken(ContractModel):
    """One word or audio event from Scribe, with times in seconds."""

    text: NonEmptyText
    kind: TokenKind
    start_s: NonNegativeFloat
    end_s: NonNegativeFloat
    speaker_id: Identifier
    logprob: LogProb | None = None

    @model_validator(mode="after")
    def _end_not_before_start(self) -> Self:
        if self.end_s < self.start_s:
            raise ValueError("end_s must be greater than or equal to start_s")
        return self


class SessionTranscript(SessionScoped):
    """Verbatim, word-timed transcript of one session (all speakers)."""

    language: LanguageCode
    language_probability: Proportion
    audio_duration_s: NonNegativeFloat
    target_speaker_id: Identifier | None = Field(
        description="Speaker analysed by the pipeline; None when nobody speaks."
    )
    tokens: tuple[TranscriptToken, ...]

    @model_validator(mode="after")
    def _tokens_in_time_order(self) -> Self:
        if any(b.start_s < a.start_s for a, b in pairwise(self.tokens)):
            raise ValueError("tokens must be sorted by start_s")
        return self


class QualityReport(SessionScoped):
    """Outcome of the step 0 quality control (docs/specs/pipeline.md, step 0)."""

    status: QualityStatus
    reasons: tuple[QualityReason, ...] = ()
    target_word_count: NonNegativeInt
    target_speaking_time_s: NonNegativeFloat
    target_speech_share: Proportion
    mean_logprob: LogProb | None = None

    @model_validator(mode="after")
    def _status_matches_reasons(self) -> Self:
        reasons = set(self.reasons)
        if len(reasons) != len(self.reasons):
            raise ValueError("quality reasons must not repeat")
        if self.status is QualityStatus.USABLE and reasons:
            raise ValueError("a usable session cannot carry quality reasons")
        if self.status is QualityStatus.REJECTED and not reasons & REJECTION_REASONS:
            raise ValueError("a rejected session needs at least one rejection reason")
        if self.status is QualityStatus.PARTIAL and (
            reasons & REJECTION_REASONS or not reasons & PARTIAL_REASONS
        ):
            raise ValueError("a partial session needs partial reasons and no rejection reason")
        return self


# ---------------------------------------------------------------------------
# Step 1: markers
# ---------------------------------------------------------------------------


class MarkerSpec(ContractModel):
    """Static description of a marker, shown to clinicians (definition and sources)."""

    marker: MarkerId
    family: MarkerFamily
    decline_direction: DeclineDirection
    in_change_index: bool
    definition: NonEmptyText
    sources: tuple[StudyRef, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _index_markers_have_a_direction(self) -> Self:
        if self.in_change_index and self.decline_direction is DeclineDirection.UNCERTAIN:
            raise ValueError("a marker with an uncertain direction cannot enter the index")
        return self


class MarkerValue(ContractModel):
    """Value of one marker for one session; None when it cannot be computed."""

    marker: MarkerId
    value: float | None
    n_units: NonNegativeInt = Field(description="Count the value is computed on.")


class SessionMetrics(SessionScoped):
    """All marker values of one session (target speaker only)."""

    markers: tuple[MarkerValue, ...]

    @model_validator(mode="after")
    def _markers_unique(self) -> Self:
        ids = [m.marker for m in self.markers]
        if len(set(ids)) != len(ids):
            raise ValueError("each marker may appear only once")
        return self

    def value_of(self, marker: MarkerId) -> float | None:
        """Return the value of ``marker``, or None if absent or not computable."""
        for item in self.markers:
            if item.marker is marker:
                return item.value
        return None


# ---------------------------------------------------------------------------
# Step 2: narrative analyst (experimental, outside the change index)
# ---------------------------------------------------------------------------


class Episode(ContractModel):
    episode_id: Identifier
    summary: NonEmptyText
    life_period: LifePeriod
    people: tuple[NonEmptyText, ...] = ()
    places: tuple[NonEmptyText, ...] = ()
    time_references: tuple[NonEmptyText, ...] = ()
    utterance_indices: tuple[NonNegativeInt, ...] = Field(min_length=1)


class Repetition(ContractModel):
    """An anecdote told again, in the same session or a previous one (Cook 2009)."""

    episode_id: Identifier
    scope: RepetitionScope
    previous_session_id: Identifier | None = None
    previous_episode_id: Identifier
    self_flagged: bool = Field(description="The person says they already told it.")
    rationale: NonEmptyText
    quoted_passages: tuple[NonEmptyText, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _scope_matches_session(self) -> Self:
        across = self.scope is RepetitionScope.ACROSS_SESSIONS
        if across and self.previous_session_id is None:
            raise ValueError("an across-session repetition needs previous_session_id")
        if not across and self.previous_session_id is not None:
            raise ValueError("a within-session repetition has no previous_session_id")
        return self


class NarrativeAnalysis(SessionScoped):
    """Output of step 2. Always experimental; never enters the change index."""

    experimental: Literal[True] = True
    model_id: Identifier
    episodes: tuple[Episode, ...]
    repetitions: tuple[Repetition, ...] = ()

    @model_validator(mode="after")
    def _repetitions_point_to_episodes(self) -> Self:
        known = {e.episode_id for e in self.episodes}
        if len(known) != len(self.episodes):
            raise ValueError("episode ids must be unique")
        for rep in self.repetitions:
            if rep.episode_id not in known:
                raise ValueError(f"repetition refers to unknown episode {rep.episode_id!r}")
            within = rep.scope is RepetitionScope.WITHIN_SESSION
            if within and rep.previous_episode_id not in known:
                raise ValueError("a within-session repetition must refer to an episode here")
        return self


# ---------------------------------------------------------------------------
# Step 3: longitudinal drift
# ---------------------------------------------------------------------------


class AnalysedSession(ContractModel):
    """What step 3 needs about one session: its metadata and the outputs of steps 0 and 1."""

    metadata: RecordingMetadata
    quality: QualityReport
    metrics: SessionMetrics | None = Field(description="None for a rejected session.")

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if self.quality.person_id != self.metadata.person_id:
            raise ValueError("quality report and metadata refer to different persons")
        if self.metrics is None:
            if self.quality.status is not QualityStatus.REJECTED:
                raise ValueError("only a rejected session may have no metrics")
        elif (self.metrics.session_id, self.metrics.person_id) != (
            self.quality.session_id,
            self.quality.person_id,
        ):
            raise ValueError("metrics and quality report refer to different sessions")
        return self

    @property
    def session_id(self) -> str:
        return self.quality.session_id


class MarkerBaseline(ContractModel):
    marker: MarkerId
    mean: float
    sd: NonNegativeFloat
    n: NonNegativeInt


class BaselineReference(ContractModel):
    """Personal reference: the first 3 to 5 usable sessions of one task type."""

    task_type: TaskType
    session_ids: tuple[Identifier, ...] = Field(
        min_length=MIN_BASELINE_SESSIONS, max_length=MAX_BASELINE_SESSIONS
    )
    is_frozen: bool
    markers: tuple[MarkerBaseline, ...]
    change_index_values: tuple[float, ...] = Field(
        description="Change index of each baseline session, in session_ids order."
    )

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if len(set(self.session_ids)) != len(self.session_ids):
            raise ValueError("baseline session ids must be unique")
        if len(self.change_index_values) != len(self.session_ids):
            raise ValueError("one change index value is needed per baseline session")
        ids = [m.marker for m in self.markers]
        if len(set(ids)) != len(ids):
            raise ValueError("each marker may appear only once in the baseline")
        if len(self.session_ids) == MAX_BASELINE_SESSIONS and not self.is_frozen:
            raise ValueError(f"a baseline of {MAX_BASELINE_SESSIONS} sessions must be frozen")
        return self


class SignificanceTest(ContractModel):
    """One-sided single-case t-test of one marker against the personal baseline.

    Modified t-test for comparing one case with a small sample (Crawford & Howell, 1998),
    as extended by Crawford JR, Garthwaite PH (2002), Neuropsychologia 40(8):1196-1208,
    DOI 10.1016/s0028-3932(01)00224-x, PMID 11931923. Here the small sample is the
    person's own baseline sessions. ``t`` is oriented so that positive values point
    toward decline; ``significant`` means it reaches the one-sided 0.05 critical value
    of Student's t with ``df`` degrees of freedom (conventional threshold).
    """

    t: float
    df: int = Field(ge=MIN_BASELINE_SESSIONS - 1, le=MAX_BASELINE_SESSIONS - 1)
    significant: bool


class MarkerDeviation(ContractModel):
    marker: MarkerId
    value: float | None
    baseline_mean: float
    baseline_sd: NonNegativeFloat
    test: SignificanceTest | None = Field(
        description=(
            "None when the marker cannot be tested: missing value, baseline without "
            "variance, or uncertain direction of decline."
        )
    )


class ChangeIndexScore(ContractModel):
    """How far a session sits from the personal baseline.

    ``value`` is the mean of the oriented z-scores of the tested markers, with equal
    weights (composite method of Robin 2023, study note 09). It is in units of the
    person's own variability: 0 means "as usual", positive values point toward decline.
    It is displayed as "Change from baseline". The orientation level is decided on the
    number of significant markers, not on this value (docs/specs/pipeline.md, step 3).
    """

    value: float
    tested_markers: tuple[MarkerId, ...] = Field(min_length=1)
    significant_markers: tuple[MarkerId, ...] = ()

    @model_validator(mode="after")
    def _significant_markers_were_tested(self) -> Self:
        if len(set(self.tested_markers)) != len(self.tested_markers):
            raise ValueError("tested markers must not repeat")
        if len(set(self.significant_markers)) != len(self.significant_markers):
            raise ValueError("significant markers must not repeat")
        if not set(self.significant_markers) <= set(self.tested_markers):
            raise ValueError("a significant marker must be among the tested markers")
        return self

    @property
    def is_in_deviation(self) -> bool:
        return len(self.significant_markers) >= MIN_SIGNIFICANT_MARKERS

    @property
    def is_rapid_drop(self) -> bool:
        return len(self.significant_markers) >= RAPID_DROP_MARKERS


class FamilyScore(ContractModel):
    """Mean oriented z-score of the index markers of one family (display only)."""

    family: MarkerFamily
    value: float


class OrientationDecision(ContractModel):
    level: OrientationLevel
    rule: OrientationRule
    suggested_action: SuggestedAction

    @model_validator(mode="after")
    def _rule_and_action_match_level(self) -> Self:
        if (
            self.rule is not OrientationRule.CARRIED_OVER
            and self.rule not in LEVEL_RULES[self.level]
        ):
            raise ValueError(f"rule {self.rule} cannot produce level {self.level}")
        if self.suggested_action is not LEVEL_ACTIONS[self.level]:
            raise ValueError(f"level {self.level} requires action {LEVEL_ACTIONS[self.level]}")
        return self


class Uncertainty(ContractModel):
    """What the clinician must see next to every score (CLAUDE.md, clinical rule 5)."""

    baseline_session_count: NonNegativeInt
    baseline_change_index_range: tuple[float, float] | None = None
    quality_status: QualityStatus
    adverse_context: bool


class LongitudinalComparisonResult(SessionScoped):
    """Output of step 3 for one session."""

    task_type: TaskType
    baseline: BaselineReference | None
    markers: tuple[MarkerDeviation, ...] = ()
    change_index: ChangeIndexScore | None = None
    family_scores: tuple[FamilyScore, ...] = ()
    orientation: OrientationDecision
    uncertainty: Uncertainty

    @model_validator(mode="after")
    def _clinical_rules(self) -> Self:
        level = self.orientation.level
        rule = self.orientation.rule
        quality = self.uncertainty.quality_status

        if quality is QualityStatus.REJECTED:
            raise ValueError("a rejected session has no longitudinal comparison")
        if quality is QualityStatus.PARTIAL and rule not in {
            OrientationRule.CARRIED_OVER,
            OrientationRule.INSUFFICIENT_BASELINE,
        }:
            raise ValueError("a partial session cannot change the orientation level")
        if rule is OrientationRule.CARRIED_OVER:
            if quality is QualityStatus.USABLE:
                raise ValueError("only a non-usable session carries the previous level over")
            return self

        # Clinical rule 5: no level without a baseline of MIN_BASELINE_SESSIONS sessions.
        if level is OrientationLevel.BUILDING_BASELINE:
            if self.uncertainty.baseline_session_count >= MIN_BASELINE_SESSIONS:
                raise ValueError("building_baseline requires fewer baseline sessions")
            return self
        if self.baseline is None:
            raise ValueError(f"level {level} requires a personal baseline")
        if self.uncertainty.baseline_session_count != len(self.baseline.session_ids):
            raise ValueError("baseline_session_count must match the baseline")
        if self.change_index is None:
            raise ValueError(f"level {level} requires a change index")

        # The level cannot contradict the measurements it is based on.
        if rule is OrientationRule.ADVERSE_CONTEXT_CAPPED and not self.uncertainty.adverse_context:
            raise ValueError("adverse_context_capped requires an adverse context")
        if self.change_index.is_in_deviation is (rule is OrientationRule.NOT_SIGNIFICANT):
            raise ValueError(f"rule {rule} contradicts the number of significant markers")
        if rule is OrientationRule.RAPID_DROP and not self.change_index.is_rapid_drop:
            raise ValueError(f"rapid_drop requires {RAPID_DROP_MARKERS} significant markers")
        return self


# ---------------------------------------------------------------------------
# Step 4: clinical summary
# ---------------------------------------------------------------------------

FORBIDDEN_DIAGNOSTIC_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bdiagnos\w*",  # diagnosis, diagnose(d), diagnostic
        r"\bhas\s+alzheimer(?:'s)?\b",
        r"\bhas\s+dementia\b",
        r"\bdementia\s+(?:is\s+)?confirmed\b",
        r"\bconfirmed\s+dementia\b",
    )
)
"""English counterpart of the vocabulary forbidden by CLAUDE.md, clinical rule 1."""


def find_diagnostic_terms(text: str) -> list[str]:
    """Return the forbidden diagnostic expressions found in ``text`` (empty if none)."""
    return [m.group(0) for p in FORBIDDEN_DIAGNOSTIC_PATTERNS for m in p.finditer(text)]


class Finding(ContractModel):
    """One statement of the clinician summary, always tied to at least one marker."""

    text: NonEmptyText
    marker_ids: tuple[MarkerId, ...] = Field(min_length=1)
    passages: tuple[NonEmptyText, ...] = ()
    study_refs: tuple[StudyRef, ...] = ()


class ClinicianSummary(ContractModel):
    headline: NonEmptyText
    findings: tuple[Finding, ...]
    uncertainty_statement: NonEmptyText
    suggested_action: SuggestedAction


class PreventionNote(ContractModel):
    factor: NonEmptyText
    suggestion: NonEmptyText
    source: NonEmptyText = Field(description="Full citation of a verified reference.")


class ReviewRecord(ContractModel):
    """Human oversight: a summary stays a draft until a clinician validates it."""

    status: ReviewStatus = ReviewStatus.DRAFT
    reviewed_by: NonEmptyText | None = None
    reviewed_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def _reviewer_iff_validated(self) -> Self:
        has_reviewer = self.reviewed_by is not None and self.reviewed_at is not None
        if self.status is ReviewStatus.VALIDATED and not has_reviewer:
            raise ValueError("a validated summary needs reviewed_by and reviewed_at")
        if self.status is ReviewStatus.DRAFT and (
            self.reviewed_by is not None or self.reviewed_at is not None
        ):
            raise ValueError("a draft summary has no reviewer")
        return self


class ClinicalSummaryReport(SessionScoped):
    """Output of step 4: non-diagnostic summary for the clinician and the person."""

    orientation_level: OrientationLevel
    clinician_summary: ClinicianSummary
    person_explanation: NonEmptyText
    prevention_notes: tuple[PreventionNote, ...] = ()
    review: ReviewRecord = Field(default_factory=ReviewRecord)
    generation_mode: GenerationMode
    model_id: Identifier | None = None

    @model_validator(mode="after")
    def _safe_and_consistent(self) -> Self:
        expected = LEVEL_ACTIONS[self.orientation_level]
        if self.clinician_summary.suggested_action is not expected:
            raise ValueError(f"level {self.orientation_level} requires action {expected}")
        if self.generation_mode is GenerationMode.LLM and self.model_id is None:
            raise ValueError("an LLM-generated summary must record its model_id")

        texts = [
            self.clinician_summary.headline,
            self.clinician_summary.uncertainty_statement,
            self.person_explanation,
            *(f.text for f in self.clinician_summary.findings),
            *(n.suggestion for n in self.prevention_notes),
        ]
        found = sorted({term for text in texts for term in find_diagnostic_terms(text)})
        if found:
            raise ValueError(f"diagnostic vocabulary is forbidden (CLAUDE.md rule 1): {found}")
        return self


# ---------------------------------------------------------------------------
# Risk profile (displayed next to the score, never mixed into it)
# ---------------------------------------------------------------------------


class RiskFactorEntry(ContractModel):
    factor: NonEmptyText
    value: NonEmptyText | None = None
    shared: bool = Field(description="Whether the person authorised sharing this item.")

    @model_validator(mode="after")
    def _no_value_when_not_shared(self) -> Self:
        if not self.shared and self.value is not None:
            raise ValueError("an item that is not shared cannot carry a value")
        return self


class RiskProfile(ContractModel):
    person_id: Identifier
    entries: tuple[RiskFactorEntry, ...]
    synthetic: bool = False
