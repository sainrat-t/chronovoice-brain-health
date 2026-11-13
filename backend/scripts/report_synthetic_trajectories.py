"""Print what the pipeline measures on the synthetic personas, session by session.

Used to tune backend/data/synthetic/generation_params.json until each persona follows
its designed trajectory (docs/specs/synthetic-data.md).

Run from backend/:
    uv run python -m scripts.report_synthetic_trajectories          # committed files
    uv run python -m scripts.report_synthetic_trajectories --fresh  # regenerate in memory
    uv run python -m scripts.report_synthetic_trajectories --fresh grace-santos  # one persona
"""

from __future__ import annotations

import sys

from app.agents.drift import compare_trajectory
from app.demo_data import SyntheticSession, analyse_sessions, load_personas, load_sessions
from app.schemas import MarkerId
from scripts.generate_synthetic_data import generate_all

COLUMNS = (
    ("wpm", MarkerId.SPEECH_RATE_WPM, "{:6.1f}"),
    ("maze", MarkerId.MAZE_INDEX, "{:5.2f}"),
    ("pron", MarkerId.PRONOUN_INDEX, "{:5.3f}"),
    ("noun", MarkerId.NOUN_RATIO, "{:5.3f}"),
    ("freq", MarkerId.MEAN_WORD_FREQUENCY, "{:5.2f}"),
    ("len", MarkerId.MEAN_WORD_LENGTH, "{:5.2f}"),
    ("mattr", MarkerId.MATTR_50, "{:5.3f}"),
)


def _fresh_sessions(only: set[str] | None) -> dict[str, list[SyntheticSession]]:
    by_persona: dict[str, list[SyntheticSession]] = {}
    for path, content in sorted(generate_all(only).items()):
        by_persona.setdefault(path.parent.name, []).append(
            SyntheticSession.model_validate_json(content)
        )
    return by_persona


def main() -> None:
    only = {arg for arg in sys.argv[1:] if not arg.startswith("--")} or None
    fresh = _fresh_sessions(only) if "--fresh" in sys.argv else None
    for persona in load_personas():
        if only and persona.person_id not in only:
            continue
        sessions = fresh[persona.person_id] if fresh else load_sessions(persona.person_id)
        analysed = [session for _, session in analyse_sessions(sessions)]
        results = {r.session_id: r for r in compare_trajectory(analysed)}

        print(f"\n== {persona.display_name} ==")
        header = " ".join(f"{name:>6}" for name, _, _ in COLUMNS)
        print(f" n quality  words {header}  index sig level")
        for number, session in enumerate(analysed, start=1):
            quality = session.quality
            cells = []
            for _, marker, fmt in COLUMNS:
                value = session.metrics.value_of(marker) if session.metrics else None
                cells.append(f"{fmt.format(value) if value is not None else '-':>6}")
            result = results.get(session.session_id)
            index = result.change_index if result else None
            significant = ",".join(m.value[:4] for m in index.significant_markers) if index else ""
            level = (
                f"{result.orientation.level.value} ({result.orientation.rule.value})"
                if result
                else "-"
            )
            print(
                f"{number:2d} {quality.status.value:8s} {quality.target_word_count:5d} "
                f"{' '.join(cells)} {index.value if index else float('nan'):6.2f} "
                f"{len(index.significant_markers) if index else 0:3d} {level} {significant}"
            )


if __name__ == "__main__":
    main()
