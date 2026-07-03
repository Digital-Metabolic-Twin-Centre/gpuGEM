"""Stoichiometric coefficient decomposition utilities.

This module rewrites very large or very small stoichiometric coefficients into
short chains of auxiliary metabolites and reactions. The original reaction
variables are kept in place, so a scaled solution can be mapped back by taking
the first ``n_original`` fluxes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

import numpy as np
import scipy.sparse as sp


@dataclass(frozen=True)
class CoefficientScalingMapping:
    """Metadata needed to map a decomposed model solution back to the original."""

    n_original_vars: int
    n_original_mets: int
    aux_var_indices: np.ndarray
    aux_met_indices: np.ndarray
    split_entries: list[dict[str, Any]] = field(default_factory=list)
    min_abs: float = 0.1
    max_abs: float = 100.0


def _factor_abs(value: float, min_abs: float, max_abs: float) -> list[float]:
    """Return positive factors in [min_abs, max_abs] whose product is value."""
    if min_abs <= value <= max_abs:
        return [value]

    factors: list[float] = []
    remaining = float(value)

    if remaining > max_abs:
        while remaining > max_abs:
            factors.append(max_abs)
            remaining /= max_abs
        factors.append(remaining)
    else:
        while remaining < min_abs:
            factors.append(min_abs)
            remaining /= min_abs
        factors.append(remaining)

    return factors


def decompose_stoichiometry(
    S: sp.spmatrix,
    *,
    min_abs: float = 0.1,
    max_abs: float = 100.0,
    ignore_zeros: bool = True,
) -> tuple[sp.csr_matrix, CoefficientScalingMapping]:
    """
    Split coefficients outside ``[min_abs, max_abs]`` into auxiliary chains.

    The transformation is exact for steady-state FBA rows. For one original
    entry ``a`` at metabolite row ``i`` and reaction column ``j``, the entry is
    replaced by a chain that preserves the net relationship between the
    original reaction flux ``v_j`` and the original metabolite balance.

    Large example, ``a = 10000`` and factors ``[100, 100]``::

        original row i:      + aux_1
        aux row 1:           - aux_1 + 100 aux_2
        aux row 2:           - aux_2 + 100 v_j

    Small example, ``a = 1e-6`` and factors ``[0.1, ..., 0.1]``::

        original row i:      + aux_1
        aux row 1:           - aux_1 + 0.1 aux_2
        ...
        last aux row:        - aux_k + 0.1 v_j

    Parameters
    ----------
    S:
        Stoichiometric matrix with metabolites as rows and reactions as columns.
    min_abs, max_abs:
        Desired coefficient magnitude range for non-unit split factors.
    ignore_zeros:
        If ``True``, zero entries are ignored. Sparse matrices normally do not
        store zeros, but this protects against explicitly stored zeros.

    Returns
    -------
    ``(S_scaled, mapping)``.
    """
    if min_abs <= 0:
        raise ValueError("min_abs must be positive")
    if max_abs <= 1:
        raise ValueError("max_abs must be greater than 1")
    if min_abs >= 1:
        raise ValueError("min_abs must be less than 1")
    if min_abs >= max_abs:
        raise ValueError("min_abs must be smaller than max_abs")

    coo = sp.coo_matrix(S, dtype=np.float64)
    n_mets, n_rxns = coo.shape

    rows: list[int] = []
    cols: list[int] = []
    data: list[float] = []
    aux_vars: list[int] = []
    aux_mets: list[int] = []
    split_entries: list[dict[str, Any]] = []

    next_row = n_mets
    next_col = n_rxns

    for row, col, value in zip(coo.row, coo.col, coo.data):
        value = float(value)
        abs_value = abs(value)
        if ignore_zeros and abs_value == 0:
            continue

        if min_abs <= abs_value <= max_abs:
            rows.append(int(row))
            cols.append(int(col))
            data.append(value)
            continue

        sign = 1.0 if value >= 0 else -1.0
        factors = _factor_abs(abs_value, min_abs, max_abs)
        k = len(factors)
        chain_cols = list(range(next_col, next_col + k))
        chain_rows = list(range(next_row, next_row + k))
        next_col += k
        next_row += k

        aux_vars.extend(chain_cols)
        aux_mets.extend(chain_rows)

        # Original metabolite receives the first auxiliary reaction.
        rows.append(int(row))
        cols.append(chain_cols[0])
        data.append(sign)

        # Auxiliary steady-state rows enforce the scale chain.
        for idx in range(k):
            aux_row = chain_rows[idx]
            rows.append(aux_row)
            cols.append(chain_cols[idx])
            data.append(-1.0)

            source_col = int(col) if idx == k - 1 else chain_cols[idx + 1]
            rows.append(aux_row)
            cols.append(source_col)
            data.append(factors[idx])

        split_entries.append(
            {
                "row": int(row),
                "col": int(col),
                "value": value,
                "factors": factors,
                "aux_rows": chain_rows,
                "aux_cols": chain_cols,
            }
        )

    S_scaled = sp.coo_matrix((data, (rows, cols)), shape=(next_row, next_col)).tocsr()
    mapping = CoefficientScalingMapping(
        n_original_vars=n_rxns,
        n_original_mets=n_mets,
        aux_var_indices=np.asarray(aux_vars, dtype=np.int64),
        aux_met_indices=np.asarray(aux_mets, dtype=np.int64),
        split_entries=split_entries,
        min_abs=float(min_abs),
        max_abs=float(max_abs),
    )
    return S_scaled, mapping


def scale_model(
    model: Mapping[str, Any],
    *,
    min_abs: float = 0.1,
    max_abs: float = 100.0,
) -> tuple[dict[str, Any], CoefficientScalingMapping]:
    """
    Return a decomposed copy of a gpuGEM model dictionary and its mapping.

    ``model`` should follow the dictionary format returned by
    :mod:`gpugem.loaders`, with keys ``S, b, lb, ub, c`` and optional
    ``C, d_lb, d_ub``. Coupling constraints are extended with zero columns for
    the auxiliary reactions.
    """
    S_scaled, mapping = decompose_stoichiometry(
        model["S"], min_abs=min_abs, max_abs=max_abs
    )
    n_aux = len(mapping.aux_var_indices)
    n_aux_mets = len(mapping.aux_met_indices)

    scaled = dict(model)
    scaled["S"] = S_scaled
    scaled["b"] = np.concatenate(
        [np.asarray(model["b"], dtype=np.float64), np.zeros(n_aux_mets)]
    )
    # Auxiliary fluxes are algebraically coupled to the original reaction flux.
    # They must be effectively free so reversible original reactions remain
    # reversible. Use finite solver-friendly infinity, matching gpuGEM loaders.
    inf = 1e30
    scaled["lb"] = np.concatenate(
        [np.asarray(model["lb"], dtype=np.float64), np.full(n_aux, -inf)]
    )
    scaled["ub"] = np.concatenate(
        [np.asarray(model["ub"], dtype=np.float64), np.full(n_aux, inf)]
    )
    scaled["c"] = np.concatenate(
        [np.asarray(model["c"], dtype=np.float64), np.zeros(n_aux)]
    )

    if model.get("C") is not None:
        C = sp.csr_matrix(model["C"], dtype=np.float64)
        scaled["C"] = sp.hstack(
            [C, sp.csr_matrix((C.shape[0], n_aux), dtype=np.float64)],
            format="csr",
        )

    return scaled, mapping


def remap_fluxes(
    scaled_fluxes: np.ndarray,
    mapping: CoefficientScalingMapping,
) -> np.ndarray:
    """Map a scaled-model flux vector back to the original reaction variables."""
    x = np.asarray(scaled_fluxes, dtype=np.float64)
    if x.shape[0] < mapping.n_original_vars:
        raise ValueError(
            "scaled_fluxes is shorter than the original variable count recorded "
            "in the mapping"
        )
    return x[: mapping.n_original_vars].copy()
