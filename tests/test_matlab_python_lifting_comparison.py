"""Tests for the pure pieces of the MATLAB vs Python lifted-model comparison
-- no live Gurobi or MATLAB required.

Covers benchmarks/_matlab_python_lifting_worker.py::flux_summary and
benchmarks/run_matlab_python_lifting_comparison.py::build_comparison_row.
"""
from __future__ import annotations

import numpy as np
import scipy.sparse as sp

from benchmarks._matlab_python_lifting_worker import flux_summary
from benchmarks.run_matlab_python_lifting_comparison import build_comparison_row


def _run(status="Optimal", objective=1.0, l2=1.0, max_abs=1.0, residual=1e-8,
         n_aux_vars=3, excluded=False, excluded_reason=None):
    return {
        "status": status, "objective": objective,
        "flux_summary": None if l2 is None else {
            "l2_norm": l2, "max_abs": max_abs, "residual_inf": residual,
        },
        "n_aux_vars": n_aux_vars,
        "solve_s": 1.23,
        "excluded": excluded, "excluded_reason": excluded_reason,
    }


# --- flux_summary ---

def test_flux_summary_none_when_no_fluxes():
    assert flux_summary(None, sp.csr_matrix((1, 2)), np.zeros(1)) is None


def test_flux_summary_computes_l2_max_and_residual():
    S = sp.csr_matrix(np.array([[1.0, -1.0]]))
    b = np.array([0.0])
    fluxes = np.array([2.0, 2.0])
    summary = flux_summary(fluxes, S, b)
    assert summary["residual_inf"] == 0.0
    assert summary["max_abs"] == 2.0
    assert summary["l2_norm"] == np.linalg.norm(fluxes)


# --- build_comparison_row ---

def test_matching_results_are_verified_correct():
    row = build_comparison_row("fake_model", _run(), _run(), n_cols=10)
    assert row["verified_correct"] is True
    assert row["status_agrees"] is True
    assert row["objective_agrees"] is True
    assert row["flux_agrees"] is True
    assert row["excluded_models"] is None


def test_status_mismatch_is_flagged_not_silently_passed():
    row = build_comparison_row(
        "fake_model", _run(status="Optimal"), _run(status="TimeLimit"), n_cols=10)
    assert row["status_agrees"] is False
    assert row["verified_correct"] is False


def test_objective_mismatch_is_flagged_not_silently_passed():
    row = build_comparison_row(
        "fake_model", _run(objective=1.0), _run(objective=2.0), n_cols=10)
    assert row["objective_agrees"] is False
    assert row["verified_correct"] is False


def test_flux_mismatch_is_flagged_not_silently_passed():
    row = build_comparison_row(
        "fake_model", _run(l2=1.0), _run(l2=100.0), n_cols=10)
    assert row["flux_agrees"] is False
    assert row["verified_correct"] is False


def test_flux_residual_over_tolerance_is_flagged():
    row = build_comparison_row(
        "fake_model", _run(residual=1.0), _run(residual=1e-8), n_cols=10)
    assert row["flux_agrees"] is False
    assert row["verified_correct"] is False


def test_aux_var_mismatch_alone_does_not_force_failure():
    """Edge case (spec): different aux-variable counts are a data point, not
    by themselves a correctness failure."""
    row = build_comparison_row(
        "fake_model", _run(n_aux_vars=3), _run(n_aux_vars=5), n_cols=10)
    assert row["aux_vars_match"] is False
    assert row["verified_correct"] is True  # everything else still agrees


def test_excluded_model_never_silently_dropped():
    row = build_comparison_row(
        "fake_model", _run(excluded=True, excluded_reason="MATLAB timed out"),
        _run(), n_cols=10)
    assert row["excluded_models"] is not None
    assert "MATLAB timed out" in row["excluded_models"]
    assert row["verified_correct"] is False
    # the row itself is still present with the model name -- never omitted
    assert row["model"] == "fake_model"


def test_both_excluded_still_produces_a_row():
    row = build_comparison_row(
        "fake_model",
        _run(excluded=True, excluded_reason="matlab crash"),
        _run(excluded=True, excluded_reason="python crash"),
        n_cols=10)
    assert "matlab crash" in row["excluded_models"]
    assert "python crash" in row["excluded_models"]
    assert row["verified_correct"] is False
