"""What the API returns, built from the store (docs/specs/api.md and clinician-ui.md).

Step 3 is recomputed here from the stored sessions of the person: it is pure and
fast, and a stored comparison could go stale (docs/specs/api.md, section 7).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime

from app.agents.drift import compare_trajectory
from app.agents.markers import MARKER_SPECS
from app.agents.summary import ACTION_TEXT, RULE_TEXT
from app.api.models import (
    IN_PROGRESS,
    STEP_LABELS,
    OrientationView,
    Person,
    PersonDetail,
    PersonSummary,
    RetoldAnecdote,
    SessionDetail,
    SessionItem,
    SessionStatusView,
    Trajectory,
    TrajectoryPoint,
)
from app.api.transcript_view import annotate_transcript
from app.language import get_adapter
from app.prompts import load_prompt_bank
from app.schemas import (
    ClinicalSummaryReport,
    LongitudinalComparisonResult,
    OrientationLevel,
    QualityStatus,
)
from app.store import SessionRecord, Store, StoredAnalysis

LEVEL_ORDER = {
    OrientationLevel.REVIEW_RECOMMENDED: 0,
    OrientationLevel.MONITOR: 1,
    OrientationLevel.STABLE: 2,
    OrientationLevel.BUILDING_BASELINE: 3,
}
"""Order of the list of people: who needs attention first (clinician-ui.md, screen 1)."""


@dataclass(frozen=True)
class _PersonState:
    """Everything stored about one person, with step 3 recomputed."""

    sessions: list[SessionRecord]
    analyses: dict[str, StoredAnalysis]
    comparisons: dict[str, LongitudinalComparisonResult]

    @property
    def latest_comparison(self) -> LongitudinalComparisonResult | None:
        compared = [s for s in self.sessions if s.session_id in self.comparisons]
        return self.comparisons[compared[-1].session_id] if compared else None


def _state(store: Store, person_id: str) -> _PersonState:
    sessions = store.sessions_of(person_id)
    analyses = store.analyses_of([s.session_id for s in sessions])
    results = compare_trajectory([a.analysed for a in analyses.values()])
    return _PersonState(sessions, analyses, {r.session_id: r for r in results})


def age(birth_year: int | None, today: date | None = None) -> int | None:
    """Age reached this year: the birth date itself is not collected."""
    return None if birth_year is None else (today or date.today()).year - birth_year


def person_summaries(store: Store) -> list[PersonSummary]:
    rows = [
        _person_summary(person, _state(store, person.person_id)) for person in store.list_people()
    ]
    return sorted(rows, key=lambda row: (LEVEL_ORDER[row.orientation_level], row.display_name))


def _person_summary(person: Person, state: _PersonState) -> PersonSummary:
    latest = state.latest_comparison
    return PersonSummary(
        person_id=person.person_id,
        display_name=person.display_name,
        birth_year=person.birth_year,
        age=age(person.birth_year),
        language=person.language,
        synthetic=person.synthetic,
        last_session_at=state.sessions[-1].metadata.recorded_at if state.sessions else None,
        session_count=len(state.sessions),
        usable_session_count=sum(
            a.analysed.quality.status is QualityStatus.USABLE for a in state.analyses.values()
        ),
        in_progress_count=sum(s.status in IN_PROGRESS for s in state.sessions),
        orientation_level=(
            OrientationLevel.BUILDING_BASELINE if latest is None else latest.orientation.level
        ),
        baseline_session_count=0 if latest is None else latest.uncertainty.baseline_session_count,
    )


def person_detail(store: Store, person: Person) -> PersonDetail:
    state = _state(store, person.person_id)
    summaries = store.summaries_of([s.session_id for s in state.sessions])
    latest_summary = next(
        (summaries[s.session_id] for s in reversed(state.sessions) if s.session_id in summaries),
        None,
    )
    return PersonDetail(
        person=person,
        age=age(person.birth_year),
        risk_profile=store.risk_profile(person.person_id),
        first_session_at=state.sessions[0].metadata.recorded_at if state.sessions else None,
        last_session_at=state.sessions[-1].metadata.recorded_at if state.sessions else None,
        orientation=_orientation(state),
        trajectory=_trajectory(person.person_id, state),
        latest_summary=latest_summary,
        sessions=tuple(_session_item(s, state.analyses.get(s.session_id)) for s in state.sessions),
        retold_anecdotes=_retold_anecdotes(state),
    )


def trajectory(store: Store, person_id: str) -> Trajectory:
    return _trajectory(person_id, _state(store, person_id))


def _trajectory(person_id: str, state: _PersonState) -> Trajectory:
    points = [
        TrajectoryPoint(
            session_id=s.session_id,
            recorded_at=s.metadata.recorded_at,
            quality_status=state.analyses[s.session_id].analysed.quality.status,
            metrics=state.analyses[s.session_id].analysed.metrics,
            comparison=state.comparisons.get(s.session_id),
        )
        for s in state.sessions
        if s.session_id in state.analyses
    ]
    return Trajectory(
        person_id=person_id, marker_specs=tuple(MARKER_SPECS.values()), points=tuple(points)
    )


def _orientation(state: _PersonState) -> OrientationView | None:
    compared = [s for s in state.sessions if s.session_id in state.comparisons]
    if not compared:
        return None
    session = compared[-1]
    comparison = state.comparisons[session.session_id]
    decision = comparison.orientation
    return OrientationView(
        session_id=session.session_id,
        recorded_at=session.metadata.recorded_at,
        level=decision.level,
        rule=decision.rule,
        rule_text=RULE_TEXT[decision.rule],
        suggested_action=decision.suggested_action,
        action_text=ACTION_TEXT[decision.suggested_action],
        uncertainty=comparison.uncertainty,
        adverse_context=session.metadata.context.adverse_items,
    )


def _retold_anecdotes(state: _PersonState) -> tuple[RetoldAnecdote, ...]:
    recorded = {s.session_id: s.metadata.recorded_at for s in state.sessions}
    episodes = {
        (session_id, e.episode_id): e.summary
        for session_id, stored in state.analyses.items()
        if stored.narrative is not None
        for e in stored.narrative.episodes
    }
    found: list[RetoldAnecdote] = []
    for session in state.sessions:
        stored = state.analyses.get(session.session_id)
        if stored is None or stored.narrative is None:
            continue
        for repetition in stored.narrative.repetitions:
            origin = repetition.previous_session_id or session.session_id
            found.append(
                RetoldAnecdote(
                    session_id=session.session_id,
                    recorded_at=session.metadata.recorded_at,
                    episode_summary=episodes[(session.session_id, repetition.episode_id)],
                    scope=repetition.scope,
                    previous_session_id=repetition.previous_session_id,
                    previous_recorded_at=recorded.get(origin),
                    previous_episode_summary=episodes.get((origin, repetition.previous_episode_id)),
                    self_flagged=repetition.self_flagged,
                    acknowledgement_quote=repetition.acknowledgement_quote,
                    rationale=repetition.rationale,
                    quoted_passages=repetition.quoted_passages,
                )
            )
    return tuple(found)


def _session_item(record: SessionRecord, stored: StoredAnalysis | None) -> SessionItem:
    prompt = load_prompt_bank().get(record.metadata.prompt_id)
    quality = None if stored is None else stored.analysed.quality
    return SessionItem(
        session_id=record.session_id,
        person_id=record.person_id,
        recorded_at=record.metadata.recorded_at,
        source=record.metadata.source,
        prompt_id=record.metadata.prompt_id,
        theme=None if prompt is None else prompt.theme,
        status=record.status,
        quality_status=None if quality is None else quality.status,
        speaking_time_s=None if quality is None else round(quality.target_speaking_time_s, 1),
        synthetic=record.metadata.synthetic,
    )


def session_status(record: SessionRecord) -> SessionStatusView:
    return SessionStatusView(
        session_id=record.session_id,
        status=record.status,
        step=STEP_LABELS[record.status],
        error=record.error,
    )


def session_detail(store: Store, record: SessionRecord) -> SessionDetail:
    state = _state(store, record.person_id)
    stored = state.analyses.get(record.session_id)
    transcript = store.transcript(record.session_id)
    summary: ClinicalSummaryReport | None = store.summaries_of([record.session_id]).get(
        record.session_id
    )
    return SessionDetail(
        session=_session_item(record, stored),
        metadata=record.metadata,
        prompt=load_prompt_bank().get(record.metadata.prompt_id),
        error=record.error,
        quality=None if stored is None else stored.analysed.quality,
        metrics=None if stored is None else stored.analysed.metrics,
        comparison=state.comparisons.get(record.session_id),
        narrative=None if stored is None else stored.narrative,
        summary=summary,
        transcript=(
            None
            if transcript is None
            # The person's language: a rejected session may have been heard in another one.
            else annotate_transcript(transcript, get_adapter(record.metadata.language))
        ),
    )


def last_asked(sessions: Sequence[SessionRecord]) -> dict[str, datetime]:
    """When each theme was last asked to the person."""
    asked: dict[str, datetime] = {}
    for session in sessions:
        prompt_id = session.metadata.prompt_id
        if prompt_id is not None:
            when = session.metadata.recorded_at
            asked[prompt_id] = max(asked.get(prompt_id, when), when)
    return asked
