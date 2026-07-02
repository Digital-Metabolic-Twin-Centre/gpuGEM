"""Convenience wrapper: solve a COBRApy model directly."""

from __future__ import annotations
from typing import Any

from gpugem.loaders import from_cobra
from gpugem.result import FBAResult
from gpugem import solver as _solver


def solve_cobra(model, time_limit: float = 60.0, **cuopt_kwargs: Any) -> FBAResult:
    """
    Solve a COBRApy ``Model`` using GPU-accelerated PDLP.

    Parameters
    ----------
    model:
        A ``cobra.Model`` instance.
    time_limit:
        Wall-clock time limit in seconds.
    **cuopt_kwargs:
        Any cuOpt parameter override (e.g. ``pdlp_solver_mode=0``).

    Returns
    -------
    FBAResult
    """
    arrays = from_cobra(model)
    return _solver.solve(**arrays, time_limit=time_limit, **cuopt_kwargs)
