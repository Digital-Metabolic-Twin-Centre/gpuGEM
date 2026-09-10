"""Subprocess entry point for one in-scope model's Python-side pipeline: lift
with gpugem's reformulate.m port, solve with Gurobi, map back.

Never invoked directly by a user -- launched by
run_matlab_python_lifting_comparison.py (same subprocess-isolation precedent
as specs/004-, specs/012-, specs/013-, specs/014-).

Mirrors gpugem/solver.py's own lift=True code path (lines 142-171) exactly --
lift_mass_balance, then lift_coupling if a coupling block exists (padding S
for any extra auxiliary columns lift_coupling adds beyond lift_mass_balance's
own, same as solver.py), then extend lb/ub/c for the auxiliary variables --
but hands the lifted system to benchmarks.solve.solve_gurobi (Gurobi barrier,
method=2, spec 015 research.md R3) instead of cuOpt, since gpugem.solve()
itself only ever calls cuOpt. No new gpugem surface (spec 015 research.md R4).

See specs/015-matlab-python-lifting-comparison/.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import scipy.sparse as sp

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from benchmarks import models as M
from benchmarks import residual as R
from benchmarks import solve as SV

IN_SCOPE_MODELS = ["e_coli_core", "iML1515", "Harvey", "Harvetta", "S84", "S85"]

_INF = 1e30


def lift_and_solve(lp, lift_big, time_limit):
    """Lift `lp` (as returned by benchmarks.models.build_lp) and solve with
    Gurobi. Returns (result_dict_from_solve_gurobi, mapping, lift_solve_s)
    where lift_solve_s is the *total* lift+solve wall time (spec FR-001/002
    measure the whole pipeline, not solve_gurobi's own narrower solve_s)."""
    import gpugem

    t0 = time.perf_counter()

    S_orig = sp.csr_matrix(lp["S"])
    b_orig = np.asarray(lp["b"], dtype=np.float64)
    lb_orig = np.asarray(lp["lb"], dtype=np.float64)
    ub_orig = np.asarray(lp["ub"], dtype=np.float64)
    c_orig = np.asarray(lp["c"], dtype=np.float64)
    C_orig = lp.get("C")
    d_lb_orig = lp.get("d_lb")
    d_ub_orig = lp.get("d_ub")

    S_solve, b_solve, mapping = gpugem.lift_mass_balance(S_orig, b_orig, big=lift_big)
    n_mb_aux = mapping.n_aux_vars

    if C_orig is not None:
        C_solve, d_lb_solve, d_ub_solve, mapping = gpugem.lift_coupling(
            C_orig, d_lb_orig, d_ub_orig, lift_big, mapping)
        n_extra_aux = mapping.n_aux_vars - n_mb_aux
        if n_extra_aux > 0:
            S_solve = sp.hstack(
                [S_solve, sp.csr_matrix((S_solve.shape[0], n_extra_aux))], format="csr")
    else:
        C_solve, d_lb_solve, d_ub_solve = None, None, None

    n_aux_total = mapping.n_aux_vars
    lb_solve = np.concatenate([lb_orig, np.full(n_aux_total, -_INF)])
    ub_solve = np.concatenate([ub_orig, np.full(n_aux_total, _INF)])
    c_solve = np.concatenate([c_orig, np.zeros(n_aux_total)])

    lifted_lp = dict(S=S_solve, b=b_solve, lb=lb_solve, ub=ub_solve, c=c_solve,
                      maximize=lp["maximize"])
    if C_solve is not None:
        lifted_lp.update(C=C_solve, d_lb=d_lb_solve, d_ub=d_ub_solve)

    result = SV.solve_gurobi(lifted_lp, time_limit=time_limit, method=2)
    lift_solve_s = time.perf_counter() - t0

    return result, mapping, lift_solve_s, S_orig, b_orig


def flux_summary(fluxes_orig, S_orig, b_orig):
    if fluxes_orig is None:
        return None
    return {
        "l2_norm": float(np.linalg.norm(fluxes_orig)),
        "max_abs": float(np.max(np.abs(fluxes_orig))) if fluxes_orig.size else 0.0,
        "residual_inf": R.feasibility_residual(S_orig, b_orig, fluxes_orig),
    }


def run_model(model, lift_big=1000.0, time_limit=900.0):
    try:
        lp, _prov = M.build_lp(model)
        result, mapping, lift_solve_s, S_orig, b_orig = lift_and_solve(lp, lift_big, time_limit)
    except Exception as exc:  # noqa: BLE001 -- must still emit a PipelineRun (FR-009)
        return {
            "model": model, "pipeline": "python", "lift_big": lift_big,
            "solve_s": None, "status": None, "objective": None,
            "fluxes_available": False, "flux_summary": None,
            "n_aux_vars": None, "n_mass_balance_rows_lifted": None,
            "n_coupling_rows_lifted": None,
            "excluded": True, "excluded_reason": "%s: %s" % (type(exc).__name__, exc),
        }

    import gpugem
    fluxes_orig = None
    if result["fluxes"] is not None:
        fluxes_orig = gpugem.map_back(result["fluxes"], mapping)

    return {
        "model": model,
        "pipeline": "python",
        "lift_big": lift_big,
        "solve_s": lift_solve_s,
        "status": result["status"],
        "objective": result["objective"],
        "fluxes_available": fluxes_orig is not None,
        "flux_summary": flux_summary(fluxes_orig, S_orig, b_orig),
        "n_aux_vars": mapping.n_aux_vars,
        "n_mass_balance_rows_lifted": len(mapping.mass_balance_lifted_rows),
        "n_coupling_rows_lifted": len(mapping.coupling_lifted_rows),
        "excluded": False,
        "excluded_reason": None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=IN_SCOPE_MODELS)
    ap.add_argument("--lift-big", type=float, default=1000.0)
    ap.add_argument("--time-limit", type=float, default=900.0)
    args = ap.parse_args()

    out = run_model(args.model, lift_big=args.lift_big, time_limit=args.time_limit)
    print(json.dumps(out))


if __name__ == "__main__":
    main()
