"""Tests for block-resolved feasibility reporting (benchmarks/residual.py).

These cover the three things the V8 revision needs to be able to state:
  1. the coupling block is measured, not silently skipped;
  2. a residual is never reported against a mismatched or non-finite vector;
  3. an objective pinned by its own bounds is identified as such.
"""

import os
import sys

import numpy as np
import pytest
import scipy.sparse as sp

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "benchmarks"))

from residual import (  # noqa: E402
    block_residuals,
    feasibility_residual,
    objective_difference,
    objective_pinned_by_bounds,
)


@pytest.fixture
def coupled_lp():
    """5 reactions, 3 mass-balance rows, 2 coupling rows, objective pinned.

    v4 is fixed at 2.0 by its own bounds, so every feasible point is optimal --
    the same structure as Whole_body_objective_rxn in the whole-body models.

    The equality block has a one-dimensional nullspace direction (v3 up, v5
    down) that ONLY the coupling block restricts. That is what makes an
    S-only residual blind: points far along that direction satisfy Sv = b
    exactly while breaking the coupling rows.
    """
    S = sp.csr_matrix(np.array([
        [1., -1., 0., 0., 0.],      # v1 - v2 = 0
        [0., 1., -1., 0., 0.],      # v2 - v3 = 0
        [0., 0., 1., -1., 1.],      # v3 + v5 - v4 = 0
    ]))
    C = sp.csr_matrix(np.array([
        [1., 0., 0., -1., 0.],      # v1 - v4 in [-1, 1]
        [0., 1., 0., 0., 0.],       # v2 <= 5
    ]))
    return dict(
        S=S, b=np.zeros(3),
        C=C, d_lb=np.array([-1.0, -np.inf]), d_ub=np.array([1.0, 5.0]),
        lb=np.array([0., 0., 0., 2.0, -10.]),
        ub=np.array([10., 10., 10., 2.0, 10.]),
        c=np.array([0., 0., 0., 1., 0.]),
        maximize=True,
    )


@pytest.fixture
def uncoupled_lp(coupled_lp):
    lp = dict(coupled_lp)
    for k in ("C", "d_lb", "d_ub"):
        lp.pop(k)
    lp["lb"] = np.array([0., 0., 0., 0., -10.])
    lp["ub"] = np.array([10., 10., 10., 10., 10.])
    return lp


# --- the coupling block is actually measured -----------------------------

def test_coupling_block_is_measured(coupled_lp):
    v = np.array([2., 2., 2., 2., 0.])      # feasible everywhere
    out = block_residuals(coupled_lp, v)
    assert out["n_coupling_rows"] == 2
    assert "coupling" in out["blocks_checked"]
    assert out["coupling_max_viol"] == pytest.approx(0.0)
    assert out["coupling_rows_violated"] == 0


def test_coupling_violation_is_detected_when_equalities_are_clean(coupled_lp):
    """The case the old S-only residual could not see.

    v = (8, 8, 8, 2, -6) satisfies Sv = b exactly but breaks BOTH coupling
    rows, so an S-only residual reports 0 while the model is infeasible.
    """
    v = np.array([8., 8., 8., 2., -6.])
    assert feasibility_residual(coupled_lp["S"], coupled_lp["b"], v) == pytest.approx(0.0)

    out = block_residuals(coupled_lp, v)
    assert out["eq_max_abs"] == pytest.approx(0.0)
    assert out["eq_rows_violated"] == 0
    assert out["coupling_max_viol"] == pytest.approx(5.0)   # v1 - v4 = 6, ub 1
    assert out["coupling_rows_violated"] == 2
    assert out["all_rows_max_viol"] == pytest.approx(5.0)


def test_absent_coupling_block_is_reported_not_zeroed(uncoupled_lp):
    out = block_residuals(uncoupled_lp, np.array([1., 1., 1., 1., 0.]))
    assert out["coupling_max_viol"] is None
    assert out["coupling_rows_violated"] is None
    assert out["blocks_absent"] == ["coupling"]


def test_bound_violation_is_measured(coupled_lp):
    v = np.array([2., 2., 2., 7.0, 0.])     # v4 outside [2, 2]
    out = block_residuals(coupled_lp, v)
    assert out["bound_max_viol"] == pytest.approx(5.0)
    assert out["bound_vars_violated"] == 1


def test_matches_legacy_residual_on_equality_block(coupled_lp):
    v = np.array([1., 3., 2., 2., 0.])
    out = block_residuals(coupled_lp, v)
    legacy = feasibility_residual(coupled_lp["S"], coupled_lp["b"], v)
    assert out["eq_max_abs"] == pytest.approx(legacy)


# --- the post-condition can fail ----------------------------------------

def test_rejects_wrong_length_vector(coupled_lp):
    with pytest.raises(ValueError, match="columns"):
        block_residuals(coupled_lp, np.zeros(3))


def test_rejects_non_finite_vector(coupled_lp):
    v = np.array([1., np.nan, 1., 2., 0.])
    with pytest.raises(ValueError, match="non-finite"):
        block_residuals(coupled_lp, v)


def test_rejects_missing_solution(coupled_lp):
    with pytest.raises(ValueError, match="no primal solution"):
        block_residuals(coupled_lp, None)


# --- objective pinning ---------------------------------------------------

def test_pinned_objective_is_identified(coupled_lp):
    out = objective_pinned_by_bounds(coupled_lp)
    assert out["pinned"] is True
    assert out["n_objective_vars"] == 1
    assert out["implied_objective"] == pytest.approx(2.0)
    assert "all feasible points are optimal" in out["reason"]


def test_free_objective_is_not_flagged_as_pinned(uncoupled_lp):
    out = objective_pinned_by_bounds(uncoupled_lp)
    assert out["pinned"] is False
    assert out["implied_objective"] is None


# --- objective difference definitions -----------------------------------

def test_objective_difference_definitions_are_distinct():
    o_ref, o_test = 0.8739215069684305, 0.8739215056938601
    absolute = objective_difference(o_test, o_ref, mode="absolute")
    relative = objective_difference(o_test, o_ref, mode="relative")
    gated = objective_difference(o_test, o_ref, mode="gated")

    assert absolute == pytest.approx(1.2746e-9, rel=1e-3)
    assert relative == pytest.approx(1.4584e-9, rel=1e-3)
    assert gated == pytest.approx(absolute)          # |o| < 1 so denom is 1
    assert relative > absolute                       # they are NOT interchangeable


def test_relative_difference_refuses_zero_reference():
    with pytest.raises(ValueError, match="undefined"):
        objective_difference(1e-12, 0.0, mode="relative")


def test_unknown_mode_is_rejected():
    with pytest.raises(ValueError, match="unknown mode"):
        objective_difference(1.0, 1.0, mode="rel")
