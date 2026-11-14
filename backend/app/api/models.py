"""Models of the HTTP API (docs/specs/api.md).

The pipeline steps exchange the contracts of app.schemas; this module holds what the
API reads from requests and returns to the frontend, built from those contracts. JSON
is in snake_case, and the frontend types mirror these models.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.schemas import (
    ClinicalSummaryReport,
    Identifier,
    LanguageCode,
    LongitudinalComparisonResult,
    MarkerSpec,
    NarrativeAnalysis,
    NonEmptyText,
    OrientationLevel,
    OrientationRule,
    QualityReport,
    QualityStatus,
    RecordingContext,
    RecordingMetadata,
    RecordingSource,
    RepetitionScope,
    RiskProfile,
    SessionMetrics,
    SuggestedAction,
    TaskType,
    Uncertainty,
)


class ApiModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


Name = Annotated[str, Field(min_length=1, max_length=120)]
BirthYear = Annotated[int, Field(ge=1900, le=2030)]


class SessionStatus(StrEnum):
    """Processing of a session (docs/specs/api.md, section 3)."""

    RECEIVED = "received"
    TRANSCRIBING = "transcribing"
    ANALYSING = "analysing"
    SUMMARISING = "summarising"
    DONE = "done"
    REJECTED = "rejected"
    FAILED = "failed"


IN_PROGRESS = frozenset(
    {
        SessionStatus.RECEIVED,
        SessionStatus.TRANSCRIBING,
        SessionStatus.ANALYSING,
        SessionStatus.SUMMARISING,
    }
)

STEP_LABELS = {
    SessionStatus.RECEIVED: "Received",
    SessionStatus.TRANSCRIBING: "Transcribing",
    SessionStatus.ANALYSING: "Analysing",
    SessionStatus.SUMMARISING: "Writing summary",
    SessionStatus.DONE: "Done",
    SessionStatus.REJECTED: "Rejected by the quality check",
    SessionStatus.FAILED: "Failed",
}


# ---------------------------------------------------------------------------
# People
# ---------------------------------------------------------------------------


class PersonCreate(ApiModel):
    display_name: Name
    birth_year: BirthYear | None = None
    language: LanguageCode = "eng"


class Person(ApiModel):
    person_id: Identifier
    display_name: Name
    birth_year: BirthYear | None = None
    language: LanguageCode
    synthetic: bool = False
    summary: str | None = Field(default=None, description="Short background (personas only).")
    source_app: Identifier | None = None
    external_person_id: Identifier | None = None
    created_at: AwareDatetime


class PersonSummary(ApiModel):
    """One row of the list of people (screen 1)."""

    person_id: Identifier
    display_name: Name
    birth_year: BirthYear | None
    age: int | None
    language: LanguageCode
    synthetic: bool
    last_session_at: AwareDatetime | None
    session_count: int
    usable_session_count: int
    in_progress_count: int
    orientation_level: OrientationLevel
    baseline_session_count: int


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


class SessionUpload(ApiModel):
    """The ``metadata`` part of a session sent from the clinician interface."""

    consent: Literal[True] = Field(description="A recording without consent is refused.")
    context: RecordingContext = Field(default_factory=RecordingContext)
    prompt_id: Identifier | None = None
    recorded_at: AwareDatetime | None = Field(
        default=None, description="Defaults to the time the server receives the recording."
    )
    task_type: TaskType = TaskType.LIFE_STORY


class IntegrationMetadata(ApiModel):
    """The ``metadata`` part of a recording sent by another application (section 5)."""

    source_app: Identifier
    external_person_id: Identifier
    task_type: TaskType = TaskType.LIFE_STORY
    language: LanguageCode
    consent: Literal[True]
    recorded_at: AwareDatetime
    target_speaker_hint: Identifier | None = None
    context: RecordingContext = Field(default_factory=RecordingContext)
    display_name: Name | None = None
    birth_year: BirthYear | None = None


class SessionAccepted(ApiModel):
    session_id: Identifier
    status: SessionStatus
    status_url: str


class SessionStatusView(ApiModel):
    session_id: Identifier
    status: SessionStatus
    step: str
    error: str | None = None


class SessionItem(ApiModel):
    """One session in a list (screen 2, list of sessions)."""

    session_id: Identifier
    person_id: Identifier
    recorded_at: AwareDatetime
    source: RecordingSource
    prompt_id: Identifier | None
    theme: str | None
    status: SessionStatus
    quality_status: QualityStatus | None
    speaking_time_s: float | None
    synthetic: bool


class Prompt(ApiModel):
    prompt_id: Identifier
    theme: NonEmptyText
    question: NonEmptyText
    follow_ups: tuple[NonEmptyText, ...]


# ---------------------------------------------------------------------------
# Annotated transcript (screen 3)
# ---------------------------------------------------------------------------


class TranscriptItemKind(StrEnum):
    WORD = "word"
    FILLER = "filler"
    CUT_OFF = "cut_off"
    AUDIO_EVENT = "audio_event"
    PAUSE = "pause"


class TranscriptItem(ApiModel):
    kind: TranscriptItemKind
    text: str = Field(description="As transcribed; empty for a pause.")
    start_s: float
    end_s: float
    repeated: bool = Field(
        default=False, description="Part of a word or phrase said twice in a row."
    )
    between_utterances: bool | None = Field(
        default=None, description="For a pause: after the end of a sentence."
    )


class TranscriptTurn(ApiModel):
    speaker_id: Identifier
    is_tracked_speaker: bool
    items: tuple[TranscriptItem, ...]


class AnnotatedTranscript(ApiModel):
    target_speaker_id: Identifier | None
    pause_threshold_s: float
    turns: tuple[TranscriptTurn, ...]


class SessionDetail(ApiModel):
    session: SessionItem
    metadata: RecordingMetadata
    prompt: Prompt | None
    error: str | None
    quality: QualityReport | None
    metrics: SessionMetrics | None
    comparison: LongitudinalComparisonResult | None
    narrative: NarrativeAnalysis | None
    summary: ClinicalSummaryReport | None
    transcript: AnnotatedTranscript | None


# ---------------------------------------------------------------------------
# Person detail (screen 2)
# ---------------------------------------------------------------------------


class TrajectoryPoint(ApiModel):
    session_id: Identifier
    recorded_at: AwareDatetime
    quality_status: QualityStatus
    metrics: SessionMetrics | None = Field(
        description="Marker values, also for the sessions that build the baseline."
    )
    comparison: LongitudinalComparisonResult | None = Field(
        description="None for a rejected session, which is only marked on the time axis."
    )


class Trajectory(ApiModel):
    person_id: Identifier
    marker_specs: tuple[MarkerSpec, ...]
    points: tuple[TrajectoryPoint, ...]


class OrientationView(ApiModel):
    """The orientation card: the level of the last compared session, in words."""

    session_id: Identifier
    recorded_at: AwareDatetime
    level: OrientationLevel
    rule: OrientationRule
    rule_text: str
    suggested_action: SuggestedAction
    action_text: str
    uncertainty: Uncertainty
    adverse_context: tuple[str, ...]


class RetoldAnecdote(ApiModel):
    """An anecdote told again, from step 2 (experimental, not in the index)."""

    session_id: Identifier
    recorded_at: AwareDatetime
    episode_summary: str
    scope: RepetitionScope
    previous_session_id: Identifier | None
    previous_recorded_at: AwareDatetime | None
    previous_episode_summary: str | None
    self_flagged: bool
    acknowledgement_quote: str | None
    rationale: str
    quoted_passages: tuple[str, ...]


class PersonDetail(ApiModel):
    person: Person
    age: int | None
    risk_profile: RiskProfile | None
    first_session_at: AwareDatetime | None
    last_session_at: AwareDatetime | None
    orientation: OrientationView | None
    trajectory: Trajectory
    latest_summary: ClinicalSummaryReport | None
    sessions: tuple[SessionItem, ...]
    retold_anecdotes: tuple[RetoldAnecdote, ...]


class ReviewRequest(ApiModel):
    reviewed_by: Name
