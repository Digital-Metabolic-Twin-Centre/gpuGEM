"""Aggregate benchmark.csv + results/version_lifting/*.json +
specs/013-cobra-model-lifting/'s model_lifting/*.json into the single derived
comparison CSV (data-model.md ExtendedComparisonRow).

Standalone: reads only committed results, no solver import required (mirrors
every other aggregate_*.py script in this project's "regenerable from
committed results alone" convention). Never modifies benchmark.csv itself.

See specs/014-version-lifting-runtime-comparison/.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from benchmarks import residual as R
from benchmarks._version_lifting_worker import IN_SCOPE_MODELS

BENCHMARK_CSV = HERE / "results" / "benchmark.csv"
VERSION_LIFTING_DIR = HERE / "results" / "version_lifting"
MODEL_LIFTING_DIR = HERE / "results" / "model_lifting"
OUT_CSV = HERE / "results" / "version_lifting_comparison.csv"

RES_TOL = 1e-4
OBJ_TOL = 1e-6

CSV_COLUMNS = [
    "model", "n_cols",
    "gurobi_solve_s_median",
    "cuopt_old_unlifted_solve_s_median", "cuopt_old_unlifted_verified_correct",
    "cuopt_new_unlifted_solve_s_median", "cuopt_new_unlifted_verified_correct",
    "cuopt_old_lifted_solve_s_median", "cuopt_old_lifted_verified_correct",
    "cuopt_new_lifted_solve_s_median", "cuopt_new_lifted_verified_correct",
]


def _gate(status, objective, residual_inf, gurobi_objective):
    if status != "Optimal" or objective is None or residual_inf is None:
        return False
    if not R.objectives_agree(objective, gurobi_objective, tol=OBJ_TOL):
        return False
    return residual_inf <= RES_TOL


def _row_for_model(base_row, gurobi_objective):
    model = base_row["model"]
    row = {
        "model": model,
        "n_cols": base_row["n_cols"],
        "gurobi_solve_s_median": base_row["gurobi_solve_s_median"],
        "cuopt_old_unlifted_solve_s_median": base_row["cuopt_solve_s_median"],
        "cuopt_old_unlifted_verified_correct": bool(base_row["both_feasible"]),
        "cuopt_new_unlifted_solve_s_median": None,
        "cuopt_new_unlifted_verified_correct": None,
        "cuopt_old_lifted_solve_s_median": None,
        "cuopt_old_lifted_verified_correct": None,
        "cuopt_new_lifted_solve_s_median": None,
        "cuopt_new_lifted_verified_correct": None,
    }
    if model not in IN_SCOPE_MODELS:
        return row

    # old-version-lifted: prefer specs/013's already-published, already-gated
    # result (its own verified_correct is reused verbatim, including a known
    # failure -- research.md R3, never recomputed/reinterpreted here).
    ml_path = MODEL_LIFTING_DIR / (model + ".json")
    if ml_path.exists():
        c = json.loads(ml_path.read_text())["comparison"]
        row["cuopt_old_lifted_solve_s_median"] = c["lifted_solve_s"]
        row["cuopt_old_lifted_verified_correct"] = bool(c["verified_correct"])

    vl_path = VERSION_LIFTING_DIR / (model + ".json")
    if vl_path.exists():
        combos = json.loads(vl_path.read_text())
        for key, (col_solve, col_ok) in {
            "new_unlifted": ("cuopt_new_unlifted_solve_s_median",
                              "cuopt_new_unlifted_verified_correct"),
            "old_lifted": ("cuopt_old_lifted_solve_s_median",
                            "cuopt_old_lifted_verified_correct"),
            "new_lifted": ("cuopt_new_lifted_solve_s_median",
                            "cuopt_new_lifted_verified_correct"),
        }.items():
            if key not in combos:
                continue
            if key == "old_lifted" and row["cuopt_old_lifted_verified_correct"] is not None:
                continue  # already filled from specs/013's own published result
            c = combos[key]
            row[col_solve] = c.get("solve_s")
            row[col_ok] = _gate(c.get("status"), c.get("objective"),
                                 c.get("residual_inf"), gurobi_objective)

    return row


def load_rows():
    if not BENCHMARK_CSV.exists():
        return []
    df = pd.read_csv(BENCHMARK_CSV)
    rows = []
    for _, base_row in df.iterrows():
        gurobi_objective = base_row["gurobi_obj"]
        rows.append(_row_for_model(base_row, gurobi_objective))
    return rows


def write_csv(rows):
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for row in rows:
            w.writerow(row)


def main():
    rows = load_rows()
    write_csv(rows)
    n_in_scope = sum(1 for r in rows if r["model"] in IN_SCOPE_MODELS)
    print("wrote %s (%d rows, %d in-scope)" % (OUT_CSV, len(rows), n_in_scope))


if __name__ == "__main__":
    main()
