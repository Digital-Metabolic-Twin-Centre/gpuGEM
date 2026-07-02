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

    def __repr__(self) -> str:
        obj = f"{self.objective:.6g}" if self.objective is not None else "None"
        return (
            f"FBAResult(status={self.status!r}, objective={obj}, "
            f"time={self.wall_time_s:.3f}s)"
        )
