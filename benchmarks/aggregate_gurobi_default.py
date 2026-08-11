"""Aggregate benchmarks/results/gurobi_default/*.json into comparison.csv.

Standalone: reads only the committed per-model JSON files (this feature's own
gurobi_default/<model>.json plus each model's existing main-suite
results/<model>.json for the reused cuOpt/Gurobi-barrier columns) -- no solver
import required (mirrors benchmarks/aggregate_residual_tradeoff.py's
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

RESULTS_MAIN = HERE / "results"
RESULTS = HERE / "results" / "gurobi_default"
COMPARISON_CSV = RESULTS / "comparison.csv"

CSV_COLUMNS = [
    "model", "scale", "n_cols",
    "cuopt_solve_s", "cuopt_status", "cuopt_residual_inf",
    "gurobi_barrier_solve_s", "gurobi_barrier_status", "gurobi_barrier_residual_inf",
    "gurobi_default_solve_s", "gurobi_default_status", "gurobi_default_residual_inf",
    "gurobi_default_solved_by", "gurobi_default_feasible", "gurobi_default_obj_agree_with_cuopt",
    "gurobi_default_speedup_vs_barrier", "both_feasible",
]


def _load_main_result(model):
    d = json.loads((RESULTS_MAIN / (model + ".json")).read_text())
    prov = d["provenance"]
    return {
        "scale": prov["scale"],
        "n_cols": prov["n_cols"],
        "cuopt_solve_s": d["cuopt"]["solve_s_median"],
        "cuopt_status": d["cuopt"]["repeats"][0]["status"],
        "cuopt_residual_inf": d["cuopt"]["repeats"][0]["residual_inf"],
        "gurobi_barrier_solve_s": d["gurobi"]["solve_s_median"],
        "gurobi_barrier_status": d["gurobi"]["repeats"][0]["status"],
        "gurobi_barrier_residual_inf": d["gurobi"]["repeats"][0]["residual_inf"],
    }


def load_rows():
    """Read whichever results/gurobi_default/<model>.json files exist, in
    benchmarks.models' registry order, joined against each model's existing
    main-suite result for the reused cuOpt/Gurobi-barrier columns."""
    rows = []
    for model in M.ALL_MODELS:
        gdef_path = RESULTS / (model + ".json")
        if not gdef_path.exists():
            continue
        gdef = json.loads(gdef_path.read_text())
        main = _load_main_result(model)
        rows.append({
            "model": model,
            "scale": main["scale"],
            "n_cols": main["n_cols"],
            "cuopt_solve_s": main["cuopt_solve_s"],
            "cuopt_status": main["cuopt_status"],
            "cuopt_residual_inf": main["cuopt_residual_inf"],
            "gurobi_barrier_solve_s": main["gurobi_barrier_solve_s"],
            "gurobi_barrier_status": main["gurobi_barrier_status"],
            "gurobi_barrier_residual_inf": main["gurobi_barrier_residual_inf"],
            "gurobi_default_solve_s": gdef["solve_s"],
            "gurobi_default_status": gdef["status"],
            "gurobi_default_residual_inf": gdef["residual_inf"],
            "gurobi_default_solved_by": gdef["solved_by"],
            "gurobi_default_feasible": gdef["feasible"],
            "gurobi_default_obj_agree_with_cuopt": gdef["obj_agree_with_cuopt"],
            "gurobi_default_speedup_vs_barrier": main["gurobi_barrier_solve_s"] / gdef["solve_s"],
            "both_feasible": bool(gdef["feasible"] and gdef["obj_agree_with_cuopt"]),
        })
    return rows


def write_comparison_csv(rows):
    RESULTS.mkdir(parents=True, exist_ok=True)
    with open(COMPARISON_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for row in rows:
            w.writerow(row)


def main():
    rows = load_rows()
    write_comparison_csv(rows)
    print("wrote %s (%d models)" % (COMPARISON_CSV, len(rows)))


if __name__ == "__main__":
    main()
