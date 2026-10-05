"""Run the Gurobi default-settings benchmark.

For every model already covered by the main cuOpt-vs-Gurobi comparison,
solves fresh with Gurobi's own untouched factory default (Method=-1,
automatic algorithm selection) -- reusing, never re-solving, the model's
already-recorded cuOpt result and deliberately-configured-Gurobi (method=2,
barrier) result. Answers: what runtime would any user who never touches
Gurobi's tuning parameters actually see, for every model in the suite?

See specs/010-gurobi-default-benchmark/.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sp

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from benchmarks import aggregate_gurobi_default as AG
from benchmarks import models as M
from benchmarks import residual as R
from benchmarks import solve as SV

RESULTS_MAIN = HERE / "results"
RESULTS = HERE / "results" / "gurobi_default"
RESULTS.mkdir(parents=True, exist_ok=True)


def _load_existing_result(model):
    """Read benchmarks/results/<model>.json (the existing main-suite result) and
    return the reused cuopt/gurobi_barrier stats plus the provenance/tolerance
    fields needed to solve and gate the new default-settings result. Errors
    clearly if the main result is missing; this feature has nothing to compare
    against without it, and never solves it on the model's behalf."""
    path = RESULTS_MAIN / (model + ".json")
    if not path.exists():
        raise FileNotFoundError(
            "%s not found -- run benchmarks/run_benchmark.py for %r first "
            "(this feature reuses the main suite's results, it does not produce them)"
            % (path, model))
    d = json.loads(path.read_text())
    prov = d["provenance"]
    return {
        "scale": prov["scale"],
        "n_cols": prov["n_cols"],
        "time_limit": d["time_limit"],
        "res_tol": d["res_tol"],
        "obj_tol": d["obj_tol"],
        "cuopt_solve_s": d["cuopt"]["solve_s_median"],
        "cuopt_status": d["cuopt"]["repeats"][0]["status"],
        "cuopt_residual_inf": d["cuopt"]["repeats"][0]["residual_inf"],
        "cuopt_objective": d["cuopt"]["objective"],
        "gurobi_barrier_solve_s": d["gurobi"]["solve_s_median"],
        "gurobi_barrier_status": d["gurobi"]["repeats"][0]["status"],
        "gurobi_barrier_residual_inf": d["gurobi"]["repeats"][0]["residual_inf"],
        "gurobi_barrier_objective": d["gurobi"]["objective"],
    }


def _solve_default(model, existing):
    """Solve `model`'s existing main-suite LP fresh with Gurobi's own untouched
    factory default (method=-1, automatic algorithm selection) -- everything
    else identical to the deliberately-configured solve (same time_limit).
    Applies the same correctness gate used for every other recorded result."""
    lp, _ = M.build_lp(model)

    res = SV.solve_gurobi(lp, time_limit=existing["time_limit"], method=-1)

    S_eq = sp.csr_matrix(lp["S"])
    b_eq = np.asarray(lp["b"], dtype=np.float64)
    residual_inf = R.feasibility_residual(S_eq, b_eq, res["fluxes"])

    solved_by = "barrier" if (res["bar_iters"] or 0) > 0 else "simplex"
    feasible = res["status"] == "Optimal" and residual_inf <= existing["res_tol"]
    obj_agree_with_cuopt = R.objectives_agree(
        res["objective"], existing["cuopt_objective"], tol=existing["obj_tol"])

    return {
        "model": model,
        "n_cols": existing["n_cols"],
        "solve_s": res["solve_s"],
        "objective": res["objective"],
        "status": res["status"],
        "residual_inf": residual_inf,
        "bar_iters": res["bar_iters"],
        "simplex_iters": res["simplex_iters"],
        "solved_by": solved_by,
        "feasible": feasible,
        "obj_agree_with_cuopt": obj_agree_with_cuopt,
        "time_limit": existing["time_limit"],
    }


def run_model(model, force):
    out = RESULTS / (model + ".json")
    if out.exists() and not force:
        print("[skip] %s (exists; --force to rerun)" % model)
        return json.loads(out.read_text())

    existing = _load_existing_result(model)
    print("[%s] cuopt (reused): solve_s=%.3f" % (model, existing["cuopt_solve_s"]))
    print("[%s] gurobi_barrier (reused): solve_s=%.3f" % (model, existing["gurobi_barrier_solve_s"]))

    print("[%s] gurobi_default -- solving fresh (time_limit=%ss)..." % (model, existing["time_limit"]))
    result = _solve_default(model, existing)
    print("[%s] gurobi_default: solve_s=%.3f  status=%s  solved_by=%s  feasible=%s" % (
        model, result["solve_s"], result["status"], result["solved_by"], result["feasible"]))

    out.write_text(json.dumps(result, indent=2))
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=M.ALL_MODELS)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    from benchmarks._deps import require_or_exit
    require_or_exit("gurobipy")

    names = M.ALL_MODELS if args.all else ([args.model] if args.model else [])
    if not names:
        ap.error("give --model NAME or --all")

    for name in names:
        run_model(name, args.force)

    if args.all:
        AG.main()


if __name__ == "__main__":
    from benchmarks._deps import run_main
    run_main(main)
