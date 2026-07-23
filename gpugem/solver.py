"""
Core FBA solver — thin wrapper over NVIDIA cuOpt with validated default settings.
"""

from __future__ import annotations

import time
from typing import Any, Optional, Union

import numpy as np
import scipy.sparse as sp

from gpugem._defaults import default_settings
from gpugem.result import FBAResult

# cuOpt termination status codes
_STATUS_NAMES = {
    0: "NoTermination",
    1: "Optimal",
    2: "Infeasible",
    3: "Unbounded",
    4: "IterationLimit",
    5: "TimeLimit",
    6: "NumericalError",
    7: "PrimalFeasible",
    8: "FeasibleFound",
    9: "ConcurrentLimit",
}

_HAS_SOLUTION = frozenset([1, 5, 7])   # status codes that carry a primal solution


def solve(
    S: sp.spmatrix,
    b: np.ndarray,
    lb: np.ndarray,
    ub: np.ndarray,
    c: np.ndarray,
    *,
    C: Optional[sp.spmatrix] = None,
    d_lb: Optional[np.ndarray] = None,
    d_ub: Optional[np.ndarray] = None,
    maximize: bool = False,
    time_limit: float = 60.0,
    check_feasibility: bool = True,
    **cuopt_kwargs: Any,
) -> FBAResult:
    """
    Solve a Flux Balance Analysis LP using GPU-accelerated PDLP.

    The LP solved is::

        min/max  c @ v
        s.t.     S @ v  = b          (stoichiometric equalities)
                 d_lb ≤ C @ v ≤ d_ub (coupling constraints, optional)
                 lb ≤ v ≤ ub

    Smart defaults are chosen based on model size (see :mod:`gpugem._defaults`).
    Any cuOpt parameter can be overridden via keyword arguments.

    Parameters
    ----------
    S:
        Stoichiometric matrix (m_stoich × n_vars), sparse.
    b:
        RHS of the stoichiometric equalities (m_stoich,).
    lb, ub:
        Variable lower/upper bounds (n_vars,).
    c:
        Objective coefficient vector (n_vars,).
    C:
        Coupling constraint matrix (m_coupling × n_vars), optional sparse.
    d_lb, d_ub:
        Lower/upper bounds for coupling constraints (m_coupling,).
        Pass ``None`` or ``-inf``/``+inf`` for one-sided constraints.
    maximize:
        ``True`` for maximisation, ``False`` (default) for minimisation.
    time_limit:
        Wall-clock time limit in seconds (passed to cuOpt).
    check_feasibility:
        If ``True``, compute constraint residuals and include them in the result.
    **cuopt_kwargs:
        Any additional cuOpt parameter passed directly to ``SolverSettings``,
        overriding the defaults (e.g. ``pdlp_solver_mode=0``, ``presolve=0``).

    Returns
    -------
    FBAResult

    Examples
    --------
    Basic usage with a COBRApy model::

        import cobra
        import gpugem

        model = cobra.io.read_sbml_model("e_coli_core.xml")
        result = gpugem.solve_cobra(model)
        print(result.objective, result.status)

    Passing extra cuOpt settings::

        result = gpugem.solve(S, b, lb, ub, c, maximize=True,
                              pdlp_solver_mode=0, time_limit=300)
    """
    from cuopt.linear_programming import DataModel, Solve, SolverSettings

    S_csr = sp.csr_matrix(S)
    n_vars = S_csr.shape[1]
    n_stoich = S_csr.shape[0]

    # Build full constraint matrix A = [S; C]
    INF = 1e30
    if C is not None:
        C_csr = sp.csr_matrix(C)
        A = sp.vstack([S_csr, C_csr], format="csr")

        _d_lb = np.asarray(d_lb, dtype=np.float64) if d_lb is not None else np.full(C_csr.shape[0], -INF)
        _d_ub = np.asarray(d_ub, dtype=np.float64) if d_ub is not None else np.full(C_csr.shape[0],  INF)

        con_lb = np.concatenate([b, _d_lb])
        con_ub = np.concatenate([b, _d_ub])
    else:
        A = S_csr
        con_lb = np.asarray(b, dtype=np.float64)
        con_ub = np.asarray(b, dtype=np.float64)

    A = A.astype(np.float64)

    # Build DataModel
    dm = DataModel()
    dm.set_csr_constraint_matrix(
        A.data.astype(np.float64),
        A.indices.astype(np.int32),
        A.indptr.astype(np.int32),
    )
    dm.set_constraint_lower_bounds(con_lb)
    dm.set_constraint_upper_bounds(con_ub)
    dm.set_variable_lower_bounds(np.asarray(lb, dtype=np.float64))
    dm.set_variable_upper_bounds(np.asarray(ub, dtype=np.float64))
    dm.set_objective_coefficients(np.asarray(c, dtype=np.float64))
    dm.set_maximize(bool(maximize))

    # Merge default settings with user overrides
    params = default_settings(n_vars, time_limit=time_limit)
    params.update(cuopt_kwargs)

    settings = SolverSettings()
    applied, rejected = {}, {}
    for k, v in params.items():
        try:
            settings.set_parameter(k, v)
            applied[k] = v
        except Exception as e:
            rejected[k] = {"value": v, "error": str(e)}

    # Solve
    t0 = time.perf_counter()
    sol = Solve(dm, settings)
    wall_time = time.perf_counter() - t0

    status_code = int(sol.get_termination_status())
    status_name = _STATUS_NAMES.get(status_code, f"Unknown({status_code})")

    # Solver-reported convergence statistics (PDLP iterations, residuals, gap)
    solver_stats = {}
    n_iterations = None
    try:
        stats = sol.get_lp_stats()
        if isinstance(stats, dict):
            solver_stats = dict(stats)
            if "nb_iterations" in stats:
                n_iterations = int(stats["nb_iterations"])
    except Exception:
        pass

    # Extract solution
    fluxes = None
    objective = None
    feasibility = {}

    if status_code in _HAS_SOLUTION:
        try:
            x = np.asarray(sol.get_primal_solution(), dtype=np.float64)
            objective = float(sol.get_primal_objective())

            if len(x) == n_vars:
                fluxes = x
                if check_feasibility:
                    Ax = A @ x
                    con_viol = np.maximum(con_lb - Ax, 0.0) + np.maximum(Ax - con_ub, 0.0)
                    var_viol = np.maximum(lb - x, 0.0) + np.maximum(x - ub, 0.0)
                    stoich_viol = con_viol[:n_stoich]

                    feasibility = {
                        "stoich_max_residual": float(stoich_viol.max()),
                        "stoich_rows_violated_1e6": int((stoich_viol > 1e-6).sum()),
                        "coupling_max_residual": float(con_viol[n_stoich:].max()) if C is not None else 0.0,
                        "var_bounds_max_violation": float(var_viol.max()),
                    }
        except Exception:
            pass

    if rejected:
        import warnings
        warnings.warn(
            f"The following cuOpt parameters were rejected: {list(rejected.keys())}. "
            "They will be ignored.",
            stacklevel=2,
        )

    return FBAResult(
        status=status_name,
        objective=objective,
        fluxes=fluxes,
        wall_time_s=round(wall_time, 4),
        solver_settings=applied,
        feasibility=feasibility,
        n_iterations=n_iterations,
        solver_stats=solver_stats,
    )


class FBASolver:
    """
    Stateful FBA solver — useful when solving the same model structure repeatedly
    (e.g. iterating over many patient models or perturbations).

    Parameters
    ----------
    S, b, lb, ub, c, C, d_lb, d_ub, maximize:
        Same as :func:`solve`.
    time_limit:
        Default time limit; can be overridden per call to :meth:`solve`.
    **cuopt_kwargs:
        Default cuOpt parameter overrides; can be overridden per call.
    """

    def __init__(
        self,
        S: sp.spmatrix,
        b: np.ndarray,
        lb: np.ndarray,
        ub: np.ndarray,
        c: np.ndarray,
        *,
        C: Optional[sp.spmatrix] = None,
        d_lb: Optional[np.ndarray] = None,
        d_ub: Optional[np.ndarray] = None,
        maximize: bool = False,
        time_limit: float = 60.0,
        **cuopt_kwargs: Any,
    ) -> None:
        self._S = S
        self._b = b
        self._lb = lb
        self._ub = ub
        self._c = c
        self._C = C
        self._d_lb = d_lb
        self._d_ub = d_ub
        self._maximize = maximize
        self._time_limit = time_limit
        self._defaults = cuopt_kwargs

    def solve(
        self,
        c: Optional[np.ndarray] = None,
        lb: Optional[np.ndarray] = None,
        ub: Optional[np.ndarray] = None,
        time_limit: Optional[float] = None,
        **cuopt_kwargs: Any,
    ) -> FBAResult:
        """
        Solve the LP, optionally overriding objective or bounds for this call.

        Parameters
        ----------
        c:
            Override objective vector for this solve only.
        lb, ub:
            Override variable bounds for this solve only.
        time_limit:
            Override time limit for this solve only.
        **cuopt_kwargs:
            Additional cuOpt parameter overrides for this solve only.
        """
        params = dict(self._defaults)
        params.update(cuopt_kwargs)

        return solve(
            S=self._S,
            b=self._b,
            lb=lb if lb is not None else self._lb,
            ub=ub if ub is not None else self._ub,
            c=c if c is not None else self._c,
            C=self._C,
            d_lb=self._d_lb,
            d_ub=self._d_ub,
            maximize=self._maximize,
            time_limit=time_limit if time_limit is not None else self._time_limit,
            **params,
        )
