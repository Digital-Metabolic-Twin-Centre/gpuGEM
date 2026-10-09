"""
Gurobi backend: the CPU LP baseline and the minimum-norm QP.

The QP is used by *both* pipeline variants. cuOpt's barrier method cannot
solve this QP on the Harvey model: forming the normal-equations matrix
produces roughly 521 million nonzeros, which the GPU direct solver's allocator
cannot service regardless of free device memory. A GPU QP path is therefore
future work, and Gurobi remains a hard requirement for the second half of the
pipeline. See ``application/README.md``.

No licence credentials are read from this repository. ``make_env`` creates a
default Gurobi environment, which picks up whatever licence your own
installation is configured with (``GRB_LICENSE_FILE``, ``~/gurobi.lic``, or a
Web Licence Service configuration).
"""

from __future__ import annotations

import numpy as np
import scipy.sparse as sp

try:
    import gurobipy as gp
    from gurobipy import GRB
except ImportError as exc:  # pragma: no cover - exercised only without Gurobi
    raise ImportError(
        "gurobipy is required by the gpuGEM application (both solver paths use "
        "Gurobi for the minimum-norm QP). Install it with "
        "'pip install gpugem[gurobi]' or 'pip install gurobipy', and make sure "
        "a Gurobi licence is available."
    ) from exc

from cugem_app.biomarkers import DemandSpec, EXCHANGE_OBJ, EXCHANGE_UB, ExchangeSpec
from cugem_app.data import FLUX_TOL, WBModel

#: Gurobi parameters for the LP step. Dual simplex is the published baseline.
LP_METHOD = 1
LP_TIME_LIMIT = 60.0
BUILD_SCALE_FLAG = 2

#: Gurobi parameters for the minimum-norm QP step.
QP_WEIGHT = 1e-6
QP_METHOD = -1          # automatic; selects barrier for this QP
QP_SCALE_FLAG = -1
QP_BAR_CONV_TOL = 1e-4
QP_TIME_LIMIT = 120.0


def make_env(output: bool = False) -> gp.Env:
    """Create a default Gurobi environment using the caller's own licence."""
    env = gp.Env(empty=True)
    env.setParam("OutputFlag", 1 if output else 0)
    env.start()
    return env


def build_base_model(
    wbm: WBModel, env: gp.Env, *, print_level: int = 0
) -> tuple[gp.Model, gp.MVar]:
    """
    Build the whole-body LP once, for cloning per query.

    Constraints are added in bulk by sense, which is substantially faster than
    row by row at this size. No time limit is set here: the LP and the QP get
    their own budgets on the cloned model.
    """
    grb = gp.Model(env=env)
    grb.Params.OutputFlag = 1 if print_level > 0 else 0
    grb.Params.ScaleFlag = BUILD_SCALE_FLAG

    v = grb.addMVar(wbm.n_rxns, lb=wbm.lb, ub=wbm.ub, name="v")
    grb.setMObjective(
        None, wbm.c, 0.0,
        sense=GRB.MAXIMIZE if wbm.osenseStr == "max" else GRB.MINIMIZE,
    )

    for block, sense_arr, matrix, rhs, prefix in (
        ("stoich", wbm.csense, wbm.S, wbm.b, "s"),
        ("coupling", wbm.dsense, wbm.C, wbm.d, "c"),
    ):
        for char, op in (("E", "="), ("L", "<"), ("G", ">")):
            idx = np.where(sense_arr == char)[0]
            if len(idx) == 0:
                continue
            grb.addMConstr(
                matrix[idx, :].tocsr(), v, op, rhs[idx],
                name=[f"{prefix}{i}" for i in idx],
            )

    grb.update()
    return grb, v


def add_demand_reaction(grb: gp.Model, wbm: WBModel, spec: DemandSpec) -> int:
    """
    Add (or reuse) the demand reaction for one [bc] biomarker and set its
    bounds and objective coefficient. Returns the Gurobi variable index.

    Mirrors COBRA's ``addDemandReaction``: the column consumes one unit of the
    metabolite, so its stoichiometric coefficient is -1 in that metabolite row.
    """
    dm_name = f"DM_{spec.met_id}"

    existing = np.where(wbm.rxns == dm_name)[0]
    if len(existing):
        var = grb.getVars()[int(existing[0])]
    else:
        var = grb.addVar(lb=0.0, ub=1000.0, obj=0.0, name=dm_name)
        grb.update()
        constr = grb.getConstrByName(f"s{spec.met_index}")
        if constr is None:
            raise RuntimeError(
                f"Stoichiometric constraint row s{spec.met_index} not found; "
                "the base model was not built by build_base_model()."
            )
        grb.chgCoeff(constr, var, -1.0)
        grb.update()

    var.LB, var.UB, var.Obj = spec.lb, spec.ub, spec.obj
    return var.index


def apply_biomarkers(
    grb: gp.Model,
    wbm: WBModel,
    demands: list[DemandSpec],
    exchanges: list[ExchangeSpec],
    whole_indices: np.ndarray,
) -> list[int]:
    """
    Impose a patient's biomarker pattern on a cloned base model.

    Adds the [bc] demand columns, retunes the [u] exchange reactions, and
    re-pins the whole-body objective reaction (cloning does not preserve the
    bounds set during the wild-type setup).
    """
    var_indices = [add_demand_reaction(grb, wbm, spec) for spec in demands]

    for ex in exchanges:
        var = grb.getVars()[ex.rxn_index]
        var.Obj = EXCHANGE_OBJ
        var.UB = EXCHANGE_UB

    for idx in whole_indices:
        var = grb.getVars()[int(idx)]
        var.LB = 1.0
        var.UB = 1.0

    grb.update()
    return var_indices


def solve_lp(grb: gp.Model) -> tuple[int, float | None]:
    """Solve the biomarker-demand LP with dual simplex. Returns (status, f*)."""
    grb.ModelSense = GRB.MAXIMIZE
    grb.Params.Method = LP_METHOD
    grb.Params.TimeLimit = LP_TIME_LIMIT
    grb.update()
    grb.optimize()
    return grb.Status, (grb.ObjVal if grb.Status == GRB.OPTIMAL else None)


def solve_minnorm_qp(
    grb: gp.Model, wbm: WBModel, f_star: float, *, slack: float
) -> tuple[int, np.ndarray | None]:
    """
    Select the unique minimum-norm point on the LP optimal face.

    Pins the linear objective at ``f_star - slack`` and minimises
    ``0.5 * QP_WEIGHT * ||v||^2``. ``slack`` absorbs the error in ``f_star``
    and so depends on which solver produced it: see ``LP_SLACK`` in
    ``pipeline.py``.

    Returns ``(status, flux)`` with ``flux`` restricted to the model's own
    reactions, demand columns excluded, and values at or below ``FLUX_TOL``
    zeroed as in the MATLAB original.
    """
    variables = grb.getVars()
    n_v = len(variables)
    obj_vec = np.array([v.Obj for v in variables])
    v_mvar = gp.MVar.fromlist(variables)

    grb.addMConstr(
        sp.csr_matrix(obj_vec.reshape(1, -1)), v_mvar, ">",
        np.array([f_star - slack]),
    )
    grb.setMObjective(
        QP_WEIGHT * sp.eye(n_v, format="csr"), np.zeros(n_v), 0.0,
        sense=GRB.MINIMIZE,
    )
    grb.Params.Method = QP_METHOD
    grb.Params.ScaleFlag = QP_SCALE_FLAG
    grb.Params.BarConvTol = QP_BAR_CONV_TOL
    grb.Params.TimeLimit = QP_TIME_LIMIT
    grb.update()
    grb.optimize()

    if grb.Status not in (GRB.OPTIMAL, GRB.SUBOPTIMAL):
        return grb.Status, None

    flux = np.array([v.X for v in grb.getVars()[: wbm.n_rxns]])
    flux[np.abs(flux) <= FLUX_TOL] = 0.0
    return grb.Status, flux
