"""
Core FBA solver — thin wrapper over NVIDIA cuOpt with validated default settings.
"""

from __future__ import annotations

import time
from typing import Any, Optional

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
    lift: bool = False,
    lift_big: float = 1000.0,
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
    lift:
        If ``True``, transform badly-scaled mass-balance and coupling rows into
        an equivalent, better-scaled formulation before solving (a faithful
        port of COBRA Toolbox's ``reformulate.m``, see :mod:`gpugem.lifting`),
        then map the result back to the original variable space. ``False``
        (default) preserves today's behavior exactly -- no existing caller is
        affected. See ``specs/013-cobra-model-lifting/``.
    lift_big:
        Magnitude threshold for lifting (``reformulate.m``'s ``BIG``). Ignored
        when ``lift=False``.
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

    INF = 1e30

    # Original (never-lifted) arrays -- FBAResult is always reported in this
    # space, and feasibility is always checked against this space, regardless
    # of whether lifting is used internally (specs/013-cobra-model-lifting/
    # research.md R6).
    S_orig = sp.csr_matrix(S).astype(np.float64)
    b_orig = np.asarray(b, dtype=np.float64)
    lb_orig = np.asarray(lb, dtype=np.float64)
    ub_orig = np.asarray(ub, dtype=np.float64)
    c_orig = np.asarray(c, dtype=np.float64)
    C_orig = sp.csr_matrix(C).astype(np.float64) if C is not None else None
    n_vars_original = S_orig.shape[1]
    n_stoich_original = S_orig.shape[0]
    if C_orig is not None:
        d_lb_orig = (np.asarray(d_lb, dtype=np.float64) if d_lb is not None
                     else np.full(C_orig.shape[0], -INF))
        d_ub_orig = (np.asarray(d_ub, dtype=np.float64) if d_ub is not None
                     else np.full(C_orig.shape[0], INF))
    else:
        d_lb_orig = d_ub_orig = None

    lifting_mapping = None
    if lift:
        from gpugem.lifting import lift_coupling as _lift_coupling
        from gpugem.lifting import lift_mass_balance as _lift_mass_balance

        S_solve, b_solve, lifting_mapping = _lift_mass_balance(S_orig, b_orig, big=lift_big)
        n_mb_aux = lifting_mapping.n_aux_vars

        if C_orig is not None:
            C_solve, d_lb_solve, d_ub_solve, lifting_mapping = _lift_coupling(
                C_orig, d_lb_orig, d_ub_orig, lift_big, lifting_mapping
            )
            n_extra_aux = lifting_mapping.n_aux_vars - n_mb_aux
            if n_extra_aux > 0:
                # S and C share one variable space -- pad S with zero columns
                # for any auxiliary variables lift_coupling added beyond
                # lift_mass_balance's own (mirrors gpugem/scaling.py's
                # analogous C-padding for S's own aux vars, in reverse).
                S_solve = sp.hstack(
                    [S_solve, sp.csr_matrix((S_solve.shape[0], n_extra_aux))],
                    format="csr",
                )
        else:
            C_solve, d_lb_solve, d_ub_solve = None, None, None
            n_extra_aux = 0

        n_aux_total = lifting_mapping.n_aux_vars
        lb_solve = np.concatenate([lb_orig, np.full(n_aux_total, -INF)])
        ub_solve = np.concatenate([ub_orig, np.full(n_aux_total, INF)])
        c_solve = np.concatenate([c_orig, np.zeros(n_aux_total)])
    else:
        S_solve, b_solve = S_orig, b_orig
        lb_solve, ub_solve, c_solve = lb_orig, ub_orig, c_orig
        C_solve, d_lb_solve, d_ub_solve = C_orig, d_lb_orig, d_ub_orig

    S_csr = sp.csr_matrix(S_solve)
    n_vars = S_csr.shape[1]
    n_stoich = S_csr.shape[0]

    # Build full constraint matrix A = [S; C] (possibly lifted)
    if C_solve is not None:
        C_csr = sp.csr_matrix(C_solve)
        A = sp.vstack([S_csr, C_csr], format="csr")
        con_lb = np.concatenate([b_solve, d_lb_solve])
        con_ub = np.concatenate([b_solve, d_ub_solve])
    else:
        A = S_csr
        con_lb = np.asarray(b_solve, dtype=np.float64)
        con_ub = np.asarray(b_solve, dtype=np.float64)

    A = A.astype(np.float64)
    lb, ub, c = lb_solve, ub_solve, c_solve

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

    # Which underlying method actually produced the solution (relevant for method=Concurrent)
    solved_by = None
    try:
        solved_by = sol.get_solved_by().name
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
                if lift:
                    from gpugem.lifting import map_back as _map_back

                    x = _map_back(x, lifting_mapping)

                if len(x) == n_vars_original:
                    fluxes = x
                    if check_feasibility:
                        # Always checked against the ORIGINAL, unlifted system
                        # -- a caller sees honest diagnostics about the model
                        # they asked to solve, never the internally-lifted one
                        # (specs/013-cobra-model-lifting/research.md R6).
                        if C_orig is not None:
                            A_orig = sp.vstack([S_orig, C_orig], format="csr")
                            con_lb_orig = np.concatenate([b_orig, d_lb_orig])
                            con_ub_orig = np.concatenate([b_orig, d_ub_orig])
                        else:
                            A_orig = S_orig
                            con_lb_orig = b_orig
                            con_ub_orig = b_orig

                        Ax = A_orig @ fluxes
                        con_viol = (np.maximum(con_lb_orig - Ax, 0.0)
                                    + np.maximum(Ax - con_ub_orig, 0.0))
                        var_viol = (np.maximum(lb_orig - fluxes, 0.0)
                                    + np.maximum(fluxes - ub_orig, 0.0))
                        stoich_viol = con_viol[:n_stoich_original]

                        feasibility = {
                            "stoich_max_residual": float(stoich_viol.max()),
                            "stoich_rows_violated_1e6": int((stoich_viol > 1e-6).sum()),
                            "coupling_max_residual": (
                                float(con_viol[n_stoich_original:].max())
                                if C_orig is not None else 0.0
                            ),
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
        solved_by=solved_by,
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
