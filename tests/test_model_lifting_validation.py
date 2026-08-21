"""Tests for the pure comparison/gating math in
benchmarks/run_model_lifting_validation.py -- no GPU required.
"""
from __future__ import annotations

import pytest

from benchmarks.run_model_lifting_validation import build_comparison


def test_matching_optimal_results_are_verified_correct():
    comparison = build_comparison(
        "fake_model",
        unlifted_status="Optimal", lifted_status="Optimal",
        unlifted_objective=1.0, lifted_objective=1.0,
        unlifted_residual=1e-8, lifted_residual=1e-8,
        unlifted_solve_s=1.0, lifted_solve_s=2.0,
    )
    assert comparison["verified_correct"] is True
    assert comparison["objective_agrees"] is True


def test_objective_mismatch_is_flagged_not_silently_passed():
    comparison = build_comparison(
        "fake_model",
        unlifted_status="Optimal", lifted_status="Optimal",
        unlifted_objective=1.0, lifted_objective=2.0,
        unlifted_residual=1e-8, lifted_residual=1e-8,
        unlifted_solve_s=1.0, lifted_solve_s=2.0,
    )
    assert comparison["verified_correct"] is False
    assert comparison["objective_agrees"] is False


def test_residual_over_tolerance_is_flagged_not_silently_passed():
    comparison = build_comparison(
        "fake_model",
        unlifted_status="Optimal", lifted_status="Optimal",
        unlifted_objective=1.0, lifted_objective=1.0,
        unlifted_residual=1e-8, lifted_residual=1.0,  # way over res_tol
        unlifted_solve_s=1.0, lifted_solve_s=2.0,
    )
    assert comparison["verified_correct"] is False


def test_non_optimal_lifted_status_is_flagged_even_with_matching_objective():
    comparison = build_comparison(
        "fake_model",
        unlifted_status="Optimal", lifted_status="TimeLimit",
        unlifted_objective=1.0, lifted_objective=1.0,
        unlifted_residual=1e-8, lifted_residual=1e-8,
        unlifted_solve_s=1.0, lifted_solve_s=2.0,
    )
    assert comparison["verified_correct"] is False


def test_none_lifted_residual_never_silently_passes():
    comparison = build_comparison(
        "fake_model",
        unlifted_status="Optimal", lifted_status="Optimal",
        unlifted_objective=1.0, lifted_objective=1.0,
        unlifted_residual=1e-8, lifted_residual=None,
        unlifted_solve_s=1.0, lifted_solve_s=2.0,
    )
    assert comparison["verified_correct"] is False
