"""Tests for step 3: personal baseline, marker tests and orientation levels.

The sessions are built so that results can be checked by hand. Every index marker of
the three baseline sessions sits 1 unit before, at, and 1 unit after 10 in its decline
direction: its baseline mean is 10 and its SD is 1. A later session placed ``d`` units
toward decline on a marker therefore has an oriented z-score of ``d`` and
t = d / sqrt(4 / 3). With 2 degrees of freedom the critical value is 2.92, so
d = 4 is significant (t = 3.46) and d = 3 is not (t = 2.60).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from math import gamma, pi, sqrt

import pytest

from app.agents.drift import T_CRITICAL_05, compare_trajectory, crawford_howell_t
from app.agents.markers import MARKER_SPECS
from app.schemas import (
    AnalysedSession,
    DeclineDirection,
    LongitudinalComparisonResult,
    MarkerFamily,
    MarkerId,
    MarkerValue,
    QualityReason,
    QualityReport,
    QualityStatus,
    RecordingContext,
    RecordingMetadata,
    RecordingSource,
    SessionMetrics,
    SleepQuality,
    SuggestedAction,
    TaskType,
)

INDEX_MARKERS = tuple(m for m, spec in MARKER_SPECS.items() if spec.in_change_index)
SIGN = {
    m: 1.0 if MARKER_SPECS[m].decline_direction is DeclineDirection.INCREASE else -1.0
    for m in INDEX_MARKERS
}
TWO = (MarkerId.PRONOUN_INDEX, MarkerId.MAZE_INDEX)
FOUR = (*TWO, MarkerId.NOUN_RATIO, MarkerId.SPEECH_RATE_WPM)
START = datetime(2026, 6, 1, 10, 0, tzinfo=UTC)
POOR_NIGHT = RecordingContext(sleep=SleepQuality.POOR)

_REASONS = {
    QualityStatus.USABLE: (),
    QualityStatus.PARTIAL: (QualityReason.TOO_SHORT,),
    QualityStatus.REJECTED: (QualityReason.NO_TARGET_SPEECH,),
}


def session(
    number: int,
    toward_decline: float = 0.0,
    markers: Sequence[MarkerId] = INDEX_MARKERS,
    *,
    status: QualityStatus = QualityStatus.USABLE,
    context: RecordingContext | None = None,
    person: str = "p-1",
) -> AnalysedSession:
    """Session ``number``: ``markers`` sit ``toward_decline`` units from 10, the others at 10."""
    session_id = f"s-{number}"
    values = {m: 10.0 + (SIGN[m] * toward_decline if m in markers else 0.0) for m in INDEX_MARKERS}
    # Pauses vary from session to session; lexical diversity never does.
    values[MarkerId.PAUSES_BETWEEN_PER100W] = 5.0 + 0.1 * number
    values[MarkerId.PAUSES_WITHIN_PER100W] = 3.0 + 0.1 * number
    values[MarkerId.MATTR_50] = 0.7

    return AnalysedSession(
        metadata=RecordingMetadata(
            person_id=person,
            task_type=TaskType.LIFE_STORY,
            language="eng",
            consent=True,
            recorded_at=START + timedelta(days=14 * number),
            source=RecordingSource.CLINICIAN_UI,
            context=context or RecordingContext(),
            synthetic=True,
        ),
        quality=QualityReport(
            session_id=session_id,
            person_id=person,
            synthetic=True,
            status=status,
            reasons=_REASONS[status],
            target_word_count=600 if status is QualityStatus.USABLE else 90,
            target_speaking_time_s=280.0 if status is QualityStatus.USABLE else 40.0,
            target_speech_share=0.9,
        ),
        metrics=None
        if status is QualityStatus.REJECTED
        else SessionMetrics(
            session_id=session_id,
            person_id=person,
            synthetic=True,
            markers=tuple(
                MarkerValue(marker=m, value=values[m], n_units=600) for m in MARKER_SPECS
            ),
        ),
    )


BASELINE = (session(1, -1.0), session(2, 0.0), session(3, 1.0))


def after_baseline(*later: AnalysedSession) -> tuple[LongitudinalComparisonResult, ...]:
    """Results of the sessions that follow the three baseline sessions."""
    return compare_trajectory([*BASELINE, *later])[len(BASELINE) :]


def levels(results: Sequence[LongitudinalComparisonResult]) -> list[tuple[str, str]]:
    return [(r.orientation.level.value, r.orientation.rule.value) for r in results]


# --- Marker test ------------------------------------------------------------


def test_crawford_howell_t_by_hand() -> None:
    # Baseline 10, 12, 14: mean 12, SD 2. t = (18 - 12) / (2 * sqrt(4 / 3)).
    assert crawford_howell_t(18.0, [10.0, 12.0, 14.0]) == pytest.approx(2.598076)
    assert crawford_howell_t(6.0, [10.0, 12.0, 14.0]) == pytest.approx(-2.598076)


def test_crawford_howell_t_needs_variance() -> None:
    assert crawford_howell_t(5.0, [3.0, 3.0, 3.0]) is None


def _student_t_cdf(x: float, df: int) -> float:
    """Student's t distribution function, by Simpson's rule on its density."""
    scale = gamma((df + 1) / 2) / (sqrt(df * pi) * gamma(df / 2))

    def density(u: float) -> float:
        return float(scale * (1 + u * u / df) ** (-(df + 1) / 2))

    steps = 2000
    h = x / steps
    inner = sum((4 if i % 2 else 2) * density(i * h) for i in range(1, steps))
    return 0.5 + (density(0.0) + inner + density(x)) * h / 3


@pytest.mark.parametrize("df", [2, 3, 4])
def test_critical_values_are_the_one_sided_5_percent_points(df: int) -> None:
    assert _student_t_cdf(T_CRITICAL_05[df], df) == pytest.approx(0.95, abs=1e-4)


# --- Baseline ---------------------------------------------------------------


def test_no_level_while_the_baseline_is_being_built() -> None:
    results = compare_trajectory(BASELINE)

    assert levels(results) == [("building_baseline", "insufficient_baseline")] * 3
    assert [r.uncertainty.baseline_session_count for r in results] == [0, 1, 2]
    assert all(r.baseline is None and r.change_index is None for r in results)
    assert results[0].orientation.suggested_action is SuggestedAction.CONTINUE_BASELINE


def test_baseline_grows_with_stable_sessions_then_freezes_at_five() -> None:
    results = after_baseline(session(4), session(5), session(6), session(7))

    baselines = [r.baseline for r in results]
    assert all(b is not None for b in baselines)
    assert [(len(b.session_ids), b.is_frozen) for b in baselines if b] == [
        (3, False),
        (4, False),
        (5, True),
        (5, True),
    ]
    assert levels(results) == [("stable", "not_significant")] * 4


def test_session_in_deviation_freezes_the_baseline() -> None:
    _, after = after_baseline(session(4, 4.0, TWO), session(5))

    assert after.baseline is not None
    assert after.baseline.session_ids == ("s-1", "s-2", "s-3")
    assert after.baseline.is_frozen


def test_partial_session_does_not_join_the_baseline() -> None:
    results = compare_trajectory(
        [
            session(1, -1.0),
            session(2, 0.0),
            session(3, status=QualityStatus.PARTIAL),
            session(4, 1.0),
            session(5),
        ]
    )

    assert [r.uncertainty.baseline_session_count for r in results] == [0, 1, 2, 2, 3]
    assert levels(results)[:4] == [("building_baseline", "insufficient_baseline")] * 4
    assert results[4].baseline is not None
    assert results[4].baseline.session_ids == ("s-1", "s-2", "s-4")


def test_baseline_statistics_and_index_range() -> None:
    (result,) = after_baseline(session(4))

    assert result.baseline is not None
    stats = {m.marker: (m.mean, m.sd, m.n) for m in result.baseline.markers}
    assert stats[MarkerId.PRONOUN_INDEX] == pytest.approx((10.0, 1.0, 3))
    # Oriented z-scores of the baseline sessions are -1, 0 and +1 on every index marker.
    assert result.baseline.change_index_values == pytest.approx((-1.0, 0.0, 1.0))
    assert result.uncertainty.baseline_change_index_range == pytest.approx((-1.0, 1.0))
    assert result.uncertainty.baseline_session_count == 3


# --- Marker deviations and change index -------------------------------------


def test_deviation_of_two_markers_by_hand() -> None:
    (result,) = after_baseline(session(4, 4.0, TWO))

    assert result.change_index is not None
    # Oriented z-scores: 4 on two markers, 0 on the four others.
    assert result.change_index.value == pytest.approx(8 / 6)
    assert result.change_index.tested_markers == INDEX_MARKERS
    assert result.change_index.significant_markers == TWO

    pronoun = next(d for d in result.markers if d.marker is MarkerId.PRONOUN_INDEX)
    assert (pronoun.value, pronoun.baseline_mean, pronoun.baseline_sd) == pytest.approx(
        (14.0, 10.0, 1.0)
    )
    assert pronoun.test is not None
    assert pronoun.test.t == pytest.approx(4 / sqrt(4 / 3))
    assert (pronoun.test.df, pronoun.test.significant) == (2, True)

    # Semantic: pronoun index at 4, three markers at 0. Fluency: maze index at 4, rate at 0.
    assert {f.family: f.value for f in result.family_scores} == pytest.approx(
        {MarkerFamily.SEMANTIC: 1.0, MarkerFamily.FLUENCY: 2.0}
    )


def test_three_units_is_below_the_threshold_with_three_baseline_sessions() -> None:
    (result,) = after_baseline(session(4, 3.0))

    assert result.change_index is not None
    assert result.change_index.value == pytest.approx(3.0)
    assert result.change_index.significant_markers == ()


def test_threshold_lowers_when_the_baseline_grows() -> None:
    # Session 4 is stable and joins: values 9, 10, 11, 10 -> mean 10, SD sqrt(2 / 3).
    # Session 5 at 3 units: t = 3 / (sqrt(2 / 3) * sqrt(5 / 4)) = 3.29 >= 2.35 (3 df).
    _, result = after_baseline(session(4), session(5, 3.0, TWO))

    pronoun = next(d for d in result.markers if d.marker is MarkerId.PRONOUN_INDEX)
    assert pronoun.test is not None
    assert pronoun.test.t == pytest.approx(3 / (sqrt(2 / 3) * sqrt(5 / 4)))
    assert (pronoun.test.df, pronoun.test.significant) == (3, True)


def test_change_away_from_decline_is_never_significant() -> None:
    (result,) = after_baseline(session(4, -4.0))

    assert result.change_index is not None
    assert result.change_index.value == pytest.approx(-4.0)
    assert result.change_index.significant_markers == ()
    assert all(d.test is None or d.test.t < 0 for d in result.markers if d.marker in SIGN)
    assert levels([result]) == [("stable", "not_significant")]


def test_markers_that_cannot_be_tested_have_no_test() -> None:
    (result,) = after_baseline(session(4))
    tests = {d.marker: d.test for d in result.markers}

    # No variance in the baseline.
    assert tests[MarkerId.MATTR_50] is None
    # Uncertain direction of decline: shown, never tested.
    assert tests[MarkerId.PAUSES_BETWEEN_PER100W] is None
    assert tests[MarkerId.PAUSES_WITHIN_PER100W] is None
    assert all(tests[m] is not None for m in INDEX_MARKERS)


# --- Orientation levels -----------------------------------------------------


def test_one_significant_marker_is_not_a_deviation() -> None:
    (result,) = after_baseline(session(4, 4.0, TWO[:1]))

    assert levels([result]) == [("stable", "not_significant")]


def test_isolated_deviation_asks_for_a_repeat_session() -> None:
    (result,) = after_baseline(session(4, 4.0, TWO))

    assert levels([result]) == [("monitor", "single_significant")]
    assert result.orientation.suggested_action is SuggestedAction.REPEAT_WITHIN_TWO_WEEKS


def test_two_consecutive_deviations_recommend_a_review() -> None:
    results = after_baseline(
        session(4, 4.0, TWO), session(5, 4.0, TWO), session(6), session(7, 4.0, TWO)
    )

    assert levels(results) == [
        ("monitor", "single_significant"),
        ("review_recommended", "persistent_two_sessions"),
        ("stable", "not_significant"),
        ("monitor", "single_significant"),  # the stable session reset the count
    ]
    assert results[1].orientation.suggested_action is SuggestedAction.PROFESSIONAL_REVIEW


def test_four_significant_markers_are_a_rapid_drop() -> None:
    (result,) = after_baseline(session(4, 4.0, FOUR))

    assert levels([result]) == [("review_recommended", "rapid_drop")]


def test_adverse_context_caps_the_level_but_counts_as_a_first_signal() -> None:
    capped, confirmed = after_baseline(
        session(4, 4.0, FOUR, context=POOR_NIGHT), session(5, 4.0, TWO)
    )

    assert levels([capped, confirmed]) == [
        ("monitor", "adverse_context_capped"),
        ("review_recommended", "persistent_two_sessions"),
    ]
    assert capped.uncertainty.adverse_context
    assert not confirmed.uncertainty.adverse_context


def test_adverse_context_cannot_confirm_a_review() -> None:
    results = after_baseline(session(4, 4.0, TWO), session(5, 4.0, TWO, context=POOR_NIGHT))

    assert levels(results) == [
        ("monitor", "single_significant"),
        ("monitor", "adverse_context_capped"),
    ]


def test_partial_session_keeps_the_level_and_the_count_of_deviations() -> None:
    results = after_baseline(
        session(4, 4.0, TWO),
        session(5, 4.0, FOUR, status=QualityStatus.PARTIAL),
        session(6, 4.0, TWO),
    )

    assert levels(results) == [
        ("monitor", "single_significant"),
        ("monitor", "carried_over"),
        ("review_recommended", "persistent_two_sessions"),
    ]
    # The partial session is still compared with the baseline, for display.
    assert results[1].change_index is not None
    assert set(results[1].change_index.significant_markers) == set(FOUR)
    assert results[1].uncertainty.quality_status is QualityStatus.PARTIAL


def test_partial_session_right_after_the_baseline_has_no_level() -> None:
    (result,) = after_baseline(session(4, status=QualityStatus.PARTIAL))

    assert levels([result]) == [("building_baseline", "carried_over")]


# --- Trajectory -------------------------------------------------------------


def test_rejected_sessions_have_no_result() -> None:
    results = compare_trajectory([*BASELINE, session(4, status=QualityStatus.REJECTED), session(5)])

    assert [r.session_id for r in results] == ["s-1", "s-2", "s-3", "s-5"]


def test_sessions_are_processed_in_time_order() -> None:
    sessions = [*BASELINE, session(4, 4.0, TWO), session(5, 4.0, TWO)]

    assert compare_trajectory(sessions[::-1]) == compare_trajectory(sessions)


def test_results_keep_identity_and_synthetic_flag() -> None:
    (result,) = after_baseline(session(4))

    assert (result.session_id, result.person_id, result.synthetic) == ("s-4", "p-1", True)
    assert result.task_type is TaskType.LIFE_STORY


def test_one_person_at_a_time() -> None:
    with pytest.raises(ValueError, match="single person"):
        compare_trajectory([session(1), session(2, person="p-2")])


def test_no_session_no_result() -> None:
    assert compare_trajectory([]) == ()
