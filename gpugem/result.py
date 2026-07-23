"""FBA result container."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import numpy as np


@dataclass
class FBAResult:
    """Result returned by :func:`gpugem.solve`."""

    status: str
    """Solver termination status (e.g. ``'Optimal'``, ``'TimeLimit'``)."""

    objective: Optional[float]
    """Optimal objective value, or ``None`` if no solution was found."""

    fluxes: Optional[np.ndarray]
    """Flux vector in the original variable space, or ``None`` if unavailable."""

    wall_time_s: float
    """Total wall-clock solve time in seconds (includes presolve)."""

    solver_settings: dict = field(default_factory=dict)
    """The cuOpt parameters that were actually applied."""

    feasibility: dict = field(default_factory=dict)
    """Feasibility diagnostics: max constraint residual, violated row counts, etc."""

    n_iterations: Optional[int] = None
    """Number of PDLP iterations reported by the solver, or ``None`` if unavailable."""

    solver_stats: dict = field(default_factory=dict)
    """Solver-reported convergence statistics (``primal_residual``, ``dual_residual``,
    ``gap``, ``nb_iterations``) as returned by cuOpt's ``get_lp_stats()``."""

    def __repr__(self) -> str:
        obj = f"{self.objective:.6g}" if self.objective is not None else "None"
        iters = f", iters={self.n_iterations}" if self.n_iterations is not None else ""
        return (
            f"FBAResult(status={self.status!r}, objective={obj}, "
            f"time={self.wall_time_s:.3f}s{iters})"
        )
