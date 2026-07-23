"""
Model loaders — convert common metabolic model formats into arrays
ready for :func:`gpugem.solve`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Union

import numpy as np
import scipy.sparse as sp

_INF = 1e30


def from_cobra(model) -> Dict:
    """
    Extract LP arrays from a COBRApy ``Model`` object.

    Parameters
    ----------
    model:
        A ``cobra.Model`` instance.

    Returns
    -------
    dict with keys ``S, b, lb, ub, c, maximize``.
    Pass as ``gpugem.solve(**gpugem.loaders.from_cobra(model))``.
    """
    import cobra  # noqa: F401 — checked at call time

    S = sp.csr_matrix(cobra.util.create_stoichiometric_matrix(model), dtype=np.float64)

    lb = np.array([r.lower_bound for r in model.reactions], dtype=np.float64)
    ub = np.array([r.upper_bound for r in model.reactions], dtype=np.float64)
    c = np.array([r.objective_coefficient for r in model.reactions], dtype=np.float64)
    b = np.zeros(len(model.metabolites), dtype=np.float64)

    maximize = (model.objective.direction == "max")

    return dict(S=S, b=b, lb=lb, ub=ub, c=c, maximize=maximize)


def _str_array(x) -> np.ndarray:
    arr = np.asarray(x, dtype=object)
    return np.array([str(v) for v in arr.flat]).reshape(arr.shape)


def from_mat(
    mat_path: Union[str, Path],
    model_key: str = "modelReduced",
) -> Dict:
    """
    Load a COBRA-format ``.mat`` file (as exported by MATLAB ``saveCbModel``).

    Handles three layouts transparently:

    * **Standard COBRA models** — ``S, b, lb, ub, c, csense, osenseStr``.
    * **Whole-body models with coupling constraints** — additional
      ``C, d, dsense, ctrs`` rows.
    * **Lifted whole-body / microbiome models** — additional ``evars`` free
      variables with coefficient blocks ``E`` (in the stoichiometric rows) and
      ``D`` (in the coupling rows), plus ``evarlb, evarub, evarc``. The full
      system solved is::

          min/max  c^T v + evarc^T w
          s.t.     [S | E] [v; w]  {csense}  b
                   [C | D] [v; w]  {dsense}  d
                   lb <= v <= ub,  evarlb <= w <= evarub

    Fields may be stored either nested inside a single struct named
    ``model_key`` (e.g. Harvey's ``modelReduced``) or as flat top-level keys
    (e.g. lifted microbiome models); both are detected automatically.

    Metabolite rows whose ``csense`` is not ``'E'`` (equality) are moved into
    the ranged-constraint block alongside the coupling rows, so the returned
    ``S``/``b`` always represent strict equalities as :func:`gpugem.solve`
    expects.

    Parameters
    ----------
    mat_path:
        Path to the ``.mat`` file.
    model_key:
        Top-level variable name of the model struct, if the file uses the
        nested layout. Ignored for the flat layout.

    Returns
    -------
    dict with keys ``S, b, lb, ub, c, maximize`` and, when coupling and/or
    inequality rows are present, ``C, d_lb, d_ub``.
    """
    import scipy.io as sio

    raw = sio.loadmat(str(mat_path), struct_as_record=False, squeeze_me=True)

    # --- resolve nested-struct vs flat-top-level layout ---
    struct = raw.get(model_key, None)
    if struct is not None and hasattr(struct, "_fieldnames"):
        fields = set(struct._fieldnames)

        def get(name, default=None):
            return getattr(struct, name) if name in fields else default
    else:
        def get(name, default=None):
            v = raw.get(name, default)
            return v if v is not None else default

    def vec(name, default=None):
        v = get(name, None)
        if v is None:
            return default
        return np.asarray(v, dtype=np.float64).ravel()

    # --- core stoichiometry ---
    S = sp.csc_matrix(get("S")).astype(np.float64)
    b = vec("b", np.zeros(S.shape[0]))
    lb = vec("lb")
    ub = vec("ub")
    c = vec("c")
    osense = str(get("osenseStr", "min")).strip().lower()
    maximize = (osense == "max")

    csense_raw = get("csense", None)
    csense = (_str_array(csense_raw).ravel()
              if csense_raw is not None else np.full(S.shape[0], "E"))

    # --- coupling block (whole-body / microbiome) ---
    C_raw = get("C", None)
    C = sp.csc_matrix(C_raw).astype(np.float64) if C_raw is not None else None
    if C is not None:
        d = vec("d", np.zeros(C.shape[0]))
        dsense_raw = get("dsense", None)
        dsense = (_str_array(dsense_raw).ravel()
                  if dsense_raw is not None else np.full(C.shape[0], "E"))

    # --- lifted models: evars extend the variable (column) space ---
    evars = get("evars", None)
    E_raw = get("E", None)
    if evars is not None and E_raw is not None:
        E = sp.csc_matrix(E_raw).astype(np.float64)
        evarlb = vec("evarlb", np.zeros(E.shape[1]))
        evarub = vec("evarub", np.full(E.shape[1], _INF))
        evarc = vec("evarc", np.zeros(E.shape[1]))

        S = sp.hstack([S, E], format="csc")
        lb = np.concatenate([lb, evarlb])
        ub = np.concatenate([ub, evarub])
        c = np.concatenate([c, evarc])

        D_raw = get("D", None)
        if C is not None and D_raw is not None:
            D = sp.csc_matrix(D_raw).astype(np.float64)
            C = sp.hstack([C, D], format="csc")

    # --- split metabolite rows into equalities (S) and inequalities (ranged) ---
    m_lb = np.where(csense == "G", b, np.where(csense == "E", b, -_INF))
    m_ub = np.where(csense == "L", b, np.where(csense == "E", b, _INF))
    eq = (csense == "E")

    S_eq = sp.csr_matrix(S[eq])
    b_eq = b[eq]

    ranged_mats, ranged_lb, ranged_ub = [], [], []
    if (~eq).any():
        ranged_mats.append(sp.csr_matrix(S[~eq]))
        ranged_lb.append(m_lb[~eq])
        ranged_ub.append(m_ub[~eq])
    if C is not None:
        d_lb = np.where(dsense == "G", d, np.where(dsense == "E", d, -_INF))
        d_ub = np.where(dsense == "L", d, np.where(dsense == "E", d, _INF))
        ranged_mats.append(sp.csr_matrix(C))
        ranged_lb.append(d_lb)
        ranged_ub.append(d_ub)

    result = dict(S=S_eq, b=b_eq, lb=lb, ub=ub, c=c, maximize=maximize)
    if ranged_mats:
        result["C"] = sp.vstack(ranged_mats, format="csr")
        result["d_lb"] = np.concatenate(ranged_lb)
        result["d_ub"] = np.concatenate(ranged_ub)

    return result
