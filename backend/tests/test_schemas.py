"""Tests for the pipeline contracts, focused on the invariants they enforce."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from app.schemas import (
    MIN_BASELINE_SESSIONS,
    AnalysedSession,
    BaselineReference,
    ChangeIndexScore,
    ClinicalSummaryReport,
    ClinicianSummary,
    Finding,
    GenerationMode,
    LongitudinalComparisonResult,
    MarkerId,
    MarkerValue,
    Mood,
    NarrativeAnalysis,
    OrientationDecision,
    OrientationLevel,
    OrientationRule,
    QualityReason,
    QualityReport,
    QualityStatus,
    RecordingContext,
    RecordingMetadata,
    RecordingSource,
    Repetition,
    RepetitionScope,
    ReviewRecord,
    ReviewStatus,
    RiskFactorEntry,
    SessionMetrics,
    SessionTranscript,
    SleepQuality,
    SuggestedAction,
    TaskType,
    TokenKind,
    TranscriptToken,
    Uncertainty,
    find_diagnostic_terms,
)

NOW = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
IDS = {"session_id": "s-1", "person_id": "p-1", "synthetic": True}


# --- builders ---------------------------------------------------------------


def _metadata(**overrides: Any) -> RecordingMetadata:
    fields: dict[str, Any] = {
        "person_id": "p-1",
        "task_type": TaskType.LIFE_STORY,
        "language": "eng",
        "consent": True,
        "recorded_at": NOW,
        "source": RecordingSource.CLINICIAN_UI,
    }
    fields.update(overrides)
    return RecordingMetadata.model_validate(fields)


def _token(text: str, start: float, end: float, speaker: str = "speaker_0") -> TranscriptToken:
    return TranscriptToken(
        text=text, kind=TokenKind.WORD, start_s=start, end_s=end, speaker_id=speaker
    )


INDEX_MARKERS = (
    MarkerId.PRONOUN_INDEX,
    MarkerId.NOUN_RATIO,
    MarkerId.MEAN_WORD_FREQUENCY,
    MarkerId.MEAN_WORD_LENGTH,
    MarkerId.MAZE_INDEX,
    MarkerId.SPEECH_RATE_WPM,
)


def _index(significant: int = 0) -> ChangeIndexScore:
    """Change index with the first ``significant`` index markers significant."""
    return ChangeIndexScore(
        value=0.4, tested_markers=INDEX_MARKERS, significant_markers=INDEX_MARKERS[:significant]
    )


def _baseline(n: int = 3) -> BaselineReference:
    return BaselineReference(
        task_type=TaskType.LIFE_STORY,
        session_ids=tuple(f"s-b{i}" for i in range(n)),
        is_frozen=n == 5,
        markers=(),
        change_index_values=tuple(0.0 for _ in range(n)),
    )


def _comparison(
    level: OrientationLevel,
    rule: OrientationRule,
    *,
    baseline: BaselineReference | None,
    baseline_count: int,
    quality: QualityStatus = QualityStatus.USABLE,
    adverse: bool = False,
    significant: int | None = None,
    with_index: bool = True,
) -> LongitudinalComparisonResult:
    if significant is None:
        significant = {
            OrientationRule.RAPID_DROP: 4,
            OrientationRule.SINGLE_SIGNIFICANT: 2,
            OrientationRule.PERSISTENT_TWO_SESSIONS: 2,
            OrientationRule.ADVERSE_CONTEXT_CAPPED: 2,
        }.get(rule, 0)
    level_actions = {
        OrientationLevel.BUILDING_BASELINE: SuggestedAction.CONTINUE_BASELINE,
        OrientationLevel.STABLE: SuggestedAction.ROUTINE_FOLLOW_UP,
        OrientationLevel.MONITOR: SuggestedAction.REPEAT_WITHIN_TWO_WEEKS,
        OrientationLevel.REVIEW_RECOMMENDED: SuggestedAction.PROFESSIONAL_REVIEW,
    }
    return LongitudinalComparisonResult(
        **IDS,
        task_type=TaskType.LIFE_STORY,
        baseline=baseline,
        change_index=_index(significant) if with_index else None,
        orientation=OrientationDecision(
            level=level, rule=rule, suggested_action=level_actions[level]
        ),
        uncertainty=Uncertainty(
            baseline_session_count=baseline_count,
            quality_status=quality,
            adverse_context=adverse,
        ),
    )


def _summary(text: str = "Signals to monitor in the semantic markers.") -> ClinicalSummaryReport:
    return ClinicalSummaryReport(
        **IDS,
        orientation_level=OrientationLevel.MONITOR,
        clinician_summary=ClinicianSummary(
            headline="Change from personal baseline",
            findings=(
                Finding(text=text, beyond_usual_range=True, marker_ids=(MarkerId.PRONOUN_INDEX,)),
            ),
            uncertainty_statement="Baseline of 3 sessions; one session above threshold.",
            suggested_action=SuggestedAction.REPEAT_WITHIN_TWO_WEEKS,
        ),
        person_explanation="Your way of telling stories changed a little this time.",
        generation_mode=GenerationMode.LLM,
        model_id="claude-opus-5-5",
    )


# --- RecordingMetadata ------------------------------------------------------


def test_recording_requires_consent() -> None:
    with pytest.raises(ValidationError):
        _metadata(consent=False)


def test_recording_requires_iso_639_3_language() -> None:
    assert _metadata(language="eng").language == "eng"
    with pytest.raises(ValidationError):
        _metadata(language="en")


def test_recording_requires_timezone_aware_datetime() -> None:
    with pytest.raises(ValidationError):
        _metadata(recorded_at=datetime(2026, 11, 12, 10, 0))


def test_contracts_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        _metadata(unexpected="value")


def test_contracts_are_immutable() -> None:
    metadata = _metadata()
    with pytest.raises(ValidationError):
        metadata.language = "fra"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("context", "adverse"),
    [
        (RecordingContext(), False),
        (RecordingContext(sleep=SleepQuality.GOOD, mood=Mood.GOOD, fatigue=False), False),
        (RecordingContext(sleep=SleepQuality.POOR), True),
        (RecordingContext(new_medication=True), True),
        (RecordingContext(mood=Mood.LOW), True),
    ],
)
def test_adverse_context(context: RecordingContext, adverse: bool) -> None:
    assert context.is_adverse is adverse


def test_metadata_round_trips_through_json() -> None:
    metadata = _metadata(context=RecordingContext(sleep=SleepQuality.POOR))
    assert RecordingMetadata.model_validate_json(metadata.model_dump_json()) == metadata


# --- Step 0 -----------------------------------------------------------------


def test_token_end_cannot_precede_start() -> None:
    with pytest.raises(ValidationError):
        _token("hello", start=1.0, end=0.5)


def test_transcript_tokens_must_be_chronological() -> None:
    with pytest.raises(ValidationError):
        SessionTranscript(
            **IDS,
            language="eng",
            language_probability=0.98,
            audio_duration_s=3.0,
            target_speaker_id="speaker_0",
            tokens=(_token("world", 1.0, 1.4), _token("hello", 0.2, 0.6)),
        )


def test_quality_usable_has_no_reasons() -> None:
    with pytest.raises(ValidationError):
        QualityReport(
            **IDS,
            status=QualityStatus.USABLE,
            reasons=(QualityReason.TOO_SHORT,),
            target_word_count=600,
            target_speaking_time_s=280.0,
            target_speech_share=0.9,
        )


def test_quality_rejected_needs_a_rejection_reason() -> None:
    with pytest.raises(ValidationError):
        QualityReport(
            **IDS,
            status=QualityStatus.REJECTED,
            reasons=(QualityReason.TOO_FEW_WORDS,),
            target_word_count=40,
            target_speaking_time_s=20.0,
            target_speech_share=0.5,
        )


def test_quality_partial_with_partial_reason_is_valid() -> None:
    report = QualityReport(
        **IDS,
        status=QualityStatus.PARTIAL,
        reasons=(QualityReason.TOO_FEW_WORDS, QualityReason.TOO_SHORT),
        target_word_count=120,
        target_speaking_time_s=70.0,
        target_speech_share=0.8,
    )
    assert report.status is QualityStatus.PARTIAL


# --- Step 1 -----------------------------------------------------------------


def test_metrics_reject_duplicate_markers() -> None:
    value = MarkerValue(marker=MarkerId.NOUN_RATIO, value=0.2, n_units=500)
    with pytest.raises(ValidationError):
        SessionMetrics(**IDS, markers=(value, value))


def test_metrics_value_lookup() -> None:
    metrics = SessionMetrics(
        **IDS,
        markers=(
            MarkerValue(marker=MarkerId.NOUN_RATIO, value=0.2, n_units=500),
            MarkerValue(marker=MarkerId.MATTR_50, value=None, n_units=120),
        ),
    )
    assert metrics.value_of(MarkerId.NOUN_RATIO) == 0.2
    assert metrics.value_of(MarkerId.MATTR_50) is None
    assert metrics.value_of(MarkerId.SPEECH_RATE_WPM) is None


# --- Step 2 -----------------------------------------------------------------


def test_across_session_repetition_needs_previous_session() -> None:
    with pytest.raises(ValidationError):
        Repetition(
            episode_id="e-1",
            scope=RepetitionScope.ACROSS_SESSIONS,
            previous_episode_id="e-old",
            self_flagged=False,
            rationale="Same wedding story as two weeks ago.",
            quoted_passages=("we danced all night at the wedding",),
        )


def test_narrative_repetition_must_point_to_known_episode() -> None:
    repetition = Repetition(
        episode_id="e-unknown",
        scope=RepetitionScope.ACROSS_SESSIONS,
        previous_session_id="s-0",
        previous_episode_id="e-old",
        self_flagged=True,
        acknowledgement_quote="I told you this before",
        rationale="Told again.",
        quoted_passages=("I told you this before",),
    )
    with pytest.raises(ValidationError):
        NarrativeAnalysis(**IDS, model_id="claude-opus-5-5", episodes=(), repetitions=(repetition,))


@pytest.mark.parametrize(
    "fields",
    [
        # Said to be acknowledged, with no words to show for it.
        {"self_flagged": True},
        # Words of acknowledgement, on a repetition said not to be acknowledged.
        {"self_flagged": False, "acknowledgement_quote": "I told you this before"},
        # An episode told again from itself.
        {"self_flagged": False, "previous_episode_id": "e-1"},
    ],
)
def test_repetition_claims_must_hold_together(fields: dict[str, object]) -> None:
    base: dict[str, object] = {
        "episode_id": "e-1",
        "scope": RepetitionScope.WITHIN_SESSION,
        "previous_episode_id": "e-0",
        "rationale": "Told again.",
        "quoted_passages": ("we danced all night",),
    }
    with pytest.raises(ValidationError):
        Repetition.model_validate(base | fields)


# --- Step 3: clinical rule 5 ------------------------------------------------


def test_building_baseline_needs_no_baseline_and_no_index() -> None:
    result = _comparison(
        OrientationLevel.BUILDING_BASELINE,
        OrientationRule.INSUFFICIENT_BASELINE,
        baseline=None,
        baseline_count=1,
        with_index=False,
    )
    assert result.orientation.level is OrientationLevel.BUILDING_BASELINE


@pytest.mark.parametrize(
    "level",
    [OrientationLevel.STABLE, OrientationLevel.MONITOR, OrientationLevel.REVIEW_RECOMMENDED],
)
def test_no_orientation_level_without_baseline(level: OrientationLevel) -> None:
    rule = {
        OrientationLevel.STABLE: OrientationRule.NOT_SIGNIFICANT,
        OrientationLevel.MONITOR: OrientationRule.SINGLE_SIGNIFICANT,
        OrientationLevel.REVIEW_RECOMMENDED: OrientationRule.PERSISTENT_TWO_SESSIONS,
    }[level]
    with pytest.raises(ValidationError):
        _comparison(level, rule, baseline=None, baseline_count=MIN_BASELINE_SESSIONS - 1)


def test_baseline_needs_at_least_three_sessions() -> None:
    with pytest.raises(ValidationError):
        _baseline(n=MIN_BASELINE_SESSIONS - 1)


def test_baseline_of_five_sessions_must_be_frozen() -> None:
    with pytest.raises(ValidationError):
        BaselineReference(
            task_type=TaskType.LIFE_STORY,
            session_ids=tuple(f"s-b{i}" for i in range(5)),
            is_frozen=False,
            markers=(),
            change_index_values=(0.0,) * 5,
        )


def test_review_with_baseline_is_valid() -> None:
    result = _comparison(
        OrientationLevel.REVIEW_RECOMMENDED,
        OrientationRule.RAPID_DROP,
        baseline=_baseline(),
        baseline_count=3,
    )
    assert result.orientation.suggested_action is SuggestedAction.PROFESSIONAL_REVIEW


def test_partial_session_cannot_change_the_level() -> None:
    with pytest.raises(ValidationError):
        _comparison(
            OrientationLevel.MONITOR,
            OrientationRule.SINGLE_SIGNIFICANT,
            baseline=_baseline(),
            baseline_count=3,
            quality=QualityStatus.PARTIAL,
        )


def test_adverse_cap_requires_adverse_context() -> None:
    with pytest.raises(ValidationError):
        _comparison(
            OrientationLevel.MONITOR,
            OrientationRule.ADVERSE_CONTEXT_CAPPED,
            baseline=_baseline(),
            baseline_count=3,
            adverse=False,
        )


def test_orientation_action_is_fixed_by_level() -> None:
    with pytest.raises(ValidationError):
        OrientationDecision(
            level=OrientationLevel.MONITOR,
            rule=OrientationRule.SINGLE_SIGNIFICANT,
            suggested_action=SuggestedAction.PROFESSIONAL_REVIEW,
        )


def test_significant_markers_must_be_tested() -> None:
    with pytest.raises(ValidationError):
        ChangeIndexScore(
            value=1.0,
            tested_markers=(MarkerId.NOUN_RATIO,),
            significant_markers=(MarkerId.MAZE_INDEX,),
        )


@pytest.mark.parametrize(
    ("significant", "in_deviation", "rapid_drop"),
    [(0, False, False), (1, False, False), (2, True, False), (3, True, False), (4, True, True)],
)
def test_deviation_and_rapid_drop_follow_the_marker_count(
    significant: int, in_deviation: bool, rapid_drop: bool
) -> None:
    index = _index(significant)

    assert (index.is_in_deviation, index.is_rapid_drop) == (in_deviation, rapid_drop)


@pytest.mark.parametrize(
    ("level", "rule", "significant"),
    [
        # Stable although two markers are significant.
        (OrientationLevel.STABLE, OrientationRule.NOT_SIGNIFICANT, 2),
        # Flagged although a single marker is significant.
        (OrientationLevel.MONITOR, OrientationRule.SINGLE_SIGNIFICANT, 1),
        (OrientationLevel.REVIEW_RECOMMENDED, OrientationRule.PERSISTENT_TWO_SESSIONS, 1),
        # Rapid drop with fewer than four significant markers.
        (OrientationLevel.REVIEW_RECOMMENDED, OrientationRule.RAPID_DROP, 3),
    ],
)
def test_level_cannot_contradict_the_marker_count(
    level: OrientationLevel, rule: OrientationRule, significant: int
) -> None:
    with pytest.raises(ValidationError):
        _comparison(level, rule, baseline=_baseline(), baseline_count=3, significant=significant)


def test_partial_session_can_carry_over_any_level() -> None:
    result = _comparison(
        OrientationLevel.BUILDING_BASELINE,
        OrientationRule.CARRIED_OVER,
        baseline=_baseline(),
        baseline_count=3,
        quality=QualityStatus.PARTIAL,
    )

    assert result.orientation.rule is OrientationRule.CARRIED_OVER


def test_analysed_session_needs_metrics_unless_rejected() -> None:
    usable = QualityReport(
        **IDS,
        status=QualityStatus.USABLE,
        target_word_count=600,
        target_speaking_time_s=280.0,
        target_speech_share=0.9,
    )
    rejected = QualityReport(
        **IDS,
        status=QualityStatus.REJECTED,
        reasons=(QualityReason.NO_TARGET_SPEECH,),
        target_word_count=0,
        target_speaking_time_s=0.0,
        target_speech_share=0.0,
    )

    assert AnalysedSession(metadata=_metadata(), quality=rejected, metrics=None).session_id == "s-1"
    with pytest.raises(ValidationError):
        AnalysedSession(metadata=_metadata(), quality=usable, metrics=None)
    with pytest.raises(ValidationError):
        AnalysedSession(
            metadata=_metadata(),
            quality=usable,
            metrics=SessionMetrics(session_id="other", person_id="p-1", markers=()),
        )


# --- Step 4: clinical rule 1 and human oversight ----------------------------


@pytest.mark.parametrize(
    "text",
    [
        "This suggests a diagnosis of early dementia.",
        "The patient has Alzheimer's.",
        "Dementia confirmed by the speech markers.",
        "Diagnostic signs are present.",
    ],
)
def test_summary_rejects_diagnostic_vocabulary(text: str) -> None:
    assert find_diagnostic_terms(text)
    with pytest.raises(ValidationError):
        _summary(text)


def test_summary_accepts_non_diagnostic_wording() -> None:
    report = _summary("Signals to monitor: a memory clinic consultation may be useful.")
    assert report.review.status is ReviewStatus.DRAFT


def test_finding_needs_a_marker() -> None:
    with pytest.raises(ValidationError):
        Finding(text="Something changed.", beyond_usual_range=True, marker_ids=())


def test_validated_review_needs_reviewer_and_date() -> None:
    with pytest.raises(ValidationError):
        ReviewRecord(status=ReviewStatus.VALIDATED, reviewed_by="Dr Demo")
    record = ReviewRecord(status=ReviewStatus.VALIDATED, reviewed_by="Dr Demo", reviewed_at=NOW)
    assert record.status is ReviewStatus.VALIDATED


def test_llm_summary_records_model_id() -> None:
    data = _summary().model_dump()
    data["model_id"] = None
    with pytest.raises(ValidationError):
        ClinicalSummaryReport.model_validate(data)


# --- Risk profile -----------------------------------------------------------


def test_unshared_risk_item_has_no_value() -> None:
    assert RiskFactorEntry(factor="Genomic data", shared=False).value is None
    with pytest.raises(ValidationError):
        RiskFactorEntry(factor="Genomic data", value="APOE e4", shared=False)
