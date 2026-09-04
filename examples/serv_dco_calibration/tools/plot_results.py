#!/usr/bin/env python3
"""Plots from results/serv_dco.csv. Updates the README figures. Not required to run tests."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

EXAMPLE = Path(__file__).resolve().parents[1]
CSV_PATH = EXAMPLE / "results" / "serv_dco.csv"
FIGURES = EXAMPLE / "figures"
RESULTS = EXAMPLE / "results"


def _is_true(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes"}


def main() -> int:
    try:
        import matplotlib.pyplot as plt
        from matplotlib.patches import Patch
    except ImportError:
        print("matplotlib is not installed; skip plotting", file=sys.stderr)
        return 0

    if not CSV_PATH.exists():
        print(f"No {CSV_PATH}; run the tests first", file=sys.stderr)
        return 1

    rows = [row for row in csv.DictReader(CSV_PATH.open()) if row["case"] != "behavioral"]
    if not rows:
        print("CSV has no SPICE cases to plot", file=sys.stderr)
        return 1

    labels = [row["case"].replace("_", " ") for row in rows]
    initial = [int(row["initial_count"]) for row in rows]
    final = [int(row["final_count"]) for row in rows]
    trims = [int(row["final_trim"]) for row in rows]
    passed = [_is_true(row["fw_pass"]) for row in rows]
    target = int(rows[0]["target_count"])

    FIGURES.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    x = list(range(len(labels)))
    ax.bar([i - 0.2 for i in x], initial, width=0.4, color="#6baed6", label="first measurement")
    ax.bar([i + 0.2 for i in x], final, width=0.4, color="#217a3a", label="calibrated count")
    ax.axhline(target, color="#d35400", linestyle="--", linewidth=1.2, label=f"target = {target}")
    ax.set_xticks(x, labels)
    ax.set_ylabel("oscillator edges in the measure window")
    ax.set_title("Firmware calibration across analog conditions")
    ax.set_ylim(0, max(max(initial), max(final), target) * 1.15)
    ax.legend()
    fig.tight_layout()
    for dest in (FIGURES, RESULTS):
        fig.savefig(dest / "serv_dco_counts.png", dpi=120)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    colors = ["#217a3a" if ok else "#c0392b" for ok in passed]
    ax.bar(labels, trims, color=colors)
    ax.set_ylabel("final trim code")
    ax.set_title("Trim chosen by SERV firmware")
    ax.set_ylim(0, 16)
    ax.legend(
        handles=[
            Patch(facecolor="#217a3a", label="PASS"),
            Patch(facecolor="#c0392b", label="FAIL (range exhausted)"),
        ]
    )
    fig.tight_layout()
    for dest in (FIGURES, RESULTS):
        fig.savefig(dest / "serv_dco_trims.png", dpi=120)
    plt.close(fig)

    print(f"Wrote {FIGURES / 'serv_dco_counts.png'} and {FIGURES / 'serv_dco_trims.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
