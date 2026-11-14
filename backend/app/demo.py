"""Loading the synthetic personas into the store (docs/specs/api.md, sections 4 and 7).

Their sessions go through steps 0, 1 and 3 at load time. The texts of steps 2 and 4
come from a snapshot generated once by scripts/build_demo_snapshot.py, so that the
server starts in seconds and shows the same, reviewable texts at every restart.
"""

from __future__ import annotations

import logging
from collections.abc import Collection
from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict

from app.agents.drift import compare_trajectory
from app.agents.summary import write_summary
from app.api.models import Person, SessionStatus
from app.demo_data import SYNTHETIC_ROOT, analyse_sessions, load_personas, load_sessions
from app.language import get_adapter
from app.schemas import ClinicalSummaryReport, NarrativeAnalysis, QualityStatus
from app.store import SessionRecord, Store

logger = logging.getLogger(__name__)

SNAPSHOT_ROOT = SYNTHETIC_ROOT / "llm_snapshot"


class LLMSnapshot(BaseModel):
    """The texts of steps 2 and 4 for one persona, generated once by a model."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    synthetic: Literal[True]
    person_id: str
    generated_at: AwareDatetime
    narratives: tuple[NarrativeAnalysis, ...]
    summaries: tuple[ClinicalSummaryReport, ...]


def snapshot_path(person_id: str, root: Path = SNAPSHOT_ROOT) -> Path:
    return root / f"{person_id}.json"


def load_snapshot(person_id: str, root: Path = SNAPSHOT_ROOT) -> LLMSnapshot | None:
    path = snapshot_path(person_id, root)
    if not path.exists():
        return None
    return LLMSnapshot.model_validate_json(path.read_text())


def seed_demo(
    store: Store,
    *,
    only: Collection[str] | None = None,
    synthetic_root: Path = SYNTHETIC_ROOT,
    snapshot_root: Path = SNAPSHOT_ROOT,
) -> None:
    """Load the personas (all of them, or those in ``only``) into an empty store."""
    for persona in load_personas(synthetic_root):
        if only is not None and persona.person_id not in only:
            continue
        sessions = load_sessions(persona.person_id, synthetic_root)
        pairs = analyse_sessions(sessions)
        comparisons = {r.session_id: r for r in compare_trajectory([a for _, a in pairs])}
        snapshot = load_snapshot(persona.person_id, snapshot_root)
        narratives = {n.session_id: n for n in snapshot.narratives} if snapshot else {}
        summaries = {s.session_id: s for s in snapshot.summaries} if snapshot else {}
        adapter = get_adapter(persona.language)

        store.add_person(
            Person(
                person_id=persona.person_id,
                display_name=persona.display_name,
                birth_year=persona.birth_year,
                language=persona.language,
                synthetic=True,
                summary=persona.summary,
                created_at=sessions[0].metadata.recorded_at,
            ),
            persona.risk_profile,
        )
        for session, (transcript, analysed) in zip(sessions, pairs, strict=True):
            rejected = analysed.quality.status is QualityStatus.REJECTED
            store.add_session(
                SessionRecord(
                    session_id=session.session_id,
                    metadata=session.metadata,
                    status=SessionStatus.REJECTED if rejected else SessionStatus.DONE,
                    created_at=session.metadata.recorded_at,
                )
            )
            store.save_results(session.session_id, transcript, analysed)
            narrative = narratives.get(session.session_id)
            if narrative is not None:
                store.save_narrative(session.session_id, narrative)

            comparison = comparisons.get(session.session_id)
            if comparison is None:
                continue
            report = summaries.get(session.session_id)
            if report is None or report.orientation_level is not comparison.orientation.level:
                if report is not None:
                    logger.warning(
                        "snapshot summary of %s is for level %s, now %s: fixed wording used",
                        session.session_id,
                        report.orientation_level.value,
                        comparison.orientation.level.value,
                    )
                report = write_summary(
                    transcript=transcript,
                    analysed=analysed,
                    comparison=comparison,
                    llm=None,
                    adapter=adapter,
                )
            store.save_summary(report)


def reset_demo(store: Store) -> None:
    """Back to the state of the demo: the personas only."""
    store.initialise()
    store.clear()
    seed_demo(store)
