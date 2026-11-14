"""Generate the texts of steps 2 and 4 for the personas, once, with the configured model.

They are saved in data/synthetic/llm_snapshot/<person>.json and loaded with the
personas, so that the server starts fast and always shows the same texts, which can
be reread before the demo (docs/specs/api.md, section 7). The sessions sent to the
model are fictional. About 50 calls for the three personas.

Run from backend/, with the model key in .env:

    uv run --env-file .env python -m scripts.build_demo_snapshot              # all personas
    uv run --env-file .env python -m scripts.build_demo_snapshot grace-santos
"""

from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

from app.agents.drift import compare_trajectory
from app.agents.narrative import analyse_narrative
from app.agents.summary import write_summary
from app.demo import SNAPSHOT_ROOT, LLMSnapshot, snapshot_path
from app.demo_data import analyse_sessions, load_personas, load_sessions
from app.language import get_adapter
from app.llm import LLMClient, create_llm_client
from app.processing import NARRATIVE_QUALITIES
from app.schemas import ClinicalSummaryReport, GenerationMode, NarrativeAnalysis, TaskType


def build(person_id: str, language: str, llm: LLMClient) -> LLMSnapshot:
    adapter = get_adapter(language)
    sessions = load_sessions(person_id)
    pairs = analyse_sessions(sessions)
    comparisons = {r.session_id: r for r in compare_trajectory([a for _, a in pairs])}
    narratives: list[NarrativeAnalysis] = []
    summaries: list[ClinicalSummaryReport] = []
    for session, (transcript, analysed) in zip(sessions, pairs, strict=True):
        narrative = None
        if (
            session.metadata.task_type is TaskType.LIFE_STORY
            and analysed.quality.status in NARRATIVE_QUALITIES
        ):
            narrative = analyse_narrative(transcript, narratives, llm, adapter)
            if narrative is not None:
                narratives.append(narrative)
        comparison = comparisons.get(session.session_id)
        if comparison is not None:
            summaries.append(
                write_summary(
                    transcript=transcript,
                    analysed=analysed,
                    comparison=comparison,
                    llm=llm,
                    adapter=adapter,
                )
            )
    return LLMSnapshot(
        synthetic=True,
        person_id=person_id,
        generated_at=datetime.now(UTC),
        narratives=tuple(narratives),
        summaries=tuple(summaries),
    )


def main() -> None:
    llm = create_llm_client()
    if llm is None:
        sys.exit("No model key found: put MISTRAL_API_KEY or ANTHROPIC_API_KEY in backend/.env")
    wanted = set(sys.argv[1:])
    personas = [p for p in load_personas() if not wanted or p.person_id in wanted]
    SNAPSHOT_ROOT.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=len(personas) or 1) as pool:
        snapshots = pool.map(lambda p: build(p.person_id, p.language, llm), personas)
        for snapshot in snapshots:
            path = snapshot_path(snapshot.person_id)
            path.write_text(snapshot.model_dump_json(indent=1) + "\n")
            written = sum(s.generation_mode is GenerationMode.LLM for s in snapshot.summaries)
            print(
                f"{snapshot.person_id}: {len(snapshot.narratives)} narratives, "
                f"{written}/{len(snapshot.summaries)} summaries written by the model -> {path}"
            )


if __name__ == "__main__":
    main()
