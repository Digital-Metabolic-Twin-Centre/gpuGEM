"""Tests for the constraint-residual speed/correctness trade-off benchmark's
comparison-assembly logic and figure data prep -- no GPU or Gurobi required.
"""
from __future__ import annotations

import json

import pytest

from benchmarks.run_residual_tradeoff import build_model_comparison


# --- _load_002_result --------------------------------------------------------

def _fake_002_result(tmp_path, model="FakeModel"):
    d = {
        "provenance": {"model": model, "scale": "microbiome", "n_cols": 12345},
        "time_limit": 900.0,
        "gurobi": {
            "solve_s_median": 50.0, "objective": 1.0,
            "repeats": [{"status": "Optimal", "iters": 91, "residual_inf": 1e-6}],
        },
        "cuopt": {
            "solve_s_median": 500.0, "objective": 1.0,
            "repeats": [{"status": "Optimal", "iters": 984000, "residual_inf": 8.9e-05}],
        },
    }
    p = tmp_path / (model + ".json")
    p.write_text(json.dumps(d))
    return p


def test_load_002_result_marks_reused_and_null_rows_violated(tmp_path, monkeypatch):
    _fake_002_result(tmp_path)
    import benchmarks.run_residual_tradeoff as RT
    monkeypatch.setattr(RT, "RESULTS_002", tmp_path)

    shipped, gurobi, scale, n_cols = RT._load_002_result("FakeModel")

    assert shipped["source"] == "reused"
    assert gurobi["source"] == "reused"
    assert shipped["rows_violated"] is None
    assert gurobi["rows_violated"] is None
    assert shipped["solve_s"] == 500.0
    assert gurobi["solve_s"] == 50.0
    assert shipped["residual_inf"] == 8.9e-05
    assert scale == "microbiome"
    assert n_cols == 12345
    assert shipped["time_limit"] == 900.0


def test_load_002_result_missing_file_raises_clearly(tmp_path, monkeypatch):
    import benchmarks.run_residual_tradeoff as RT
    monkeypatch.setattr(RT, "RESULTS_002", tmp_path)

    with pytest.raises(FileNotFoundError):
        RT._load_002_result("NoSuchModel")


# --- build_model_comparison ---------------------------------------------------

def _result(solve_s, residual_inf, source="reused", rows_violated=None, configuration="x"):
    return {
        "configuration": configuration, "source": source, "solve_s": solve_s,
        "iterations": 1, "status": "Optimal", "objective": 1.0,
        "residual_inf": residual_inf, "rows_violated": rows_violated, "time_limit": 900.0,
    }


def test_build_model_comparison_speedup_and_violation_ratio():
    shipped = _result(500.0, 8.9e-05, configuration="shipped_default")
    residual_0 = _result(6.5, 156.4, source="fresh", rows_violated=12345, configuration="residual_0")
    gurobi = _result(50.0, 1e-6, configuration="gurobi")

    comp = build_model_comparison("S85", "microbiome", 874634, shipped, residual_0, gurobi)

    assert comp["speedup_residual_0_vs_shipped"] == pytest.approx(500.0 / 6.5)
    assert comp["violation_ratio_residual_0_vs_shipped"] == pytest.approx(156.4 / 8.9e-05)
    assert comp["residual_0"]["rows_violated"] == 12345
    assert comp["shipped_default"]["rows_violated"] is None
    assert comp["gurobi"]["rows_violated"] is None


def test_build_model_comparison_preserves_all_three_results():
    shipped = _result(500.0, 8.9e-05, configuration="shipped_default")
    residual_0 = _result(6.5, 156.4, source="fresh", configuration="residual_0")
    gurobi = _result(50.0, 1e-6, configuration="gurobi")

    comp = build_model_comparison("S85", "microbiome", 874634, shipped, residual_0, gurobi)

    # nothing removed or replaced -- all three configurations present side by side
    assert comp["shipped_default"]["solve_s"] == 500.0
    assert comp["residual_0"]["solve_s"] == 6.5
    assert comp["gurobi"]["solve_s"] == 50.0


# --- figure data prep (make_residual_tradeoff_figures._floor_for_log) -------

def test_floor_for_log_handles_zero_without_crashing():
    from benchmarks.make_residual_tradeoff_figures import _floor_for_log
    import numpy as np

    plotted, floor = _floor_for_log([0.0, 1e-8, 5.0])

    assert np.all(np.isfinite(plotted))
    assert np.all(plotted > 0)  # log-scale-safe
    assert plotted[0] == pytest.approx(floor)  # the zero was floored, not dropped
    assert plotted[1] == pytest.approx(1e-8)   # non-zero values pass through unchanged
    assert plotted[2] == pytest.approx(5.0)


def test_floor_for_log_all_zero_uses_fallback_floor():
    from benchmarks.make_residual_tradeoff_figures import _floor_for_log

    plotted, floor = _floor_for_log([0.0, 0.0])

    assert floor == 1e-12
    assert list(plotted) == [1e-12, 1e-12]
