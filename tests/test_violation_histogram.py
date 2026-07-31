"""Tests for signed per-row constraint-violation vectors and their binned histogram
representation -- no GPU required.
"""
from __future__ import annotations

import numpy as np
import pytest

from benchmarks.violation_histogram import histogram, signed_row_violations


# --- signed_row_violations ----------------------------------------------------

def test_signed_row_violations_equality_rows_reduce_to_signed_residual():
    A = np.eye(3)
    b = np.array([1.0, 2.0, 3.0])
    v = np.array([1.0, 2.5, 2.0])  # row0 satisfied, row1 exceeds, row2 falls short

    viol = signed_row_violations(A, b, b, v)

    assert viol[0] == pytest.approx(0.0)
    assert viol[1] == pytest.approx(0.5)   # excess
    assert viol[2] == pytest.approx(-1.0)  # shortfall


def test_signed_row_violations_true_range_rows():
    A = np.eye(2)
    lb = np.array([0.0, 0.0])
    ub = np.array([10.0, 10.0])
    v = np.array([5.0, 15.0])  # within range, above range

    viol = signed_row_violations(A, lb, ub, v)

    assert viol[0] == pytest.approx(0.0)
    assert viol[1] == pytest.approx(5.0)


# --- histogram ------------------------------------------------------------

def test_histogram_invariant_holds_and_zero_violations_still_valid():
    violations = np.zeros(1000)  # a model with no violations at all

    h = histogram(violations)

    assert h["n_rows"] == 1000
    assert h["n_satisfied"] == 1000
    assert sum(h["shortfall_counts"]) == 0
    assert sum(h["excess_counts"]) == 0
    # invariant: n_satisfied + sum(shortfall) + sum(excess) == n_rows
    assert h["n_satisfied"] + sum(h["shortfall_counts"]) + sum(h["excess_counts"]) == h["n_rows"]


def test_histogram_splits_shortfall_and_excess_by_direction():
    violations = np.array([-5.0, -0.001, 2.0, 0.0, 300.0])

    h = histogram(violations)

    assert h["n_rows"] == 5
    assert h["n_satisfied"] == 1
    assert sum(h["shortfall_counts"]) == 2
    assert sum(h["excess_counts"]) == 2
    assert h["n_satisfied"] + sum(h["shortfall_counts"]) + sum(h["excess_counts"]) == h["n_rows"]


def test_histogram_magnitude_below_floor_counts_as_satisfied():
    # smaller than the smallest bin edge (1e-9) but not exactly zero -- treated as satisfied,
    # not silently dropped from the invariant
    violations = np.array([1e-15, -1e-12])

    h = histogram(violations)

    assert h["n_satisfied"] == 2
    assert sum(h["shortfall_counts"]) == 0
    assert sum(h["excess_counts"]) == 0


def test_histogram_bin_edges_match_shared_constant():
    from benchmarks.violation_histogram import MAGNITUDE_BIN_EDGES

    h = histogram(np.array([1.0]))

    assert h["bin_edges"] == pytest.approx(MAGNITUDE_BIN_EDGES.tolist())
    assert len(h["bin_edges"]) == 25
    assert len(h["shortfall_counts"]) == 24
    assert len(h["excess_counts"]) == 24
