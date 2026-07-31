"""Signed per-row constraint-violation vectors, binned into shared log-scale magnitude
histograms -- the data behind the population-pyramid-style violation-distribution figures.

Reuses gpugem/solver.py's own range-violation definition (con_lb/con_ub either encoding an
equality row when con_lb == con_ub, or a true coupling range otherwise), signed so a caller can
tell which side of the allowed range a row falls on.
"""
from __future__ import annotations

import numpy as np
import scipy.sparse as sp

# Shared across every model and both figures so the same y-position always means the same
# magnitude. 24 bins, two per decade, 1e-9 (near machine-precision noise) to 1e3 (well above the
# worst observed violation, ~156.4 on S85).
MAGNITUDE_BIN_EDGES = np.logspace(-9, 3, 25)


def signed_row_violations(A, row_lb, row_ub, v):
    """Full signed violation vector for one row block.

    Negative: row falls short of its required balance/range ("category A" / shortfall).
    Positive: row exceeds its required balance/range ("category B" / excess).
    Zero: row is satisfied. For equality rows (row_lb == row_ub == b), this reduces to
    the signed residual A @ v - b.
    """
    Av = sp.csr_matrix(A) @ np.asarray(v, dtype=np.float64)
    row_lb = np.asarray(row_lb, dtype=np.float64)
    row_ub = np.asarray(row_ub, dtype=np.float64)
    return -np.maximum(row_lb - Av, 0.0) + np.maximum(Av - row_ub, 0.0)


def histogram(violations, edges=MAGNITUDE_BIN_EDGES):
    """Bin a signed violation vector into a ViolationHistogram dict (data-model.md).

    Rows at exactly zero (or below the smallest bin edge) are counted in n_satisfied rather
    than the binned counts, so a model with no violations still yields a valid histogram
    instead of corrupting the log-scale bins with a zero-magnitude entry.
    """
    violations = np.asarray(violations, dtype=np.float64)
    edges = np.asarray(edges, dtype=np.float64)
    floor = edges[0]

    magnitude = np.abs(violations)
    shortfall_mag = magnitude[violations < 0]
    excess_mag = magnitude[violations > 0]

    shortfall_counts, _ = np.histogram(shortfall_mag[shortfall_mag >= floor], bins=edges)
    excess_counts, _ = np.histogram(excess_mag[excess_mag >= floor], bins=edges)

    n_satisfied = int(violations.size - (shortfall_mag >= floor).sum() - (excess_mag >= floor).sum())

    return {
        "bin_edges": edges.tolist(),
        "shortfall_counts": shortfall_counts.astype(int).tolist(),
        "excess_counts": excess_counts.astype(int).tolist(),
        "n_rows": int(violations.size),
        "n_satisfied": n_satisfied,
    }
