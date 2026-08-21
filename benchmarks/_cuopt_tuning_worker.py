"""Subprocess entry point for one S85 cuOpt-tuning candidate.

Never invoked directly by a user -- launched by run_cuopt_tuning.py as
`python -m benchmarks._cuopt_tuning_worker <candidate_id>` so an untested setting
(new to this investigation: Fast1, true Mixed precision, PSLP re-tested, warm
start) cannot take down the orchestrator or the other candidates, matching
specs/004-s85-solver-mode-experiment/'s subprocess-isolation pattern
(specs/012-cuopt-native-tuning/research.md R6).

Non-warm-start candidates go through gpugem.solve's existing **cuopt_kwargs
override mechanism -- gpugem/_defaults.py is never touched (spec FR-009).
Warm-start candidates need the cold solve's warm-start data fed into a second
solve, which gpugem.solve does not expose (it builds a fresh SolverSettings
internally every call); those two candidates use cuOpt's raw
DataModel/SolverSettings/Solve API directly here, in this file only -- no new
gpugem public surface (plan.md Constitution Check).

cuOpt's own logging writes to the OS-level stdout file descriptor directly, so
it cannot be cleanly separated from this script's own output by reassigning
sys.stdout. Instead, this script guarantees its one JSON result is the *last*
line written to stdout; the orchestrator parses only the final non-empty line.
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

from benchmarks import models as M
from benchmarks import residual as R
from benchmarks import cuopt_tuning_candidates as C

_STATUS_NAMES = {
    0: "NoTermination", 1: "Optimal", 2: "Infeasible", 3: "Unbounded",
    4: "IterationLimit", 5: "TimeLimit", 6: "NumericalError", 7: "PrimalFeasible",
    8: "FeasibleFound", 9: "ConcurrentLimit",
}
_HAS_SOLUTION = frozenset([1, 5, 7])


def _solve_single(lp, time_limit, cuopt_kwargs):
    """Non-warm-start path: gpugem.solve's existing per-call override mechanism."""
    import gpugem

    solver_args = {k: lp[k] for k in ("S", "b", "lb", "ub", "c", "maximize") if k in lp}
    for k in ("C", "d_lb", "d_ub"):
        if lp.get(k) is not None:
            solver_args[k] = lp[k]

    res = gpugem.solve(time_limit=time_limit, check_feasibility=True,
                        **solver_args, **cuopt_kwargs)
    return {
        "phase": "single",
        "solve_s": float(res.wall_time_s),
        "status": res.status,
        "iterations": res.n_iterations,
        "objective": None if res.objective is None else float(res.objective),
        "fluxes": None if res.fluxes is None else res.fluxes,
    }


def _build_raw_datamodel(lp):
    """Mirrors gpugem/solver.py's solve()'s A=[S;C] construction exactly, needed
    here only because the warm-start phase pair must keep the raw cuOpt
    Solution object alive across two Solve() calls, which gpugem.solve does not
    expose."""
    from cuopt.linear_programming import DataModel

    INF = 1e30
    S_csr = sp.csr_matrix(lp["S"]).astype(np.float64)
    n_vars = S_csr.shape[1]
    n_stoich = S_csr.shape[0]
    C = lp.get("C")

    if C is not None:
        C_csr = sp.csr_matrix(C)
        A = sp.vstack([S_csr, C_csr], format="csr")
        d_lb = lp.get("d_lb")
        d_ub = lp.get("d_ub")
        _d_lb = (np.asarray(d_lb, dtype=np.float64) if d_lb is not None
                 else np.full(C_csr.shape[0], -INF))
        _d_ub = (np.asarray(d_ub, dtype=np.float64) if d_ub is not None
                 else np.full(C_csr.shape[0], INF))
        con_lb = np.concatenate([np.asarray(lp["b"], dtype=np.float64), _d_lb])
        con_ub = np.concatenate([np.asarray(lp["b"], dtype=np.float64), _d_ub])
    else:
        A = S_csr
        con_lb = np.asarray(lp["b"], dtype=np.float64)
        con_ub = np.asarray(lp["b"], dtype=np.float64)
    A = A.astype(np.float64)

    dm = DataModel()
    dm.set_csr_constraint_matrix(A.data.astype(np.float64), A.indices.astype(np.int32),
                                  A.indptr.astype(np.int32))
    dm.set_constraint_lower_bounds(con_lb)
    dm.set_constraint_upper_bounds(con_ub)
    dm.set_variable_lower_bounds(np.asarray(lp["lb"], dtype=np.float64))
    dm.set_variable_upper_bounds(np.asarray(lp["ub"], dtype=np.float64))
    dm.set_objective_coefficients(np.asarray(lp["c"], dtype=np.float64))
    dm.set_maximize(bool(lp.get("maximize", False)))
    return dm, A, con_lb, con_ub, n_vars, n_stoich


def _settings_for(n_vars, time_limit, cuopt_kwargs):
    from cuopt.linear_programming import SolverSettings
    from gpugem._defaults import default_settings

    params = default_settings(n_vars, time_limit=time_limit)
    params.update(cuopt_kwargs)
    settings = SolverSettings()
    for k, v in params.items():
        settings.set_parameter(k, v)
    return settings


def _phase_from_sol(sol, phase_name, t_wall):
    status_code = int(sol.get_termination_status())
    status_name = _STATUS_NAMES.get(status_code, "Unknown(%d)" % status_code)
    iterations = None
    try:
        stats = sol.get_lp_stats()
        if isinstance(stats, dict) and "nb_iterations" in stats:
            iterations = int(stats["nb_iterations"])
    except Exception:
        pass
    objective = None
    fluxes = None
    if status_code in _HAS_SOLUTION:
        try:
            objective = float(sol.get_primal_objective())
            fluxes = np.asarray(sol.get_primal_solution(), dtype=np.float64)
        except Exception:
            pass
    return {
        "phase": phase_name,
        "solve_s": float(t_wall),
        "status": status_name,
        "iterations": iterations,
        "objective": objective,
        "fluxes": fluxes,
    }


def _solve_warm_start(lp, time_limit, cuopt_kwargs):
    """Cold phase (produces warm-start data), then warm phase (consumes it) --
    presolve=0 + pdlp_solver_mode in {Stable2, Fast1} only, per
    specs/012-cuopt-native-tuning/research.md R4."""
    import time
    from cuopt.linear_programming import Solve, SolverSettings

    dm, A, con_lb, con_ub, n_vars, n_stoich = _build_raw_datamodel(lp)

    cold_settings = _settings_for(n_vars, time_limit, cuopt_kwargs)
    t0 = time.perf_counter()
    sol_cold = Solve(dm, cold_settings)
    cold_wall = time.perf_counter() - t0
    cold_phase = _phase_from_sol(sol_cold, "cold", cold_wall)

    warm_settings = _settings_for(n_vars, time_limit, cuopt_kwargs)
    warm_data = sol_cold.get_pdlp_warm_start_data()
    warm_settings.set_pdlp_warm_start_data(warm_data)
    t0 = time.perf_counter()
    sol_warm = Solve(dm, warm_settings)
    warm_wall = time.perf_counter() - t0
    warm_phase = _phase_from_sol(sol_warm, "warm", warm_wall)

    return [cold_phase, warm_phase]


def _solve_preprocessing(preproc, time_limit):
    """User Story 3: apply the transform, solve the transformed LP, invert the
    solution back to the original variable space, and re-check correctness
    against the *original* S/b -- reconstruction_verified MUST be set before
    solve_s is treated as meaningful (spec FR-008/SC-003)."""
    from benchmarks import cuopt_tuning_preprocessing as P

    lp, _ = M.build_lp("S85")
    S_orig = sp.csr_matrix(lp["S"])
    b_orig = np.asarray(lp["b"], dtype=np.float64)

    transformed_lp, context = P.transform(lp)
    phase = _solve_single(transformed_lp, time_limit, {})
    reconstructed_fluxes = P.inverse(phase["fluxes"], context)

    residual_inf = R.feasibility_residual(S_orig, b_orig, reconstructed_fluxes)
    phase = dict(phase)
    phase["fluxes"] = reconstructed_fluxes
    phase["phase"] = "preprocessing_reconstructed"
    return [phase], residual_inf


def main():
    ap = argparse.ArgumentParser()
    all_ids = [c["id"] for c in C.CANDIDATES] + [c["id"] for c in C.PREPROCESSING_CANDIDATES]
    ap.add_argument("candidate_id", choices=all_ids)
    ap.add_argument("--time-limit", type=float, default=900.0)
    ap.add_argument("--cuopt-version", default=None,
                     help="recorded verbatim in the result; defaults to the "
                          "running interpreter's installed cuopt.__version__")
    args = ap.parse_args()

    is_preprocessing = args.candidate_id in {c["id"] for c in C.PREPROCESSING_CANDIDATES}

    if is_preprocessing:
        preproc = next(c for c in C.PREPROCESSING_CANDIDATES if c["id"] == args.candidate_id)
        phases, residual_inf = _solve_preprocessing(preproc, args.time_limit)
        claimed = phases[-1]
        user_story = preproc["user_story"]
        cuopt_kwargs = {}
        source_note = preproc["source_note"]
        # Reconstruction is checked at the same tolerance published for S85
        # (results/S85.json's res_tol) -- read here rather than hardcoded, so
        # this never silently drifts from the project's actual gate.
        s85_result_path = HERE / "results" / "S85.json"
        res_tol = (json.loads(s85_result_path.read_text())["res_tol"]
                   if s85_result_path.exists() else 1e-4)
        reconstruction_verified = bool(
            claimed["status"] == "Optimal" and residual_inf <= res_tol)
    else:
        candidate = C.get_candidate(args.candidate_id)
        lp, prov = M.build_lp("S85")
        S_eq = sp.csr_matrix(lp["S"])
        b_eq = np.asarray(lp["b"], dtype=np.float64)

        if candidate["warm_start"]:
            phases = _solve_warm_start(lp, args.time_limit, candidate["cuopt_kwargs"])
        else:
            phases = [_solve_single(lp, args.time_limit, candidate["cuopt_kwargs"])]

        claimed = phases[-1]
        residual_inf = R.feasibility_residual(S_eq, b_eq, claimed["fluxes"])
        user_story = candidate["user_story"]
        cuopt_kwargs = candidate["cuopt_kwargs"]
        source_note = candidate["source_note"]
        reconstruction_verified = None  # not applicable outside User Story 3

    cuopt_version = args.cuopt_version
    if cuopt_version is None:
        import cuopt
        cuopt_version = getattr(cuopt, "__version__", "unknown")

    out_phases = []
    for p in phases:
        p = dict(p)
        p.pop("fluxes", None)
        out_phases.append(p)

    result = {
        "id": args.candidate_id,
        "user_story": user_story,
        "cuopt_version": cuopt_version,
        "cuopt_kwargs": cuopt_kwargs,
        "phases": out_phases,
        "status": claimed["status"],
        "solve_s": claimed["solve_s"],
        "iterations": claimed["iterations"],
        "objective": claimed["objective"],
        "residual_inf": residual_inf,
        "source_note": source_note,
        "reconstruction_verified": reconstruction_verified,
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
