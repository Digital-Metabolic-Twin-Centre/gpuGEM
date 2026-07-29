"""Aggregate benchmarks/results/residual_tradeoff/*.json into comparison.csv.

Standalone: reads only the committed per-model JSON files, no solver import
required (mirrors benchmarks/aggregate_sweep.py's "regenerable from committed
results" property).
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from benchmarks import models as M

RESULTS = HERE / "results" / "residual_tradeoff"
COMPARISON_CSV = RESULTS / "comparison.csv"

CSV_COLUMNS = ["model", "scale", "n_cols", "configuration", "source",
               "solve_s", "iterations", "status", "objective", "residual_inf",
               "rows_violated", "time_limit",
               "speedup_residual_0_vs_shipped", "violation_ratio_residual_0_vs_shipped"]


def load_comparisons():
    """Read whichever results/residual_tradeoff/<model>.json files exist, in
    benchmarks.models' registry order (matches 002's scale/n_cols ordering)."""
    comparisons = []
    for model in M.ALL_MODELS:
        p = RESULTS / (model + ".json")
        if p.exists():
            comparisons.append(json.loads(p.read_text()))
    return comparisons


def rows_for_comparison(comparison):
    """One CSV row per configuration for this model (3 rows)."""
    speedup = comparison["speedup_residual_0_vs_shipped"]
    violation_ratio = comparison["violation_ratio_residual_0_vs_shipped"]
    rows = []
    for key in ("shipped_default", "residual_0", "gurobi"):
        r = comparison[key]
        rows.append({
            "model": comparison["model"],
            "scale": comparison["scale"],
            "n_cols": comparison["n_cols"],
            "configuration": r["configuration"],
            "source": r["source"],
            "solve_s": r["solve_s"],
            "iterations": r["iterations"] if r["iterations"] is not None else "",
            "status": r["status"],
            "objective": r["objective"],
            "residual_inf": r["residual_inf"],
            "rows_violated": r["rows_violated"] if r["rows_violated"] is not None else "",
            "time_limit": r["time_limit"],
            "speedup_residual_0_vs_shipped": speedup,
            "violation_ratio_residual_0_vs_shipped": violation_ratio,
        })
    return rows


def write_comparison_csv(comparisons):
    RESULTS.mkdir(parents=True, exist_ok=True)
    with open(COMPARISON_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for comparison in comparisons:
            for row in rows_for_comparison(comparison):
                w.writerow(row)


def main():
    comparisons = load_comparisons()
    write_comparison_csv(comparisons)
    print("wrote %s (%d models, %d rows)" % (
        COMPARISON_CSV, len(comparisons), len(comparisons) * 3))


if __name__ == "__main__":
    main()
