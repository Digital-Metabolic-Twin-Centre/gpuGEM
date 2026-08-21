"""The one last-resort, non-simplifying preprocessing candidate (User Story 3).

External row/column (Ruiz-style geometric) equilibration on S85's mass-balance
matrix S, tuned to its known [1e-6, 2e5] coefficient range
(specs/012-cuopt-native-tuning/research.md R5). Purely a linear reformulation:
the transform and its inverse are exact (no rows/columns dropped, no
approximation), so the reconstructed result must equal the original model's
result up to the same tolerance every other candidate is held to (spec FR-008).

cuOpt already performs its own internal Ruiz equilibration before the first PDLP
iteration (research.md R5) -- this external pass is not expected to add much on
top of that; it exists to make the "did we even try improving the matrix's
conditioning directly" question answerable, honestly, as the discouraged
fallback the spec frames it as (research.md R8).
"""
from __future__ import annotations

import numpy as np
import scipy.sparse as sp

_INF = 1e30


def _row_minmax_abs(A_csr):
    """Vectorized per-row min/max of |A_ij| over nonzeros only (rows with no
    nonzeros get min=max=1.0, i.e. no scaling)."""
    indptr = A_csr.indptr
    data = np.abs(A_csr.data)
    n_rows = A_csr.shape[0]
    nnz_per_row = np.diff(indptr)
    nonempty = nnz_per_row > 0
    starts = indptr[:-1][nonempty]
    row_min = np.ones(n_rows)
    row_max = np.ones(n_rows)
    if starts.size:
        row_max[nonempty] = np.maximum.reduceat(data, starts)
        row_min[nonempty] = np.minimum.reduceat(data, starts)
    return row_min, row_max


def _col_minmax_abs(A_csr):
    return _row_minmax_abs(A_csr.tocsc().T.tocsr())


def ruiz_scale(S, n_iters=3):
    """Return (row_scale, col_scale) such that diag(row_scale) @ S @
    diag(col_scale) is better-conditioned -- standard Ruiz geometric-mean
    equilibration, iterated a few times."""
    A = sp.csr_matrix(S).astype(np.float64)
    m, n = A.shape
    row_scale = np.ones(m)
    col_scale = np.ones(n)

    for _ in range(n_iters):
        row_min, row_max = _row_minmax_abs(A)
        r = 1.0 / np.sqrt(row_min * row_max)
        r[~np.isfinite(r)] = 1.0
        A = sp.diags(r) @ A
        row_scale *= r

        col_min, col_max = _col_minmax_abs(A)
        cst = 1.0 / np.sqrt(col_min * col_max)
        cst[~np.isfinite(cst)] = 1.0
        A = A @ sp.diags(cst)
        col_scale *= cst

    return row_scale, col_scale


def transform(lp):
    """Apply row/column equilibration to lp's S block and every array that
    shares the variable space with it (lb, ub, c). C (coupling), if present, is
    column-rescaled the same way for consistency but not row-rescaled -- row
    scaling an inequality/coupling row is equally exact, but S is this
    candidate's actual target (research.md R5's ill-conditioning finding is
    about S specifically).

    Returns (transformed_lp, context) where context carries what's needed to
    invert the solution exactly.
    """
    S = sp.csr_matrix(lp["S"]).astype(np.float64)
    row_scale, col_scale = ruiz_scale(S)

    S_t = sp.diags(row_scale) @ S @ sp.diags(col_scale)
    b_t = row_scale * np.asarray(lp["b"], dtype=np.float64)

    # v = col_scale * v'  =>  lb'_j = lb_j / col_scale_j (col_scale > 0 by construction)
    lb = np.asarray(lp["lb"], dtype=np.float64)
    ub = np.asarray(lp["ub"], dtype=np.float64)
    lb_t = np.where(lb <= -_INF, lb, lb / col_scale)
    ub_t = np.where(ub >= _INF, ub, ub / col_scale)

    c = np.asarray(lp["c"], dtype=np.float64)
    c_t = c * col_scale  # c^T v = (c * col_scale)^T v' -- objective value is invariant

    transformed = dict(lp)
    transformed["S"] = S_t
    transformed["b"] = b_t
    transformed["lb"] = lb_t
    transformed["ub"] = ub_t
    transformed["c"] = c_t

    if lp.get("C") is not None:
        C_t = sp.csr_matrix(lp["C"]) @ sp.diags(col_scale)
        transformed["C"] = C_t
        # d_lb/d_ub are untouched -- only the variable (column) axis was rescaled

    context = {"row_scale": row_scale, "col_scale": col_scale}
    return transformed, context


def inverse(fluxes_transformed, context):
    """Map a solution of the transformed LP back to the original variable
    space: v = col_scale * v'. Exact, not approximate."""
    if fluxes_transformed is None:
        return None
    return context["col_scale"] * np.asarray(fluxes_transformed, dtype=np.float64)
