"""Faithful Python translation of COBRA Toolbox's ``reformulate.m``
(``cobratoolbox/src/base/solvers/rescale/reformulate.m``), which implements the
model-lifting method described in Sun, Fleming, Saunders & Thiele's multi-scale
FBA paper.

Badly-scaled mass-balance rows (``lift_mass_balance``) and, separately,
badly-scaled two-nonzero-opposite-sign coupling rows (``lift_coupling``) are
decomposed into chains of auxiliary reactions/variables whose coefficients are
bounded by ``big``. Original variables are never reordered, rescaled, or
removed -- only appended after -- so mapping a lifted solution back
(``map_back``) is a literal prefix slice, not an inverse transform.

This is a *different* algorithm from :mod:`gpugem.scaling`'s existing
``decompose_stoichiometry``/``scale_model`` (per-entry independent chains,
handles both large and small coefficients, no coupling-block lifting, bounded
auxiliary variables) -- the two modules are intentionally separate and neither
is a drop-in replacement for the other (see specs/013-cobra-model-lifting/
research.md R3). This module never imports from or modifies ``gpugem.scaling``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import scipy.sparse as sp

_INF = 1e30


@dataclass(frozen=True)
class LiftingMapping:
    """Metadata needed to map a lifted model's solution back to the original,
    and to report how much lifting actually corrected the model's scale."""

    n_original_vars: int
    n_original_stoich_rows: int
    n_original_coupling_rows: Optional[int]
    big: float
    mass_balance_lifted_rows: list = field(default_factory=list)
    coupling_lifted_rows: list = field(default_factory=list)
    n_aux_vars: int = 0
    n_aux_rows: int = 0


def _row_step_size(magnitudes: np.ndarray, dum: np.ndarray) -> float:
    """Translate reformulate.m line 99: ``stp = mode(nthroot(lrgnums, dum+1))``.

    MATLAB's ``mode()`` breaks ties toward the smallest value, and a vector of
    (in practice, for continuous stoichiometric coefficients) all-distinct
    floats has every element tied at frequency 1 -- so ``mode()`` of such a
    vector is exactly ``min()``. Using Python's ``statistics.mode()`` here
    would be wrong: it returns the *first* most-common element for all-unique
    data, not the minimum, and would silently diverge from reformulate.m's
    actual behavior (specs/013-cobra-model-lifting/research.md R1 point 3).
    """
    roots = magnitudes ** (1.0 / (dum + 1))
    return float(np.min(roots))


def lift_mass_balance(S, b, big: float = 1000.0):
    """Port of reformulate.m lines 63-141 (the ``S`` / mass-balance block).

    Parameters
    ----------
    S:
        Stoichiometric matrix (equality rows only -- gpuGEM's ``S`` is always
        the homogeneous mass-balance block by construction, matching
        reformulate.m's own ``storow = csense=='E' & b==0`` precondition).
    b:
        Right-hand side; rows with ``b != 0`` are left untouched, matching
        reformulate.m's own precondition (they are not candidates for
        lifting, not an error case).
    big:
        Magnitude threshold (reformulate.m's ``BIG``).

    Returns
    -------
    ``(S_lifted, b_lifted, mapping)`` -- ``mapping.n_aux_vars``/``n_aux_rows``
    only reflect this call; ``lift_coupling`` extends the same mapping's
    counts when composed with this one (see ``gpugem.solver``'s integration).
    """
    S = sp.csr_matrix(S).astype(np.float64)
    b = np.asarray(b, dtype=np.float64)
    n_mets, n_rxns = S.shape
    logbig = np.log(big)  # reformulate.m line 65

    new_rows: list = []
    new_cols: list = []
    new_data: list = []
    zeroed: set = set()
    lifted_rows: list = []

    next_col = n_rxns
    next_row = n_mets

    for i in range(n_mets):
        if b[i] != 0:
            continue  # reformulate.m line 67: only homogeneous rows are candidates
        start, end = S.indptr[i], S.indptr[i + 1]
        row_cols = S.indices[start:end]
        row_vals = S.data[start:end]
        large_mask = np.abs(row_vals) > big
        if not large_mask.any():
            continue

        lrgind_cols = row_cols[large_mask]
        lrgvals = row_vals[large_mask]
        lrgnums = np.abs(lrgvals)
        # reformulate.m line 94: dum = max(floor(log(lrgnums)/logbig), 1)
        dum = np.maximum(np.floor(np.log(lrgnums) / logbig), 1).astype(np.int64)
        stp = _row_step_size(lrgnums, dum)
        maxdum = int(dum.max())

        aux_cols = list(range(next_col, next_col + maxdum))
        aux_rows = list(range(next_row, next_row + maxdum))
        next_col += maxdum
        next_row += maxdum

        # reformulate.m line 106: original row -> first chain link, coeff -stp
        new_rows.append(i)
        new_cols.append(aux_cols[0])
        new_data.append(-stp)

        # reformulate.m lines 103-105 (dumblk): bidiagonal chain
        # aux_row[k]: +1 * aux_col[k]  ( - stp * aux_col[k+1]  if k < maxdum-1 )
        for k in range(maxdum):
            new_rows.append(aux_rows[k])
            new_cols.append(aux_cols[k])
            new_data.append(1.0)
            if k < maxdum - 1:
                new_rows.append(aux_rows[k])
                new_cols.append(aux_cols[k + 1])
                new_data.append(-stp)

        # reformulate.m lines 107-110: tap each dum-level back to its
        # original column(s), sharing the one chain built above
        for k2 in range(int(dum.min()), maxdum + 1):
            level_mask = dum == k2
            if not level_mask.any():
                continue
            for j, v in zip(lrgind_cols[level_mask], lrgvals[level_mask]):
                new_rows.append(aux_rows[k2 - 1])
                new_cols.append(int(j))
                new_data.append(v / (stp ** k2))

        for j in lrgind_cols:
            zeroed.add((i, int(j)))
        lifted_rows.append(i)

    # reformulate.m line 111 (delnan): drop the original large entries
    coo = S.tocoo()
    keep = np.array(
        [(r, c) not in zeroed for r, c in zip(coo.row, coo.col)], dtype=bool
    )
    rows = np.concatenate([coo.row[keep], np.asarray(new_rows, dtype=np.int64)])
    cols = np.concatenate([coo.col[keep], np.asarray(new_cols, dtype=np.int64)])
    data = np.concatenate([coo.data[keep], np.asarray(new_data, dtype=np.float64)])

    n_aux_vars = next_col - n_rxns
    n_aux_rows = next_row - n_mets
    S_lifted = sp.csr_matrix(
        (data, (rows, cols)), shape=(n_mets + n_aux_rows, n_rxns + n_aux_vars)
    )
    b_lifted = np.concatenate([b, np.zeros(n_aux_rows)])

    mapping = LiftingMapping(
        n_original_vars=n_rxns,
        n_original_stoich_rows=n_mets,
        n_original_coupling_rows=None,
        big=float(big),
        mass_balance_lifted_rows=lifted_rows,
        coupling_lifted_rows=[],
        n_aux_vars=n_aux_vars,
        n_aux_rows=n_aux_rows,
    )
    return S_lifted, b_lifted, mapping


def lift_coupling(C, d_lb, d_ub, big: float, mapping: LiftingMapping):
    """Port of reformulate.m lines 143-217 (the ``C`` / coupling block).

    Targets rows with exactly two nonzero, opposite-sign entries and a
    homogeneous bound (``d_lb==0`` or ``d_ub==0``) -- reformulate.m's own
    ``cuprow`` selection (lines 145-150). Non-matching rows pass through
    unchanged. Only the single largest-magnitude entry per targeted row is
    lifted (reformulate.m's own behavior, lines 153-157, 195) -- if a row has
    two entries both exceeding ``big``, the smaller one is left as-is; this
    is reformulate.m's documented behavior, not a gap introduced here.

    ``mapping`` must be the ``LiftingMapping`` already returned by
    ``lift_mass_balance`` for the same model (so new columns are appended
    after any mass-balance auxiliary columns, and both blocks' counts are
    combined into one mapping).
    """
    C = sp.csr_matrix(C).astype(np.float64)
    d_lb = np.asarray(d_lb, dtype=np.float64)
    d_ub = np.asarray(d_ub, dtype=np.float64)
    n_rows, n_cols_total = C.shape
    logbig = np.log(big)  # reformulate.m line 65 (shared constant, recomputed here)

    new_rows: list = []
    new_cols: list = []
    new_data: list = []
    zeroed: set = set()
    lifted_rows: list = []
    new_row_d_lb: list = []
    new_row_d_ub: list = []

    next_col = n_cols_total
    next_row = n_rows

    for i in range(n_rows):
        start, end = C.indptr[i], C.indptr[i + 1]
        row_cols = C.indices[start:end]
        row_vals = C.data[start:end]
        nz = row_vals != 0
        row_cols = row_cols[nz]
        row_vals = row_vals[nz]
        # reformulate.m lines 145-150 (cuprow): candidate rows are exactly
        # two nonzero, opposite-sign entries with a homogeneous bound
        if len(row_vals) != 2:
            continue
        if np.sign(row_vals[0]) == np.sign(row_vals[1]):
            continue
        homogeneous = (d_lb[i] == 0) or (d_ub[i] == 0)
        if not homogeneous:
            continue

        # reformulate.m lines 153-157: only the single largest-magnitude
        # entry per row is lifted, even if a second entry also exceeds big
        maxidx = int(np.argmax(np.abs(row_vals)))
        qty = float(np.abs(row_vals[maxidx]))
        if qty <= big:
            continue
        j = int(row_cols[maxidx])
        sgn = 1.0 if row_vals[maxidx] >= 0 else -1.0

        # reformulate.m line 182 (dum) and line 186 (stp) -- a scalar per
        # row, no row-sharing/mode() needed since exactly one value is lifted
        dum = max(int(np.floor(np.log(qty) / logbig)), 1)
        stp = qty ** (1.0 / (dum + 1))

        aux_cols = list(range(next_col, next_col + dum))
        aux_rows = list(range(next_row, next_row + dum))
        next_col += dum
        next_row += dum

        # reformulate.m line 193: C(i, n+1) = sgn*stp
        new_rows.append(i)
        new_cols.append(aux_cols[0])
        new_data.append(sgn * stp)

        # reformulate.m lines 189-190 (dumblk): sgn*[-1, +stp] bidiagonal chain
        for k in range(dum):
            new_rows.append(aux_rows[k])
            new_cols.append(aux_cols[k])
            new_data.append(sgn * -1.0)
            if k < dum - 1:
                new_rows.append(aux_rows[k])
                new_cols.append(aux_cols[k + 1])
                new_data.append(sgn * stp)

        # reformulate.m line 194: C(m+dum, j) = sgn*qty/stp^dum (last level only
        # -- a single value, not a shared multi-tap loop, since exactly one
        # entry is lifted per targeted row)
        new_rows.append(aux_rows[dum - 1])
        new_cols.append(j)
        new_data.append(sgn * qty / (stp ** dum))

        zeroed.add((i, j))
        lifted_rows.append(i)
        for _ in range(dum):
            new_row_d_lb.append(0.0 if d_lb[i] == 0 else -_INF)
            new_row_d_ub.append(0.0 if d_ub[i] == 0 else _INF)

    coo = C.tocoo()
    keep = np.array(
        [(r, c) not in zeroed for r, c in zip(coo.row, coo.col)], dtype=bool
    )
    rows = np.concatenate([coo.row[keep], np.asarray(new_rows, dtype=np.int64)])
    cols = np.concatenate([coo.col[keep], np.asarray(new_cols, dtype=np.int64)])
    data = np.concatenate([coo.data[keep], np.asarray(new_data, dtype=np.float64)])

    n_aux_vars = next_col - n_cols_total
    n_aux_rows = next_row - n_rows
    n_cols_final = mapping.n_original_vars + mapping.n_aux_vars + n_aux_vars
    C_lifted = sp.csr_matrix(
        (data, (rows, cols)), shape=(n_rows + n_aux_rows, n_cols_final)
    )
    d_lb_lifted = np.concatenate([d_lb, np.asarray(new_row_d_lb, dtype=np.float64)])
    d_ub_lifted = np.concatenate([d_ub, np.asarray(new_row_d_ub, dtype=np.float64)])

    combined = LiftingMapping(
        n_original_vars=mapping.n_original_vars,
        n_original_stoich_rows=mapping.n_original_stoich_rows,
        n_original_coupling_rows=n_rows,
        big=mapping.big,
        mass_balance_lifted_rows=mapping.mass_balance_lifted_rows,
        coupling_lifted_rows=lifted_rows,
        n_aux_vars=mapping.n_aux_vars + n_aux_vars,
        n_aux_rows=mapping.n_aux_rows + n_aux_rows,
    )
    return C_lifted, d_lb_lifted, d_ub_lifted, combined


def map_back(fluxes_lifted, mapping: LiftingMapping) -> np.ndarray:
    """Map a lifted model's solution back to the original variable space.

    A literal prefix slice (specs/013-cobra-model-lifting/research.md R5):
    reformulate.m never reorders, rescales, or removes original variables, so
    no inverse arithmetic is needed -- unlike a scaling-based transform.
    """
    x = np.asarray(fluxes_lifted, dtype=np.float64)
    if x.shape[0] < mapping.n_original_vars:
        raise ValueError(
            "fluxes_lifted is shorter than the original variable count "
            "recorded in the mapping"
        )
    return x[: mapping.n_original_vars].copy()
