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


# --- figure data prep (make_violation_distribution_figures._smooth_curve) ---

def test_smooth_curve_tapers_to_zero_at_both_ends():
    from benchmarks.make_violation_distribution_figures import _smooth_curve

    edges = np.logspace(-9, 3, 25)
    counts = np.zeros(24)
    counts[10] = 50.0

    y, x = _smooth_curve(edges, counts)

    assert y[0] == pytest.approx(edges[0])
    assert y[-1] == pytest.approx(edges[-1])
    assert x[0] == pytest.approx(0.0)
    assert x[-1] == pytest.approx(0.0)
    assert x.max() > 0  # the bump in the middle is preserved, not smoothed away


def test_smooth_curve_never_goes_negative():
    """PCHIP can overshoot near sharp jumps (e.g. a single nonzero bin between zeros);
    the figure clips this so a rendered band never implies a negative count."""
    from benchmarks.make_violation_distribution_figures import _smooth_curve

    edges = np.logspace(-9, 3, 25)
    counts = np.zeros(24)
    counts[5] = 1.0  # an isolated spike -- the case most likely to overshoot

    y, x = _smooth_curve(edges, counts)

    assert np.all(x >= 0.0)


def test_zero_violation_model_still_yields_a_plottable_curve():
    """A model with no violations at all (n_satisfied == n_rows) must still produce a
    valid, empty-but-not-omitted histogram -- the figure represents it, not silently
    drops it (spec edge case)."""
    h = histogram(np.zeros(500))

    from benchmarks.make_violation_distribution_figures import _smooth_curve

    y, x = _smooth_curve(h["bin_edges"], h["shortfall_counts"])
    assert np.all(x == 0.0)  # a flat, empty (but present) contour, not an error


# --- figure data prep (make_violation_distribution_figures._label_anchor/_angle) --

def test_label_anchor_picks_true_peak_on_the_negative_shortfall_side():
    """Regression test: x is signed (negative on the shortfall side), so "widest
    point" means largest magnitude, not largest signed value -- a naive sort by -x
    would treat the near-zero tail as "best" and the true (very negative) peak as
    "worst" on this side."""
    from benchmarks.make_violation_distribution_figures import _label_anchor
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    ax.set_xlim(-1000, 1000)
    ax.set_ylim(0, 10)
    y = np.linspace(0, 10, 50)
    x = -np.abs(np.sin(np.linspace(0, np.pi, 50))) * 900  # peak (most negative) at the middle

    idx, _ = _label_anchor(ax, y, x, placed_px=[])

    assert 20 <= idx <= 30  # near the middle, where |x| is largest


def test_label_angle_always_in_readable_range():
    """Regression test: the old sign-based +/-180 adjustment could leave the angle
    outside (-90, 90], rendering the label upside-down/mirrored."""
    from benchmarks.make_violation_distribution_figures import _label_angle
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    ax.set_xlim(-1000, 1000)
    ax.set_ylim(0, 10)
    y = np.linspace(0, 10, 50)

    for x in (np.linspace(-900, 900, 50), np.linspace(900, -900, 50), np.full(50, -500.0)):
        angle = _label_angle(ax, y, x, idx=25)
        assert -90 <= angle <= 90
