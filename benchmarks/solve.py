"""Solver wrappers: cuOpt (gpuGEM shipped defaults) and Gurobi standalone.

Both receive the identical LP dict from benchmarks.models.build_lp.
"""
from __future__ import annotations

import time

import numpy as np
import scipy.sparse as sp

_INF = 1e30
_CUOPT_HAS_SOLUTION = {"Optimal", "TimeLimit", "PrimalFeasible", "FeasibleFound"}


def _solver_args(lp):
    args = {k: lp[k] for k in ("S", "b", "lb", "ub", "c", "maximize") if k in lp}
    for k in ("C", "d_lb", "d_ub"):
        if lp.get(k) is not None:
            args[k] = lp[k]
    return args


def solve_cuopt(lp, time_limit=900.0):
    """Solve with gpugem.solve -- cuOpt PDLP + size-selected shipped defaults."""
    import gpugem

    res = gpugem.solve(time_limit=time_limit, check_feasibility=True, **_solver_args(lp))
    return {
        "solver": "cuopt",
        "solve_s": float(res.wall_time_s),
        "objective": None if res.objective is None else float(res.objective),
        "status": res.status,
        "iters": res.n_iterations,
        "fluxes": None if res.fluxes is None else np.asarray(res.fluxes, dtype=np.float64),
        "settings": dict(res.solver_settings),
        "feasibility": dict(res.feasibility),
    }


# Gurobi error numbers for "no licence" and "model exceeds size-limited licence" (from the Gurobi
# reference manual; NOT verified on this repo's CI because gurobipy is not installed here).
_GUROBI_LICENCE_ERRNOS = (10009, 10010)


def solve_gurobi(lp, time_limit=900.0, method=2):
    """Solve with Gurobi standalone. method=2 -> barrier (+ default crossover).

    A missing/invalid/size-limited licence is raised as ``DependencyError(kind="license")`` so it
    is distinguishable from "gurobipy not installed" and from a failed solve.
    """
    from gpugem._deps import DependencyError, require

    gp = require("gurobipy")
    try:
        return _solve_gurobi(lp, time_limit, method)
    except gp.GurobiError as exc:
        no_licence = (getattr(exc, "errno", None) in _GUROBI_LICENCE_ERRNOS
                      or "licen" in str(exc).lower())
        if not no_licence:
            raise
        raise DependencyError(
            "gurobipy", "license",
            "obtain a Gurobi licence (free academic licences: "
            "https://www.gurobi.com/academia/academic-program-and-licenses/), set GRB_LICENSE_FILE "
            "to it, and run `grbprobe` to check it; models above the size-limited licence "
            "need a full licence",
            purpose=_deps_purpose(),
            detail="%s: %s" % (type(exc).__name__, exc)) from exc


def _deps_purpose():
    from gpugem._deps import REGISTRY
    return REGISTRY["gurobipy"].purpose


def _solve_gurobi(lp, time_limit, method):
    import gurobipy as gp
    from gurobipy import GRB

    env = gp.Env(empty=True)
    env.setParam("OutputFlag", 0)
    env.start()
    m = gp.Model(env=env)
    m.Params.OutputFlag = 0
    m.Params.TimeLimit = time_limit
    m.Params.Method = method

    S = sp.csr_matrix(lp["S"])
    n = S.shape[1]
    lb = np.asarray(lp["lb"], dtype=np.float64).copy()
    ub = np.asarray(lp["ub"], dtype=np.float64).copy()
    lb[lb <= -_INF] = -GRB.INFINITY
    ub[ub >= _INF] = GRB.INFINITY

    v = m.addMVar(n, lb=lb, ub=ub, name="v")
    sense = GRB.MAXIMIZE if lp["maximize"] else GRB.MINIMIZE
    m.setMObjective(None, np.asarray(lp["c"], dtype=np.float64), 0.0, sense=sense)

    if S.shape[0]:
        m.addMConstr(S, v, "=", np.asarray(lp["b"], dtype=np.float64))

    if lp.get("C") is not None:
        C = sp.csr_matrix(lp["C"])
        dlb = np.asarray(lp["d_lb"], dtype=np.float64)
        dub = np.asarray(lp["d_ub"], dtype=np.float64)
        low = dlb > -_INF
        high = dub < _INF
        eqm = low & high & (np.abs(dub - dlb) < 1e-9)
        um = high & ~eqm
        lm = low & ~eqm
        if eqm.any():
            m.addMConstr(C[eqm], v, "=", dub[eqm])
        if um.any():
            m.addMConstr(C[um], v, "<", dub[um])
        if lm.any():
            m.addMConstr(C[lm], v, ">", dlb[lm])

    m.update()
    t = time.perf_counter()
    m.optimize()
    solve_s = time.perf_counter() - t

    status_map = {GRB.OPTIMAL: "Optimal", GRB.INFEASIBLE: "Infeasible",
                  GRB.UNBOUNDED: "Unbounded", GRB.INF_OR_UNBD: "InfOrUnbd",
                  GRB.TIME_LIMIT: "TimeLimit"}
    status = status_map.get(m.Status, "Status%d" % m.Status)

    obj = None
    fluxes = None
    iters = None
    bar_iters = None
    simplex_iters = None
    if m.SolCount > 0:
        obj = float(m.ObjVal)
        fluxes = np.asarray(v.X, dtype=np.float64)
    try:
        bar_iters = int(m.BarIterCount)
        simplex_iters = int(m.IterCount)
        iters = bar_iters if bar_iters > 0 else simplex_iters
    except Exception:
        pass

    m.dispose()
    env.dispose()
    return {
        "solver": "gurobi",
        "solve_s": float(solve_s),
        "objective": obj,
        "status": status,
        "iters": iters,
        "fluxes": fluxes,
        "method": method,
        "bar_iters": bar_iters,
        "simplex_iters": simplex_iters,
    }
