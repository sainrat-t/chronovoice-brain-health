"""Step 3 of the pipeline: change of each session from the personal baseline.

Pure statistics, no LLM. Specified in docs/specs/pipeline.md (step 3):

* the personal baseline is the first 3 usable sessions; it grows to 5 while new
  sessions stay stable, then freezes;
* each marker of a session is tested against the baseline with the modified t-test
  for small samples of Crawford & Garthwaite (2002);
* a session is "in deviation" when at least MIN_SIGNIFICANT_MARKERS index markers are
  significant, and a "rapid drop" from RAPID_DROP_MARKERS;
* the orientation level follows from these counts, from the session context and
  from the previous session. No level is given before the baseline exists.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from math import sqrt
from statistics import fmean, stdev

from app.agents.markers import MARKER_SPECS
from app.schemas import (
    LEVEL_ACTIONS,
    MAX_BASELINE_SESSIONS,
    MIN_BASELINE_SESSIONS,
    AnalysedSession,
    BaselineReference,
    ChangeIndexScore,
    DeclineDirection,
    FamilyScore,
    LongitudinalComparisonResult,
    MarkerBaseline,
    MarkerDeviation,
    MarkerFamily,
    MarkerId,
    OrientationDecision,
    OrientationLevel,
    OrientationRule,
    QualityStatus,
    SessionMetrics,
    SignificanceTest,
    TaskType,
    Uncertainty,
)

T_CRITICAL_05: dict[int, float] = {2: 2.9200, 3: 2.3534, 4: 2.1318}
"""One-sided 0.05 critical values of Student's t, by degrees of freedom (standard
table; 0.05 is the conventional threshold). Baselines of 3, 4 and 5 sessions."""

_DECLINE_SIGN = {DeclineDirection.INCREASE: 1.0, DeclineDirection.DECREASE: -1.0}


def crawford_howell_t(value: float, baseline: Sequence[float]) -> float | None:
    """Modified t of one case against a small sample.

    t = (value - mean) / (sd * sqrt((n + 1) / n)), with n - 1 degrees of freedom:
    Crawford & Howell (1998), as extended by Crawford JR, Garthwaite PH (2002),
    Neuropsychologia 40(8):1196-1208, DOI 10.1016/s0028-3932(01)00224-x, PMID 11931923.
    Returns None when the baseline has no variance.
    """
    n = len(baseline)
    sd = stdev(baseline)
    if sd == 0:
        return None
    return (value - fmean(baseline)) / (sd * sqrt((n + 1) / n))


def compare_trajectory(
    sessions: Sequence[AnalysedSession],
) -> tuple[LongitudinalComparisonResult, ...]:
    """Compare every session of one person with their personal baseline.

    Sessions are processed in time order, one baseline per task type. Rejected
    sessions have no result. The whole trajectory is recomputed on each call, so the
    result only depends on the sessions given.
    """
    if len({session.metadata.person_id for session in sessions}) > 1:
        raise ValueError("compare_trajectory expects the sessions of a single person")

    states: dict[TaskType, _Trajectory] = {}
    results: list[LongitudinalComparisonResult] = []
    for session in sorted(sessions, key=lambda s: s.metadata.recorded_at):
        if session.metrics is None:
            continue
        state = states.setdefault(session.metadata.task_type, _Trajectory())
        results.append(_compare_session(session, session.metrics, state))
    return tuple(results)


@dataclass(slots=True)
class _Trajectory:
    """What must be remembered from one session to the next, for one task type."""

    baseline: list[SessionMetrics] = field(default_factory=list)
    frozen: bool = False
    level: OrientationLevel = OrientationLevel.BUILDING_BASELINE
    previous_in_deviation: bool = False


def _compare_session(
    session: AnalysedSession, metrics: SessionMetrics, state: _Trajectory
) -> LongitudinalComparisonResult:
    task_type = session.metadata.task_type
    usable = session.quality.status is QualityStatus.USABLE
    adverse = session.metadata.context.is_adverse

    def result(
        decision: OrientationDecision,
        reference: BaselineReference | None = None,
        deviations: tuple[MarkerDeviation, ...] = (),
        index: ChangeIndexScore | None = None,
        families: tuple[FamilyScore, ...] = (),
    ) -> LongitudinalComparisonResult:
        values = reference.change_index_values if reference else ()
        return LongitudinalComparisonResult(
            session_id=metrics.session_id,
            person_id=metrics.person_id,
            synthetic=metrics.synthetic,
            task_type=task_type,
            baseline=reference,
            markers=deviations,
            change_index=index,
            family_scores=families,
            orientation=decision,
            uncertainty=Uncertainty(
                baseline_session_count=len(reference.session_ids) if reference else baseline_size,
                baseline_change_index_range=(min(values), max(values)) if values else None,
                quality_status=session.quality.status,
                adverse_context=adverse,
            ),
        )

    # Clinical rule 5: no orientation level before the baseline exists.
    baseline_size = len(state.baseline)
    if baseline_size < MIN_BASELINE_SESSIONS:
        if usable:
            state.baseline.append(metrics)
        return result(
            _decision(OrientationLevel.BUILDING_BASELINE, OrientationRule.INSUFFICIENT_BASELINE)
        )

    reference = _baseline_reference(state.baseline, task_type, frozen=state.frozen)
    deviations, index, families = _deviations(metrics, state.baseline)

    # A partial session is shown, but it cannot change the level or join the baseline.
    if not usable:
        decision = _decision(state.level, OrientationRule.CARRIED_OVER)
        return result(decision, reference, deviations, index, families)

    if index is None:
        raise ValueError(f"session {metrics.session_id}: no marker can be compared")
    decision = _decide(
        index, adverse_context=adverse, previous_in_deviation=state.previous_in_deviation
    )
    state.level = decision.level
    state.previous_in_deviation = index.is_in_deviation
    if not state.frozen:
        if decision.level is OrientationLevel.STABLE:
            state.baseline.append(metrics)
            state.frozen = len(state.baseline) == MAX_BASELINE_SESSIONS
        else:
            state.frozen = True
    return result(decision, reference, deviations, index, families)


def _decide(
    index: ChangeIndexScore, *, adverse_context: bool, previous_in_deviation: bool
) -> OrientationDecision:
    """Orientation level of a usable session (docs/specs/pipeline.md, step 3)."""
    if not index.is_in_deviation:
        return _decision(OrientationLevel.STABLE, OrientationRule.NOT_SIGNIFICANT)
    if adverse_context:
        # A session in an adverse context is a first signal, never a confirmation.
        return _decision(OrientationLevel.MONITOR, OrientationRule.ADVERSE_CONTEXT_CAPPED)
    if previous_in_deviation:
        return _decision(
            OrientationLevel.REVIEW_RECOMMENDED, OrientationRule.PERSISTENT_TWO_SESSIONS
        )
    if index.is_rapid_drop:
        return _decision(OrientationLevel.REVIEW_RECOMMENDED, OrientationRule.RAPID_DROP)
    return _decision(OrientationLevel.MONITOR, OrientationRule.SINGLE_SIGNIFICANT)


def _decision(level: OrientationLevel, rule: OrientationRule) -> OrientationDecision:
    return OrientationDecision(level=level, rule=rule, suggested_action=LEVEL_ACTIONS[level])


def _baseline_values(baseline: Sequence[SessionMetrics], marker: MarkerId) -> list[float]:
    values = (session.value_of(marker) for session in baseline)
    return [value for value in values if value is not None]


def _deviations(
    metrics: SessionMetrics, baseline: Sequence[SessionMetrics]
) -> tuple[tuple[MarkerDeviation, ...], ChangeIndexScore | None, tuple[FamilyScore, ...]]:
    """Test each marker of a session against the baseline and summarise the index markers."""
    df = len(baseline) - 1
    deviations: list[MarkerDeviation] = []
    z_scores: dict[MarkerId, float] = {}
    significant: list[MarkerId] = []

    for marker, spec in MARKER_SPECS.items():
        values = _baseline_values(baseline, marker)
        if len(values) < 2:
            continue
        mean, sd = fmean(values), stdev(values)
        value = metrics.value_of(marker)
        sign = _DECLINE_SIGN.get(spec.decline_direction)

        test = None
        complete = len(values) == len(baseline)
        raw_t = crawford_howell_t(value, values) if value is not None and complete else None
        if value is not None and sign is not None and raw_t is not None:
            t = sign * raw_t
            test = SignificanceTest(t=t, df=df, significant=t >= T_CRITICAL_05[df])
            if spec.in_change_index:
                z_scores[marker] = sign * (value - mean) / sd
                if test.significant:
                    significant.append(marker)
        deviations.append(
            MarkerDeviation(
                marker=marker, value=value, baseline_mean=mean, baseline_sd=sd, test=test
            )
        )

    if not z_scores:
        return tuple(deviations), None, ()

    index = ChangeIndexScore(
        value=fmean(z_scores.values()),
        tested_markers=tuple(z_scores),
        significant_markers=tuple(significant),
    )
    families = tuple(
        FamilyScore(family=family, value=fmean(scores))
        for family in MarkerFamily
        if (scores := [z for m, z in z_scores.items() if MARKER_SPECS[m].family is family])
    )
    return tuple(deviations), index, families


def _baseline_reference(
    baseline: Sequence[SessionMetrics], task_type: TaskType, *, frozen: bool
) -> BaselineReference:
    """Describe the baseline: mean and SD of each marker, and the index of its sessions."""
    markers: list[MarkerBaseline] = []
    index_z: list[list[float]] = [[] for _ in baseline]

    for marker, spec in MARKER_SPECS.items():
        values = _baseline_values(baseline, marker)
        if len(values) < 2:
            continue
        mean, sd = fmean(values), stdev(values)
        markers.append(MarkerBaseline(marker=marker, mean=mean, sd=sd, n=len(values)))

        sign = _DECLINE_SIGN.get(spec.decline_direction)
        if spec.in_change_index and sign is not None and sd > 0 and len(values) == len(baseline):
            for session_z, value in zip(index_z, values, strict=True):
                session_z.append(sign * (value - mean) / sd)

    return BaselineReference(
        task_type=task_type,
        session_ids=tuple(session.session_id for session in baseline),
        is_frozen=frozen,
        markers=tuple(markers),
        change_index_values=tuple(fmean(z) if z else 0.0 for z in index_z),
    )
