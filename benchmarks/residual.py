"""Feasibility residual and objective-agreement checks (correctness gate)."""
from __future__ import annotations

import numpy as np
import scipy.sparse as sp


def feasibility_residual(S, b, v) -> float:
    """||S v - b||_inf on the equality (stoichiometric) rows."""
    if v is None:
        return float("inf")
    r = sp.csr_matrix(S) @ np.asarray(v, dtype=np.float64) - np.asarray(b, dtype=np.float64)
    if r.size == 0:
        return 0.0
    return float(np.max(np.abs(r)))


def objectives_agree(o1, o2, tol: float = 1e-6) -> bool:
    if o1 is None or o2 is None:
        return False
    denom = max(1.0, abs(o1), abs(o2))
    return abs(o1 - o2) / denom <= tol
