"""Run the constraint-residual speed/correctness trade-off benchmark.

For every model already covered by the 002 cross-scale benchmark, assembles a
three-way comparison: cuOpt under gpugem's shipped defaults (reused from 002's
committed results, not re-solved), cuOpt with per_constraint_residual=0 (solved
fresh here), and Gurobi (reused from 002). Answers: how much speed does
disabling gpugem's per-row constraint-residual check buy, and how much
constraint-violation correctness does it cost -- per model, not just S85.

per_constraint_residual=0 is NOT validated for correctness and is never
recommended or adopted as a default by this tool (see
specs/005-residual-tradeoff-benchmark/).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from benchmarks import aggregate_residual_tradeoff as AG
from benchmarks import models as M
from benchmarks import residual as R
from benchmarks import solve as SV
from benchmarks import violation_histogram as VH

RESULTS_002 = HERE / "results"
RESULTS = HERE / "results" / "residual_tradeoff"
RESULTS.mkdir(parents=True, exist_ok=True)


def _load_002_result(model):
    """Read benchmarks/results/<model>.json (the existing 002 result) and return
    (shipped_default, gurobi, scale, n_cols) -- the two reused ResidualModeResults
    plus the provenance fields needed for the comparison. Errors clearly if the
    002 result is missing; this feature has nothing to compare against without it."""
    path = RESULTS_002 / (model + ".json")
    if not path.exists():
        raise FileNotFoundError(
            "%s not found -- run benchmarks/run_benchmark.py for %r first "
            "(this feature reuses 002's results, it does not produce them)" % (path, model))
    d = json.loads(path.read_text())
    prov = d["provenance"]
    time_limit = d["time_limit"]

    shipped_default = {
        "configuration": "shipped_default",
        "source": "reused",
        "solve_s": d["cuopt"]["solve_s_median"],
        "iterations": d["cuopt"]["repeats"][0]["iters"],
        "status": d["cuopt"]["repeats"][0]["status"],
        "objective": d["cuopt"]["objective"],
        "residual_inf": d["cuopt"]["repeats"][0]["residual_inf"],
        "rows_violated": None,
        "time_limit": time_limit,
    }
    gurobi = {
        "configuration": "gurobi",
        "source": "reused",
        "solve_s": d["gurobi"]["solve_s_median"],
        "iterations": d["gurobi"]["repeats"][0]["iters"],
        "status": d["gurobi"]["repeats"][0]["status"],
        "objective": d["gurobi"]["objective"],
        "residual_inf": d["gurobi"]["repeats"][0]["residual_inf"],
        "rows_violated": None,
        "time_limit": time_limit,
    }
    return shipped_default, gurobi, prov["scale"], prov["n_cols"]


def build_model_comparison(model, scale, n_cols, shipped_default, residual_0, gurobi):
    """Pure function: assemble the ModelComparison dict (data-model.md) from the
    three ResidualModeResults, computing the derived speedup/violation-ratio
    fields. No I/O, no solving -- safe to unit test on synthetic input."""
    speedup = shipped_default["solve_s"] / residual_0["solve_s"]
    violation_ratio = residual_0["residual_inf"] / shipped_default["residual_inf"]
    return {
        "model": model,
        "scale": scale,
        "n_cols": n_cols,
        "shipped_default": shipped_default,
        "residual_0": residual_0,
        "gurobi": gurobi,
        "speedup_residual_0_vs_shipped": speedup,
        "violation_ratio_residual_0_vs_shipped": violation_ratio,
    }


def _solve_residual_0(model, time_limit):
    """Solve `model`'s existing 002 LP fresh with per_constraint_residual=0 (cuOpt's
    own default, overriding gpugem's shipped per-row check) -- everything else
    identical to the shipped-default settings. No subprocess isolation: this is
    cuOpt's own long-established default behavior, not an untested setting
    (research R2)."""
    import gpugem

    lp, _ = M.build_lp(model)
    args = SV._solver_args(lp)

    res = gpugem.solve(
        time_limit=time_limit,
        check_feasibility=True,
        per_constraint_residual=0,
        **args,
    )

    import scipy.sparse as sp
    import numpy as np
    S_eq = sp.csr_matrix(lp["S"])
    b_eq = np.asarray(lp["b"], dtype=np.float64)
    resid = R.feasibility_residual(S_eq, b_eq, res.fluxes)

    rows_violated = res.feasibility.get("stoich_rows_violated_1e6")

    eq_viol = VH.signed_row_violations(S_eq, b_eq, b_eq, res.fluxes)
    violation_histogram_equations = VH.histogram(eq_viol)

    violation_histogram_constraints = None
    if lp.get("C") is not None:
        C = sp.csr_matrix(lp["C"])
        d_lb = np.asarray(lp["d_lb"], dtype=np.float64)
        d_ub = np.asarray(lp["d_ub"], dtype=np.float64)
        con_viol = VH.signed_row_violations(C, d_lb, d_ub, res.fluxes)
        violation_histogram_constraints = VH.histogram(con_viol)

    return {
        "configuration": "residual_0",
        "source": "fresh",
        "solve_s": res.wall_time_s,
        "iterations": res.n_iterations,
        "status": res.status,
        "objective": res.objective,
        "residual_inf": resid,
        "rows_violated": rows_violated,
        "time_limit": time_limit,
        "violation_histogram_equations": violation_histogram_equations,
        "violation_histogram_constraints": violation_histogram_constraints,
    }


def run_model(model, force):
    out = RESULTS / (model + ".json")
    if out.exists() and not force:
        existing = json.loads(out.read_text())
        if "violation_histogram_equations" in existing.get("residual_0", {}):
            print("[skip] %s (exists; --force to rerun)" % model)
            return existing
        print("[backfill] %s (missing violation histogram data; re-solving)" % model)

    shipped_default, gurobi, scale, n_cols = _load_002_result(model)
    print("[%s] shipped_default (reused): solve_s=%.3f  residual_inf=%.3e" % (
        model, shipped_default["solve_s"], shipped_default["residual_inf"]))
    print("[%s] gurobi (reused): solve_s=%.3f  residual_inf=%.3e" % (
        model, gurobi["solve_s"], gurobi["residual_inf"]))

    print("[%s] residual_0 -- solving fresh (time_limit=%ss)..." % (model, shipped_default["time_limit"]))
    residual_0 = _solve_residual_0(model, shipped_default["time_limit"])
    print("[%s] residual_0: solve_s=%.3f  status=%s  residual_inf=%.3e  rows_violated=%s" % (
        model, residual_0["solve_s"], residual_0["status"], residual_0["residual_inf"],
        residual_0["rows_violated"]))

    comparison = build_model_comparison(model, scale, n_cols, shipped_default, residual_0, gurobi)
    out.write_text(json.dumps(comparison, indent=2))
    print("[%s] speedup=%.2fx  violation_ratio=%.2fx" % (
        model, comparison["speedup_residual_0_vs_shipped"],
        comparison["violation_ratio_residual_0_vs_shipped"]))
    return comparison


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=M.ALL_MODELS)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    names = M.ALL_MODELS if args.all else ([args.model] if args.model else [])
    if not names:
        ap.error("give --model NAME or --all")

    for name in names:
        run_model(name, args.force)

    if args.all:
        AG.main()


if __name__ == "__main__":
    main()
