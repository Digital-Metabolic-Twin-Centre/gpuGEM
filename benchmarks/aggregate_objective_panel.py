"""Aggregate benchmarks/results/objective_panel/<model>/*.json into the two
additive CSV views (spec FR-007).

Standalone: reads only the committed per-(model, objective) JSON files, no
solver import required (mirrors benchmarks/aggregate_gurobi_default.py's
"regenerable from committed results" property).
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from benchmarks import models as M
from benchmarks import objective_panel as OP

RESULTS = HERE / "results" / "objective_panel"
RUNTIME_CSV = RESULTS / "objective_runtime.csv"
DETAILS_CSV = RESULTS / "benchmark_details.csv"

RUNTIME_COLUMNS = ["model", "objective_id", "reaction_id", "solver",
                   "objective_value_median", "runtime_s_median"]
DETAILS_COLUMNS = ["model", "objective_id", "reaction_id", "category", "solver", "status",
                   "residual_inf_median", "iters_median", "feasible", "obj_agree_with_cuopt",
                   "both_feasible"]


def load_results():
    """Read whichever results/objective_panel/<model>/*.json files exist, in
    benchmarks.models registry order, then in that model's
    objective_candidates/<model>.csv panel order (contracts/csv-columns.md) --
    NOT alphabetical filename order, which would scramble the "first row is
    the already-published baseline" convention (e.g. ATPM.json sorts before
    BIOMASS_*.json alphabetically even though BIOMASS is the panel's actual
    first/baseline entry)."""
    results = []
    for model in M.ALL_MODELS:
        model_dir = RESULTS / model
        if not model_dir.exists():
            continue
        try:
            panel = OP._load_panel(model)
        except FileNotFoundError:
            continue
        for entry in panel:
            p = model_dir / (entry["reaction_id"] + ".json")
            if p.exists():
                results.append(json.loads(p.read_text()))
    return results


def runtime_rows(result):
    rows = []
    for solver in ("cuopt", "gurobi"):
        s = result[solver]
        rows.append({
            "model": result["model"],
            "objective_id": result["objective_id"],
            "reaction_id": result["reaction_id"],
            "solver": solver,
            "objective_value_median": s["objective_median"],
            "runtime_s_median": s["solve_s_median"],
        })
    return rows


def detail_rows(result):
    rows = []
    for solver in ("cuopt", "gurobi"):
        s = result[solver]
        rows.append({
            "model": result["model"],
            "objective_id": result["objective_id"],
            "reaction_id": result["reaction_id"],
            "category": result["category"],
            "solver": solver,
            "status": s["status"],
            "residual_inf_median": s["residual_inf_median"],
            "iters_median": s["iters_median"],
            "feasible": s["feasible"],
            "obj_agree_with_cuopt": result["obj_agree_with_cuopt"],
            "both_feasible": result["both_feasible"],
        })
    return rows


def write_csvs(results):
    RESULTS.mkdir(parents=True, exist_ok=True)
    with open(RUNTIME_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=RUNTIME_COLUMNS)
        w.writeheader()
        for result in results:
            for row in runtime_rows(result):
                w.writerow(row)

    with open(DETAILS_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=DETAILS_COLUMNS)
        w.writeheader()
        for result in results:
            for row in detail_rows(result):
                w.writerow(row)


def main():
    results = load_results()
    write_csvs(results)
    print("wrote %s and %s (%d objective results, %d rows each)" % (
        RUNTIME_CSV, DETAILS_CSV, len(results), len(results) * 2))


if __name__ == "__main__":
    main()
