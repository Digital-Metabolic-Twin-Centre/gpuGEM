"""Merge the per-solver block-resolved residuals into one like-for-like table.

Inputs
------
results/block_residuals/block_residuals.csv
    cuOpt (shipped_default, residual_0) and Gurobi barrier, measured on the
    GPU host in the published environment (cuOpt 26.06.00, Gurobi 13.0.2).
results/highs_baseline/highs_method_blocks.csv
    HiGHS, both algorithm selections, measured by run_highs_baseline.py.

Why a merge script rather than one runner: the three solvers cannot run in one
process on one machine (cuOpt needs the GPU host's CUDA 12 stack, HiGHS was
measured separately), so the blocks are measured where each solver lives and
joined on (model, solver) here.

Output
------
results/block_residuals/table_s2_blocks.csv
    One row per (model, solver): both blocks, plus the ratio that shows how
    much the published single-number comparison depended on the row set.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
BR = HERE / "results" / "block_residuals"

# The configuration reported for each solver in the manuscript table.
REPORTED = {
    ("cuopt", "shipped_default"): "gpuGEM (cuOpt PDLP)",
    ("gurobi", "gurobi"): "Gurobi 13.0.2 barrier",
}
HIGHS_REPORTED_METHOD = "choose"   # HiGHS's own default selection


def _f(x):
    if x in (None, "", "None"):
        return None
    return float(x)


def _i(x):
    if x in (None, "", "None"):
        return None
    return int(float(x))


def load_gpu(path):
    rows = []
    for r in csv.DictReader(path.open()):
        label = REPORTED.get((r.get("solver"), r["configuration"]))
        rows.append({
            "model": r["model"],
            "solver": label or f"{r.get('solver')} ({r['configuration']})",
            "reported_in_table": label is not None,
            "configuration": r["configuration"],
            "status": r["status"],
            "solve_s": _f(r["solve_s"]),
            "iterations": _i(r["iterations"]),
            "eq_max_abs": _f(r["eq_max_abs"]),
            "eq_rows_violated": _i(r["eq_rows_violated"]),
            "coupling_max_viol": _f(r["coupling_max_viol"]),
            "coupling_rows_violated": _i(r["coupling_rows_violated"]),
            "all_rows_max_viol": _f(r["all_rows_max_viol"]),
            "n_eq_rows": _i(r["n_eq_rows"]),
            "n_coupling_rows": _i(r["n_coupling_rows"]),
            "source": "block_residuals.csv",
        })
    return rows


def load_highs(path):
    rows = []
    for r in csv.DictReader(path.open()):
        reported = r["method"] == HIGHS_REPORTED_METHOD
        rows.append({
            "model": r["model"],
            # 1.15.1 locally; the published baseline used 1.14.0 and both give
            # identical iteration counts and bit-identical residuals on the
            # models checked, so the columns are comparable.
            "solver": f"HiGHS 1.15.1 ({r['method']})",
            "reported_in_table": reported,
            "configuration": f"method={r['method']}",
            "status": "Optimal",
            "solve_s": _f(r["solve_s"]),
            "iterations": (_i(r["simplex_it"]) or 0) + (_i(r["ipm_it"]) or 0),
            "eq_max_abs": _f(r["eq_max_abs"]),
            "eq_rows_violated": _i(r["eq_rows_violated"]),
            "coupling_max_viol": _f(r["coupling_max_viol"]),
            "coupling_rows_violated": _i(r["coupling_rows_violated"]),
            "all_rows_max_viol": _f(r["legacy_residual_allrows"]),
            "n_eq_rows": _i(r["n_eq_rows"]),
            "n_coupling_rows": _i(r["n_coupling_rows"]),
            "source": "highs_method_blocks.csv",
        })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gpu", default=str(BR / "block_residuals.csv"))
    ap.add_argument("--highs",
                    default=str(HERE / "results" / "highs_baseline" /
                                "highs_method_blocks.csv"))
    ap.add_argument("--out", default=str(BR / "table_s2_blocks.csv"))
    a = ap.parse_args()

    rows = load_gpu(Path(a.gpu)) + load_highs(Path(a.highs))

    # The whole point of the table: on models with a coupling block, which
    # block binds, and does the row set change the solver ordering?
    for r in rows:
        eq, cp = r["eq_max_abs"], r["coupling_max_viol"]
        r["binding_block"] = (
            None if eq is None else
            "mass-balance" if cp is None else
            "coupling" if cp > eq else "mass-balance")
        r["coupling_over_eq"] = (
            None if (eq in (None, 0) or cp is None) else round(cp / eq, 2))

    order = {m: i for i, m in enumerate(
        ["e_coli_core", "iML1515", "Harvey", "Harvetta",
         "S84", "S85", "S9", "S15", "S23", "S83"])}
    rows.sort(key=lambda r: (order.get(r["model"], 99), r["solver"]))

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out}  ({len(rows)} rows)")

    # Ordering check, printed because it is the claim the table has to support.
    print("\nSolver ordering by basis, models with a coupling block:")
    hdr = f"{'model':12s} {'basis':12s} " + "".join(f"{s:26s}" for s in
          ("tightest", "middle", "loosest"))
    print(hdr)
    by_model = {}
    for r in rows:
        if r["reported_in_table"] and r["n_coupling_rows"]:
            by_model.setdefault(r["model"], []).append(r)
    for m, rs in sorted(by_model.items(), key=lambda kv: order.get(kv[0], 99)):
        if len(rs) < 2:
            continue
        for basis, key in (("mass-balance", "eq_max_abs"),
                           ("all rows", "all_rows_max_viol")):
            s = sorted(rs, key=lambda r: r[key])
            cells = "".join(f"{r['solver'].split()[0]+' '+format(r[key],'.3e'):26s}"
                            for r in s)
            print(f"{m:12s} {basis:12s} {cells}")


if __name__ == "__main__":
    main()
