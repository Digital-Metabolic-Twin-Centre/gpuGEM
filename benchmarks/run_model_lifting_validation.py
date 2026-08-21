"""Validate gpugem's opt-in model-lifting feature (gpugem.lifting, a faithful
reformulate.m port) against a real model: solve unlifted and lifted, confirm
correctness parity (LiftedSolveComparison, spec FR-006/SC-001), and report the
before/after coefficient-range correction (ScaleReport, spec FR-007/SC-002).

Runtime/performance comparison is explicitly out of scope (spec FR-009) --
unlifted_solve_s/lifted_solve_s are recorded for context only.

See specs/013-cobra-model-lifting/.
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

RESULTS = HERE / "results" / "model_lifting"
RESULTS.mkdir(parents=True, exist_ok=True)

RES_TOL = 1e-4
OBJ_TOL = 1e-6


def _max_abs_among_rows(mat, rows):
    if not rows:
        return 0.0
    sub = sp.csr_matrix(mat)[rows, :]
    data = sub.tocoo().data
    return float(np.max(np.abs(data))) if data.size else 0.0


def scale_report(model_name, lp, lift_big):
    """Apply the same lift_mass_balance/lift_coupling calls
    gpugem.solve(lift=True) would use internally, purely to measure and
    report the before/after coefficient ranges (spec FR-007) -- a separate
    call from the actual solve path, acceptable since this is a reporting
    script, not a performance-critical one."""
    import gpugem

    S = sp.csr_matrix(lp["S"])
    b = np.asarray(lp["b"], dtype=np.float64)
    S_lifted, b_lifted, mapping = gpugem.lift_mass_balance(S, b, big=lift_big)

    mb_before = _max_abs_among_rows(S, mapping.mass_balance_lifted_rows)
    mb_after = _max_abs_among_rows(S_lifted, mapping.mass_balance_lifted_rows)

    coupling_before = coupling_after = None
    if lp.get("C") is not None:
        C = sp.csr_matrix(lp["C"])
        d_lb = np.asarray(lp["d_lb"], dtype=np.float64)
        d_ub = np.asarray(lp["d_ub"], dtype=np.float64)
        C_lifted, d_lb_l, d_ub_l, mapping = gpugem.lift_coupling(
            C, d_lb, d_ub, lift_big, mapping)
        coupling_before = _max_abs_among_rows(C, mapping.coupling_lifted_rows)
        coupling_after = _max_abs_among_rows(C_lifted, mapping.coupling_lifted_rows)

    report = {
        "model": model_name,
        "big": lift_big,
        "mass_balance_max_abs_before": mb_before,
        "mass_balance_max_abs_after": mb_after,
        "coupling_max_abs_before": coupling_before,
        "coupling_max_abs_after": coupling_after,
        "n_mass_balance_rows_lifted": len(mapping.mass_balance_lifted_rows),
        "n_coupling_rows_lifted": len(mapping.coupling_lifted_rows),
        "n_aux_vars_added": mapping.n_aux_vars,
    }

    # Measured and reported, never silently asserted away: the shared-chain
    # step size (reformulate.m's own mode()/min()-based stp, R1) is not
    # mathematically guaranteed to bring *every* tapped entry within `big`
    # when a row's large entries span a wide magnitude range -- confirmed by
    # direct stress-testing during this feature's implementation. This is a
    # property of the reference algorithm itself, not a translation gap.
    report["mass_balance_fully_corrected"] = mb_after <= lift_big + 1e-6
    report["coupling_fully_corrected"] = (
        coupling_after is None or coupling_after <= lift_big + 1e-6
    )
    return report


def build_comparison(model_name, unlifted_status, lifted_status, unlifted_objective,
                      lifted_objective, unlifted_residual, lifted_residual,
                      unlifted_solve_s, lifted_solve_s, obj_tol=OBJ_TOL, res_tol=RES_TOL):
    """Pure comparison/gating logic (no solving) -- kept separate from
    lifted_solve_comparison so it's unit-testable without a GPU (spec/tasks
    T018)."""
    obj_agrees = R.objectives_agree(unlifted_objective, lifted_objective, tol=obj_tol)
    verified_correct = bool(
        unlifted_status == "Optimal" and lifted_status == "Optimal"
        and obj_agrees and lifted_residual is not None and lifted_residual <= res_tol
    )
    return {
        "model": model_name,
        "unlifted_status": unlifted_status,
        "lifted_status": lifted_status,
        "unlifted_objective": unlifted_objective,
        "lifted_objective": lifted_objective,
        "objective_agrees": obj_agrees,
        "unlifted_residual_inf": unlifted_residual,
        "lifted_residual_inf": lifted_residual,
        "verified_correct": verified_correct,
        "unlifted_solve_s": unlifted_solve_s,
        "lifted_solve_s": lifted_solve_s,
    }


def lifted_solve_comparison(model_name, lp, lift_big, time_limit=900.0):
    import gpugem

    S = sp.csr_matrix(lp["S"])
    b = np.asarray(lp["b"], dtype=np.float64)

    t0 = time.perf_counter()
    r_unlifted = gpugem.solve(**lp, time_limit=time_limit)
    unlifted_solve_s = time.perf_counter() - t0
    unlifted_residual = R.feasibility_residual(S, b, r_unlifted.fluxes)

    t0 = time.perf_counter()
    r_lifted = gpugem.solve(**lp, time_limit=time_limit, lift=True, lift_big=lift_big)
    lifted_solve_s = time.perf_counter() - t0
    lifted_residual = R.feasibility_residual(S, b, r_lifted.fluxes)

    return build_comparison(
        model_name, r_unlifted.status, r_lifted.status,
        r_unlifted.objective, r_lifted.objective,
        unlifted_residual, lifted_residual,
        unlifted_solve_s, lifted_solve_s,
    )


def run_model(model_name, lift_big=1000.0, time_limit=900.0):
    lp, _prov = M.build_lp(model_name)

    print("[%s] solving unlifted and lifted (lift_big=%s)..." % (model_name, lift_big),
          flush=True)
    comparison = lifted_solve_comparison(model_name, lp, lift_big, time_limit=time_limit)
    tag = "OK" if comparison["verified_correct"] else "FAILED"
    print("[%s] %s  unlifted_obj=%s  lifted_obj=%s  lifted_residual=%.3e" % (
        tag, model_name, comparison["unlifted_objective"], comparison["lifted_objective"],
        comparison["lifted_residual_inf"]), flush=True)

    report = scale_report(model_name, lp, lift_big)
    print("[%s] scale check: mass-balance %d rows lifted, max|coef| %.3e -> %.3e "
          "(<= big? %s)" % (
              model_name, report["n_mass_balance_rows_lifted"],
              report["mass_balance_max_abs_before"], report["mass_balance_max_abs_after"],
              report["mass_balance_fully_corrected"]), flush=True)
    if report["coupling_max_abs_before"] is not None:
        print("[%s] scale check: coupling %d rows lifted, max|coef| %.3e -> %.3e "
              "(<= big? %s)" % (
                  model_name, report["n_coupling_rows_lifted"],
                  report["coupling_max_abs_before"], report["coupling_max_abs_after"],
                  report["coupling_fully_corrected"]), flush=True)

    out = {"comparison": comparison, "scale_report": report}
    out_path = RESULTS / (model_name + ".json")
    out_path.write_text(json.dumps(out, indent=2))
    print("[%s] wrote %s" % (model_name, out_path), flush=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=list(M.REGISTRY.keys()))
    ap.add_argument("--lift-big", type=float, default=1000.0)
    ap.add_argument("--time-limit", type=float, default=900.0)
    args = ap.parse_args()

    out = run_model(args.model, lift_big=args.lift_big, time_limit=args.time_limit)
    sys.exit(0 if out["comparison"]["verified_correct"] else 1)


if __name__ == "__main__":
    main()
