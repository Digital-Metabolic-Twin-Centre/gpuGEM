"""
gpuGEM backend: the biomarker-demand LP solved on the GPU.

This is the point of the application. The LP is handed to the public
``gpugem.solve`` entry point rather than to cuOpt directly, so the published
speed-up is obtained with the settings the package applies on its own.

On this model gpuGEM's size-adaptive defaults (``gpugem._defaults``) resolve
to PDLP in double precision with primal and dual tolerances of 1e-8 and
max-norm convergence checking, which is the configuration the manuscript
reports. No solver parameters are overridden here beyond the time limit.

(A note on precision, because the research notes this was ported from say
otherwise: ``pdlp_precision=1`` is cuOpt's *Double* mode, not a mixed FP32/FP64
mode. Single precision does not converge at the tolerances this model needs.
gpuGEM's defaults carry the corrected reading.)
"""

from __future__ import annotations

import numpy as np
import scipy.sparse as sp

from cugem_app.biomarkers import DemandSpec, EXCHANGE_OBJ, EXCHANGE_UB, ExchangeSpec
from cugem_app.data import WBModel

#: Time limit handed to gpuGEM, matching the published runs.
LP_TIME_LIMIT = 120.0


def build_augmented_arrays(
    wbm: WBModel, demands: list[DemandSpec], exchanges: list[ExchangeSpec]
) -> dict:
    """
    State the patient LP in the form ``gpugem.solve`` accepts.

    The Harvey model needs no reformulation: its stoichiometric rows are all
    equalities with a zero right-hand side, which is exactly ``S v = b``, and
    its coupling rows are one-sided inequalities, which become ``d_lb <= C v <=
    d_ub`` with the unused side set to infinity.

    One column is appended per [bc] biomarker, carrying coefficient -1 in that
    metabolite's row of ``S`` and zeros in ``C``. [u] biomarkers modify
    existing columns in place.

    Returns a keyword dict ready to splat into ``gpugem.solve``.
    """
    if not np.all(wbm.csense == "E"):
        unique = sorted(set(wbm.csense.tolist()))
        raise ValueError(
            "gpugem.solve expects equality stoichiometric rows (S v = b), but "
            f"this model's csense contains {unique}. Inequality rows would have "
            "to be moved into the coupling block first."
        )

    n_mets, n_coup, n_dm = wbm.n_mets, wbm.C.shape[0], len(demands)

    if n_dm:
        rows = np.array([s.met_index for s in demands], dtype=np.int64)
        cols = np.arange(n_dm, dtype=np.int64)
        dm_S = sp.csc_matrix(
            (np.full(n_dm, -1.0), (rows, cols)), shape=(n_mets, n_dm)
        )
        S = sp.hstack([wbm.S, dm_S], format="csr")
        C = sp.hstack([wbm.C, sp.csc_matrix((n_coup, n_dm))], format="csr")
        lb = np.concatenate([wbm.lb, [s.lb for s in demands]])
        ub = np.concatenate([wbm.ub, [s.ub for s in demands]])
        c = np.concatenate([wbm.c, [s.obj for s in demands]])
    else:
        S, C = wbm.S.tocsr(), wbm.C.tocsr()
        lb, ub, c = wbm.lb.copy(), wbm.ub.copy(), wbm.c.copy()

    for ex in exchanges:
        c[ex.rxn_index] = EXCHANGE_OBJ
        ub[ex.rxn_index] = EXCHANGE_UB

    d_lb = np.where(wbm.dsense == "L", -np.inf, wbm.d)
    d_ub = np.where(wbm.dsense == "G", np.inf, wbm.d)

    return dict(
        S=S, b=wbm.b, lb=lb, ub=ub, c=c,
        C=C, d_lb=d_lb, d_ub=d_ub,
        maximize=True,
    )


def solve_lp(
    wbm: WBModel,
    demands: list[DemandSpec],
    exchanges: list[ExchangeSpec],
    *,
    time_limit: float = LP_TIME_LIMIT,
    **cuopt_overrides,
):
    """
    Solve the biomarker-demand LP with gpuGEM.

    Returns the :class:`gpugem.FBAResult` unchanged, so callers can read
    ``objective``, ``wall_time_s``, ``feasibility`` and ``solver_settings``.
    """
    try:
        import gpugem
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "gpugem is not installed. From the repository root run "
            "'pip install -e .' (and ensure cuopt-cu12 is available on a "
            "CUDA 12 machine with an NVIDIA GPU)."
        ) from exc

    arrays = build_augmented_arrays(wbm, demands, exchanges)
    return gpugem.solve(**arrays, time_limit=time_limit, **cuopt_overrides)
