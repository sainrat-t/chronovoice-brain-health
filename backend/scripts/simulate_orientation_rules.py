"""Monte Carlo check of the step 3 orientation rules (docs/specs/pipeline.md, step 3).

Simulates a person whose 6 index markers are normally distributed and equally
correlated (rho), with a personal baseline of 3 to 5 sessions followed by two more
sessions tested against it. Reports, per session:

* how often a stable person is flagged ("in deviation", "rapid drop", "review");
* how often a real shift of every marker toward decline is detected.

The first version of the spec tested the change index itself against its baseline
values; its false-alert rate is printed for the record.

Run from backend/:  uv run python -m scripts.simulate_orientation_rules
"""

from __future__ import annotations

import numpy as np

from app.agents.drift import T_CRITICAL_05
from app.agents.markers import MARKER_SPECS
from app.schemas import MIN_SIGNIFICANT_MARKERS, RAPID_DROP_MARKERS

SEED = 20261113
REPETITIONS = 400_000
MARKERS = sum(spec.in_change_index for spec in MARKER_SPECS.values())
BASELINE_SIZES = (3, 4, 5)
CORRELATIONS = (0.0, 0.3, 0.6)
SHIFTS_SD = (2.0, 3.0)


def simulate(rng: np.random.Generator, n: int, rho: float, shift_sd: float) -> dict[str, float]:
    """Rates over REPETITIONS persons, for a baseline of ``n`` sessions."""
    common = rng.standard_normal((REPETITIONS, n + 2, 1))
    own = rng.standard_normal((REPETITIONS, n + 2, MARKERS))
    values = np.sqrt(rho) * common + np.sqrt(1 - rho) * own
    baseline, later = values[:, :n, :], values[:, n:, :] + shift_sd

    mean = baseline.mean(axis=1, keepdims=True)
    sd = baseline.std(axis=1, ddof=1, keepdims=True)
    z = (later - mean) / sd
    significant = z / np.sqrt((n + 1) / n) >= T_CRITICAL_05[n - 1]
    count = significant.sum(axis=2)

    in_deviation = count >= MIN_SIGNIFICANT_MARKERS
    rapid_drop = count >= RAPID_DROP_MARKERS
    review = (in_deviation[:, 0] & in_deviation[:, 1]) | rapid_drop[:, 1]

    # First version of the spec: t-test of the mean z-score against its baseline values.
    baseline_index = ((baseline - mean) / sd).mean(axis=2)
    old_t = z[:, 1, :].mean(axis=1) / (baseline_index.std(axis=1, ddof=1) * np.sqrt((n + 1) / n))

    return {
        "in_deviation": float(in_deviation[:, 1].mean()),
        "rapid_drop": float(rapid_drop[:, 1].mean()),
        "review": float(review.mean()),
        "old_rule": float((old_t >= T_CRITICAL_05[n - 1]).mean()),
    }


def main() -> None:
    rng = np.random.default_rng(SEED)
    print(f"{REPETITIONS:,} simulated persons per line, {MARKERS} markers, seed {SEED}.\n")

    print("Stable person: share of sessions flagged (false alerts)\n")
    print("| Baseline | rho | In deviation | Rapid drop | Review recommended | First spec rule |")
    print("|---|---|---|---|---|---|")
    for n in BASELINE_SIZES:
        for rho in CORRELATIONS:
            r = simulate(rng, n, rho, 0.0)
            print(
                f"| {n} | {rho} | {r['in_deviation']:.1%} | {r['rapid_drop']:.2%} "
                f"| {r['review']:.2%} | {r['old_rule']:.1%} |"
            )

    print("\nReal change: every marker shifted toward decline, rho = 0.3\n")
    print("| Baseline | Shift (SD) | In deviation | Review recommended |")
    print("|---|---|---|---|")
    for n in BASELINE_SIZES:
        for shift in SHIFTS_SD:
            r = simulate(rng, n, 0.3, shift)
            print(f"| {n} | {shift:g} | {r['in_deviation']:.0%} | {r['review']:.0%} |")


if __name__ == "__main__":
    main()
