"""
Model loaders — convert common metabolic model formats into arrays
ready for :func:`gpugem.solve`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple, Union

import numpy as np
import scipy.sparse as sp


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
    n = len(model.reactions)

    lb = np.array([r.lower_bound for r in model.reactions], dtype=np.float64)
    ub = np.array([r.upper_bound for r in model.reactions], dtype=np.float64)
    c  = np.array([r.objective_coefficient for r in model.reactions], dtype=np.float64)
    b  = np.zeros(len(model.metabolites), dtype=np.float64)

    maximize = (model.objective.direction == "max")

    return dict(S=S, b=b, lb=lb, ub=ub, c=c, maximize=maximize)


def from_mat(
    mat_path: Union[str, Path],
    model_key: str = "modelReduced",
) -> Dict:
    """
    Load a COBRA-format ``.mat`` file (as exported by MATLAB ``saveCbModel``).

    Supports both standard COBRA models (``S``, ``b``, ``lb``, ``ub``, ``c``,
    ``csense``, ``osenseStr``) and whole-body models with coupling constraints
    (``C``, ``d``, ``dsense``, ``ctrs``/``evars``).

    Parameters
    ----------
    mat_path:
        Path to the ``.mat`` file.
    model_key:
        Top-level variable name in the ``.mat`` file.

    Returns
    -------
    dict with keys ``S, b, lb, ub, c, maximize`` and optionally
    ``C, d_lb, d_ub`` when coupling constraints are present.
    """
    import scipy.io as sio

    raw = sio.loadmat(str(mat_path), struct_as_record=False, squeeze_me=True)
    m = raw[model_key]

    def _field(name, default=None):
        try:
            v = getattr(m, name)
            return v.item() if hasattr(v, "item") else v
        except AttributeError:
            return default

    def _str_array(x):
        arr = np.asarray(x, dtype=object)
        return np.array([str(v) for v in arr.flat]).reshape(arr.shape)

    S   = sp.csc_matrix(_field("S")).astype(np.float64)
    b   = np.asarray(_field("b"), dtype=np.float64).ravel()
    lb  = np.asarray(_field("lb"), dtype=np.float64).ravel()
    ub  = np.asarray(_field("ub"), dtype=np.float64).ravel()
    c   = np.asarray(_field("c"), dtype=np.float64).ravel()
    osense = str(_field("osenseStr", "min")).strip().lower()
    maximize = (osense == "max")

    result = dict(S=S, b=b, lb=lb, ub=ub, c=c, maximize=maximize)

    # Coupling constraints (whole-body / microbiome models)
    C_raw = _field("C")
    if C_raw is not None:
        C = sp.csc_matrix(C_raw).astype(np.float64)
        d = np.asarray(_field("d"), dtype=np.float64).ravel()
        dsense_raw = _field("dsense")
        INF = 1e30

        if dsense_raw is not None:
            dsense = _str_array(dsense_raw).ravel()
            d_lb = np.where(dsense == "G", d, np.where(dsense == "E", d, -INF))
            d_ub = np.where(dsense == "L", d, np.where(dsense == "E", d,  INF))
        else:
            d_lb = d
            d_ub = d

        result.update(C=C, d_lb=d_lb, d_ub=d_ub)

    # Lifted whole-body models: evars extend the variable space
    ctrs = _field("ctrs")
    evars = _field("evars")
    if ctrs is not None and evars is not None:
        # Build extra variable bounds from evars and stack the ctrs coupling block
        evar_lb = np.asarray(_field("evarlb", np.zeros(0)), dtype=np.float64).ravel()
        evar_ub = np.asarray(_field("evarub", np.full(0, 1e30)), dtype=np.float64).ravel()
        if evar_lb.size:
            result["lb"] = np.concatenate([result["lb"], evar_lb])
            result["ub"] = np.concatenate([result["ub"], evar_ub])

    return result
