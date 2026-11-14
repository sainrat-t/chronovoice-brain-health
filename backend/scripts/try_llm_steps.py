"""Real trial of the LLM steps (2 and 4) on a synthetic persona.

Calls the configured model for real: about 10 calls for step 2 and 3 to 6 for step 4,
a few cents with a small model. The sessions sent are fictional.

Run from backend/, with the key in .env (MISTRAL_API_KEY or ANTHROPIC_API_KEY):

    uv run --env-file .env python -m scripts.try_llm_steps                 # Margaret
    uv run --env-file .env python -m scripts.try_llm_steps rajesh-menon

MISTRAL_MODEL and MISTRAL_REASONING_EFFORT, set before the command, try another
Mistral model or reasoning effort without touching .env.

Step 2 is checked against what the personas were written to contain: Margaret retells
one anecdote in sessions 8, 9 and 10 without noticing, and Rajesh comes back to one in
session 7 saying he already told it (docs/specs/synthetic-data.md).
"""

from __future__ import annotations

import logging
import sys
import time
from typing import Any

from app.agents.drift import compare_trajectory
from app.agents.narrative import NarrativeDraft, analyse_narrative
from app.agents.summary import write_summary
from app.demo_data import analyse_sessions, load_sessions
from app.language import get_adapter
from app.llm import LLMClient, LLMError, LLMReply, create_llm_client
from app.schemas import NarrativeAnalysis, RepetitionScope

# Session number -> whether the person says they already told the anecdote.
EXPECTED_RETELLINGS: dict[str, dict[int, bool]] = {
    "margaret-hale": {8: False, 9: False, 10: False},
    "rajesh-menon": {7: True},
    "grace-santos": {},
}


class _Recorder:
    """Passes calls through to the real client and keeps what came back."""

    def __init__(self, client: LLMClient) -> None:
        self._client = client
        self.calls = 0
        self.errors = 0
        self.seconds = 0.0
        self.last_output: Any = None
        self.last_model = "?"

    def generate(self, *, system: str, user: str, output: type[Any]) -> LLMReply[Any]:
        self.calls += 1
        started = time.perf_counter()
        try:
            reply = self._client.generate(system=system, user=user, output=output)
        except LLMError:
            self.errors += 1
            raise
        finally:
            self.seconds += time.perf_counter() - started
        self.last_output, self.last_model = reply.output, reply.model_id
        return reply


def main() -> None:
    person_id = sys.argv[1] if len(sys.argv) > 1 else "margaret-hale"
    client = create_llm_client()
    if client is None:
        sys.exit("No model key found: put MISTRAL_API_KEY or ANTHROPIC_API_KEY in backend/.env")
    # On the standard output, so that rejections appear next to the session they concern.
    logging.basicConfig(
        level=logging.INFO, format="      [%(name)s] %(message)s", stream=sys.stdout
    )
    logging.getLogger("httpx2").setLevel(logging.WARNING)

    llm = _Recorder(client)
    adapter = get_adapter("eng")
    pairs = analyse_sessions(load_sessions(person_id))
    comparisons = {r.session_id: r for r in compare_trajectory([a for _, a in pairs])}

    print(f"== Step 2, narrative analyst: {person_id} ==")
    expected = EXPECTED_RETELLINGS.get(person_id, {})
    previous: list[NarrativeAnalysis] = []
    narratives: dict[str, NarrativeAnalysis] = {}
    # Session number -> for each anecdote retold from an earlier session, was it acknowledged.
    found: dict[int, list[bool]] = {}
    kept = 0
    for number, (transcript, _) in enumerate(pairs, start=1):
        before = llm.seconds
        analysis = analyse_narrative(transcript, previous, llm, adapter)
        if analysis is None:
            print(f"{number:2d}  skipped (model unavailable or nothing to analyse)")
            continue
        draft: NarrativeDraft = llm.last_output
        print(
            f"{number:2d}  {llm.seconds - before:5.1f}s  {llm.last_model}  "
            f"episodes {len(analysis.episodes)}/{len(draft.episodes)} kept  "
            f"repetitions {len(analysis.repetitions)}/{len(draft.repetitions)} kept"
        )
        kept += len(analysis.repetitions)
        for repetition in analysis.repetitions:
            if repetition.scope is RepetitionScope.ACROSS_SESSIONS:
                found.setdefault(number, []).append(repetition.self_flagged)
            origin = repetition.previous_session_id or "same session"
            aware = (
                f"acknowledged: {repetition.acknowledgement_quote!r}"
                if repetition.self_flagged
                else "not acknowledged"
            )
            print(
                f"      retold from {origin}/{repetition.previous_episode_id} ({aware}): "
                f"{repetition.quoted_passages[0]!r}"
            )
            print(f"         why: {repetition.rationale}")
        previous.append(analysis)
        narratives[analysis.session_id] = analysis

    hits = sum(1 for number, flagged in expected.items() if flagged in found.get(number, []))
    print(
        f"Expected retellings found: {hits}/{len(expected)}; other repetitions kept: {kept - hits}"
    )

    print(f"\n== Step 4, clinical summary: {person_id} ==")
    # The first session of each orientation level, and the last session.
    chosen: dict[str, int] = {}
    for number, (_, analysed) in enumerate(pairs, start=1):
        comparison = comparisons.get(analysed.session_id)
        if comparison is not None:
            chosen.setdefault(comparison.orientation.level.value, number)
    for number in sorted({*chosen.values(), len(pairs)}):
        transcript, analysed = pairs[number - 1]
        comparison = comparisons[analysed.session_id]
        calls = llm.calls
        report = write_summary(
            transcript=transcript,
            analysed=analysed,
            comparison=comparison,
            llm=llm,
            adapter=adapter,
        )
        summary = report.clinician_summary
        print(
            f"\n--- session {number}: {comparison.orientation.level.value} | "
            f"{report.generation_mode.value} | model calls: {llm.calls - calls} ---"
        )
        print(f"HEADLINE    {summary.headline}")
        for finding in summary.findings:
            markers = ", ".join(m.value for m in finding.marker_ids)
            studies = ", ".join(s.value for s in finding.study_refs) or "no study cited"
            print(f"FINDING     {finding.text}  [{markers}] [{studies}]")
            for passage in finding.passages:
                print(f"   QUOTE    {passage!r}")
        print(f"UNCERTAINTY {summary.uncertainty_statement}")
        print(f"PERSON      {report.person_explanation}")

    print(f"\n{llm.calls} model calls, {llm.errors} failed, {llm.seconds:.0f} s in total.")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
