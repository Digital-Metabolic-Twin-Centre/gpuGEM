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


# --------------------------------------------------------------------------
# Block-resolved feasibility (added for the V8 revision).
#
# WHY THIS EXISTS. ``feasibility_residual`` above measures ||Sv - b||_inf, i.e.
# the mass-balance (equality) block ONLY. The coupling block (C, d_lb, d_ub) is
# 63-65% of the constraint rows in the whole-body and personalised microbiome
# models, and was never measured on the cuOpt or Gurobi side. Meanwhile
# ``run_highs_baseline.py`` measured max violation over S AND C stacked
# together. The two numbers therefore describe different row sets and must not
# be compared; Supplementary Table S2 currently compares them.
#
# ``block_residuals`` reports every block separately so a residual can never
# again be quoted without saying which rows it covers.
# --------------------------------------------------------------------------

def _two_sided_violation(Ax, lo, hi):
    """Elementwise amount by which Ax falls outside [lo, hi]; 0 where inside."""
    below = np.where(np.isfinite(lo), lo - Ax, -np.inf)
    above = np.where(np.isfinite(hi), Ax - hi, -np.inf)
    return np.maximum(np.maximum(below, above), 0.0)


def block_residuals(lp, v, tol: float = 1e-4) -> dict:
    """Feasibility of ``v`` for ``lp``, resolved by constraint block.

    Covers every row and every variable of the LP -- the equality block, the
    coupling block and the variable box -- so the return value is a statement
    about the whole object, not a sample of it.

    Parameters
    ----------
    lp:
        LP dict as produced by ``benchmarks.models.build_lp``: keys ``S``, ``b``,
        ``lb``, ``ub``, ``c``, ``maximize``, and optionally ``C``, ``d_lb``,
        ``d_ub``.
    v:
        Primal solution in the ORIGINAL variable space (post-postsolve).
    tol:
        Violation threshold used for the ``*_rows_violated`` counts. The default
        matches the project's mass-balance acceptance gate of 1e-4.

    Returns
    -------
    dict
        ``eq_*``       -- max |Sv - b| and count of rows over ``tol``.
        ``coupling_*`` -- max two-sided violation of ``d_lb <= Cv <= d_ub``
                          and count of rows over ``tol``. ``None`` when the
                          model carries no coupling block.
        ``bound_*``    -- max violation of ``lb <= v <= ub``, and count.
        ``all_rows_max_viol`` -- max over the equality and coupling blocks
                          together (the quantity ``run_highs_baseline.py``
                          reports as ``residual_inf``).
        ``blocks_checked`` / ``blocks_absent`` -- which blocks this LP actually
                          has, so a caller cannot mistake "not present" for
                          "measured and clean".

    Raises
    ------
    ValueError
        If ``v`` is None, is not finite, or does not match the LP's column
        count. A residual computed against a truncated or padded vector is
        meaningless, so this fails loudly rather than returning a number.
    """
    S = sp.csr_matrix(lp["S"])
    n_cols = S.shape[1]

    if v is None:
        raise ValueError("no primal solution: cannot report feasibility")
    v = np.asarray(v, dtype=np.float64).ravel()
    if v.size != n_cols:
        raise ValueError(
            f"primal solution has {v.size} entries but the LP has {n_cols} "
            "columns -- refusing to report a residual for a mismatched vector"
        )
    if not np.all(np.isfinite(v)):
        raise ValueError(
            f"primal solution contains {int((~np.isfinite(v)).sum())} non-finite "
            "entries -- refusing to report a residual"
        )

    out = {"n_cols": int(n_cols), "tol": float(tol)}
    checked, absent = [], []

    # --- equality (mass-balance) block -----------------------------------
    b = np.asarray(lp["b"], dtype=np.float64).ravel()
    r_eq = np.abs(S @ v - b)
    out["n_eq_rows"] = int(S.shape[0])
    out["eq_max_abs"] = float(r_eq.max()) if r_eq.size else 0.0
    out["eq_rows_violated"] = int((r_eq > tol).sum())
    checked.append("equality")

    # --- coupling block ---------------------------------------------------
    if lp.get("C") is not None:
        C = sp.csr_matrix(lp["C"])
        dlo = np.asarray(lp["d_lb"], dtype=np.float64).ravel()
        dhi = np.asarray(lp["d_ub"], dtype=np.float64).ravel()
        viol_c = _two_sided_violation(C @ v, dlo, dhi)
        out["n_coupling_rows"] = int(C.shape[0])
        out["coupling_max_viol"] = float(viol_c.max()) if viol_c.size else 0.0
        out["coupling_rows_violated"] = int((viol_c > tol).sum())
        checked.append("coupling")
        all_max = max(out["eq_max_abs"], out["coupling_max_viol"])
    else:
        out["n_coupling_rows"] = 0
        out["coupling_max_viol"] = None
        out["coupling_rows_violated"] = None
        absent.append("coupling")
        all_max = out["eq_max_abs"]

    out["all_rows_max_viol"] = float(all_max)

    # --- variable box -----------------------------------------------------
    lb = np.asarray(lp["lb"], dtype=np.float64).ravel()
    ub = np.asarray(lp["ub"], dtype=np.float64).ravel()
    viol_b = _two_sided_violation(v, lb, ub)
    out["bound_max_viol"] = float(viol_b.max()) if viol_b.size else 0.0
    out["bound_vars_violated"] = int((viol_b > tol).sum())
    checked.append("bounds")

    out["blocks_checked"] = checked
    out["blocks_absent"] = absent
    return out


def objective_pinned_by_bounds(lp, atol: float = 0.0) -> dict:
    """Report whether the LP optimum is determined by variable bounds alone.

    On the whole-body and personalised models the objective is a single
    reaction with ``lb == ub``, so every feasible point attains the same
    objective and cross-solver objective agreement carries no information
    about numerical accuracy. This makes that property explicit and checkable
    instead of leaving it to be inferred from a table of zeros.

    Returns a dict with ``n_objective_vars``, ``pinned`` (bool), and, when the
    objective is a single pinned variable, the ``implied_objective`` that any
    feasible point must attain.
    """
    c = np.asarray(lp["c"], dtype=np.float64).ravel()
    lb = np.asarray(lp["lb"], dtype=np.float64).ravel()
    ub = np.asarray(lp["ub"], dtype=np.float64).ravel()
    idx = np.flatnonzero(c)

    out = {"n_objective_vars": int(idx.size)}
    if idx.size == 0:
        out.update(pinned=False, implied_objective=None, reason="empty objective")
        return out

    spread = ub[idx] - lb[idx]
    pinned_mask = np.abs(spread) <= atol
    out["objective_var_indices"] = [int(i) for i in idx]
    out["objective_var_lb"] = [float(x) for x in lb[idx]]
    out["objective_var_ub"] = [float(x) for x in ub[idx]]
    out["pinned"] = bool(pinned_mask.all())
    out["n_pinned_objective_vars"] = int(pinned_mask.sum())
    out["implied_objective"] = (
        float(np.dot(c[idx], lb[idx])) if pinned_mask.all() else None
    )
    out["reason"] = (
        "every objective variable has lb == ub: all feasible points are optimal"
        if pinned_mask.all() else
        "at least one objective variable is free to vary"
    )
    return out


def objective_difference(o_test, o_ref, mode: str = "relative") -> float:
    """Objective discrepancy under an EXPLICITLY named definition.

    Supplementary Table S2 reported one column as an absolute difference and
    the other as a relative difference while the caption described both as
    relative. Callers must now name the definition.

    mode='relative' -> |o_test - o_ref| / |o_ref|          (requires o_ref != 0)
    mode='absolute'  -> |o_test - o_ref|
    mode='gated'     -> |o_test - o_ref| / max(1, |o_test|, |o_ref|), the
                        convention used by ``objectives_agree`` above; equals
                        the absolute difference whenever |o| <= 1.
    """
    if o_test is None or o_ref is None:
        return float("nan")
    d = abs(float(o_test) - float(o_ref))
    if mode == "absolute":
        return d
    if mode == "relative":
        if o_ref == 0.0:
            raise ValueError("relative difference undefined for o_ref == 0; "
                             "use mode='absolute' or mode='gated'")
        return d / abs(float(o_ref))
    if mode == "gated":
        return d / max(1.0, abs(float(o_test)), abs(float(o_ref)))
    raise ValueError(f"unknown mode {mode!r}: use 'relative', 'absolute' or 'gated'")
