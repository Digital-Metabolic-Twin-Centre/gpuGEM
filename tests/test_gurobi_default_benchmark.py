"""Tests for the Gurobi default-settings benchmark: solve_gurobi's
bar_iters/simplex_iters extension, the existing-result loading and
default-settings solve/gate logic, and the comparison-CSV assembly --
no GPU required; a real (tiny, license-free) Gurobi model is used for the
solve_gurobi extension test since gurobipy is already a project dependency.
"""
from __future__ import annotations

import json

import numpy as np
import pytest
import scipy.sparse as sp


# --- solve_gurobi's bar_iters/simplex_iters extension (T002) ----------------

@pytest.fixture
def tiny_lp():
    """Minimal feasible LP: 4 reactions, 3 metabolites, no coupling constraints."""
    S = sp.csr_matrix(np.array([
        [ 1, -1,  0,  0],
        [ 0,  1, -1,  0],
        [ 0,  0,  1, -1],
    ], dtype=np.float64))
    return dict(S=S, b=np.zeros(3), lb=np.zeros(4), ub=np.ones(4) * 10.0,
                c=np.array([0., 0., 0., 1.]), maximize=True)


def test_solve_gurobi_returns_bar_and_simplex_iters(tiny_lp):
    from benchmarks.solve import solve_gurobi

    result = solve_gurobi(tiny_lp, time_limit=10.0)

    assert "bar_iters" in result
    assert "simplex_iters" in result
    assert isinstance(result["bar_iters"], int)
    assert isinstance(result["simplex_iters"], int)
    # existing keys unaffected -- additive change only
    assert result["status"] == "Optimal"
    assert result["iters"] in (result["bar_iters"], result["simplex_iters"])


def test_solve_gurobi_default_method_picks_one_algorithm(tiny_lp):
    from benchmarks.solve import solve_gurobi

    result = solve_gurobi(tiny_lp, time_limit=10.0, method=-1)

    assert result["method"] == -1
    # continuous LP + Method=-1 deterministically picks exactly one algorithm
    assert (result["bar_iters"] > 0) != (result["simplex_iters"] > 0) or \
        (result["bar_iters"] == 0 and result["simplex_iters"] >= 0)


# --- _load_existing_result (T003) --------------------------------------------

def _fake_main_result(tmp_path, model="FakeModel"):
    d = {
        "provenance": {"model": model, "scale": "microbiome", "n_cols": 12345},
        "time_limit": 900.0,
        "res_tol": 1e-4,
        "obj_tol": 1e-6,
        "gurobi": {
            "solve_s_median": 50.0, "objective": 1.0,
            "repeats": [{"status": "Optimal", "iters": 91, "residual_inf": 1e-6}],
        },
        "cuopt": {
            "solve_s_median": 500.0, "objective": 1.0,
            "repeats": [{"status": "Optimal", "iters": 984000, "residual_inf": 8.9e-05}],
        },
    }
    (tmp_path / (model + ".json")).write_text(json.dumps(d))


def test_load_existing_result_reuses_reported_values(tmp_path, monkeypatch):
    _fake_main_result(tmp_path)
    import benchmarks.run_gurobi_default_benchmark as RT
    monkeypatch.setattr(RT, "RESULTS_MAIN", tmp_path)

    existing = RT._load_existing_result("FakeModel")

    assert existing["scale"] == "microbiome"
    assert existing["n_cols"] == 12345
    assert existing["time_limit"] == 900.0
    assert existing["cuopt_solve_s"] == 500.0
    assert existing["cuopt_objective"] == 1.0
    assert existing["gurobi_barrier_solve_s"] == 50.0
    assert existing["gurobi_barrier_residual_inf"] == 1e-6


def test_load_existing_result_missing_file_raises_clearly(tmp_path, monkeypatch):
    import benchmarks.run_gurobi_default_benchmark as RT
    monkeypatch.setattr(RT, "RESULTS_MAIN", tmp_path)

    with pytest.raises(FileNotFoundError):
        RT._load_existing_result("NoSuchModel")


# --- _solve_default's correctness gate (T007) --------------------------------

def _existing(res_tol=1e-4, obj_tol=1e-6, cuopt_objective=1.0, time_limit=900.0, n_cols=4):
    return {
        "n_cols": n_cols, "time_limit": time_limit,
        "res_tol": res_tol, "obj_tol": obj_tol, "cuopt_objective": cuopt_objective,
    }


def _fake_solve_gurobi_result(status="Optimal", objective=1.0, fluxes=None,
                               bar_iters=0, simplex_iters=10, solve_s=0.01):
    return {
        "solver": "gurobi", "solve_s": solve_s, "objective": objective, "status": status,
        "iters": simplex_iters, "fluxes": fluxes, "method": -1,
        "bar_iters": bar_iters, "simplex_iters": simplex_iters,
    }


def _patch_solve(monkeypatch, RT, lp, gurobi_result):
    monkeypatch.setattr(RT.M, "build_lp", lambda model: (lp, None))
    monkeypatch.setattr(RT.SV, "solve_gurobi", lambda lp_, time_limit, method: gurobi_result)


def _tiny_feasible_lp():
    S = sp.csr_matrix(np.array([[1.0, -1.0]]))
    return dict(S=S, b=np.zeros(1), lb=np.zeros(2), ub=np.ones(2) * 10.0,
                c=np.array([0., 1.]), maximize=True)


def test_solve_default_marks_feasible_solve_as_passing(monkeypatch):
    import benchmarks.run_gurobi_default_benchmark as RT
    lp = _tiny_feasible_lp()
    gurobi_result = _fake_solve_gurobi_result(status="Optimal", objective=1.0,
                                               fluxes=np.array([5.0, 5.0]), bar_iters=3, simplex_iters=0)
    _patch_solve(monkeypatch, RT, lp, gurobi_result)

    result = RT._solve_default("FakeModel", _existing(cuopt_objective=1.0))

    assert result["feasible"] is True
    assert result["obj_agree_with_cuopt"] is True
    assert result["solved_by"] == "barrier"


def test_solve_default_marks_failed_status_as_infeasible_not_dropped(monkeypatch):
    """A default-settings solve that fails the correctness gate is still
    recorded and clearly marked -- never silently dropped (spec FR-003)."""
    import benchmarks.run_gurobi_default_benchmark as RT
    lp = _tiny_feasible_lp()
    gurobi_result = _fake_solve_gurobi_result(status="TimeLimit", objective=None,
                                               fluxes=None, bar_iters=0, simplex_iters=5)
    _patch_solve(monkeypatch, RT, lp, gurobi_result)

    result = RT._solve_default("FakeModel", _existing(cuopt_objective=1.0))

    assert result is not None
    assert result["status"] == "TimeLimit"
    assert result["feasible"] is False
    assert result["obj_agree_with_cuopt"] is False
    assert result["solved_by"] == "simplex"


def test_solve_default_marks_objective_disagreement_as_infeasible(monkeypatch):
    import benchmarks.run_gurobi_default_benchmark as RT
    lp = _tiny_feasible_lp()
    gurobi_result = _fake_solve_gurobi_result(status="Optimal", objective=999.0,
                                               fluxes=np.array([5.0, 5.0]), bar_iters=1, simplex_iters=0)
    _patch_solve(monkeypatch, RT, lp, gurobi_result)

    result = RT._solve_default("FakeModel", _existing(cuopt_objective=1.0))

    assert result["obj_agree_with_cuopt"] is False


# --- aggregate_gurobi_default (T012) -----------------------------------------

def _fake_gurobi_default_result(model="FakeModel", solve_s=25.0, feasible=True, obj_agree=True):
    return {
        "model": model, "n_cols": 12345, "solve_s": solve_s, "objective": 1.0,
        "status": "Optimal", "residual_inf": 1e-6, "bar_iters": 3, "simplex_iters": 0,
        "solved_by": "barrier", "feasible": feasible, "obj_agree_with_cuopt": obj_agree,
        "time_limit": 900.0,
    }


def test_load_rows_joins_reused_and_fresh_columns(tmp_path, monkeypatch):
    main_dir = tmp_path / "main"
    gdef_dir = tmp_path / "gurobi_default"
    main_dir.mkdir()
    gdef_dir.mkdir()
    _fake_main_result(main_dir, model="e_coli_core")
    (gdef_dir / "e_coli_core.json").write_text(json.dumps(_fake_gurobi_default_result("e_coli_core")))

    import benchmarks.aggregate_gurobi_default as AG
    monkeypatch.setattr(AG, "RESULTS_MAIN", main_dir)
    monkeypatch.setattr(AG, "RESULTS", gdef_dir)
    monkeypatch.setattr(AG.M, "ALL_MODELS", ["e_coli_core"])

    rows = AG.load_rows()

    assert len(rows) == 1
    row = rows[0]
    assert row["model"] == "e_coli_core"
    assert row["cuopt_solve_s"] == 500.0
    assert row["gurobi_barrier_solve_s"] == 50.0
    assert row["gurobi_default_solve_s"] == 25.0
    assert row["gurobi_default_speedup_vs_barrier"] == pytest.approx(50.0 / 25.0)
    assert row["both_feasible"] is True


def test_load_rows_skips_models_without_a_default_result(tmp_path, monkeypatch):
    main_dir = tmp_path / "main"
    gdef_dir = tmp_path / "gurobi_default"
    main_dir.mkdir()
    gdef_dir.mkdir()
    _fake_main_result(main_dir, model="e_coli_core")
    # no gurobi_default/e_coli_core.json written -- not yet solved

    import benchmarks.aggregate_gurobi_default as AG
    monkeypatch.setattr(AG, "RESULTS_MAIN", main_dir)
    monkeypatch.setattr(AG, "RESULTS", gdef_dir)
    monkeypatch.setattr(AG.M, "ALL_MODELS", ["e_coli_core"])

    assert AG.load_rows() == []


def test_write_comparison_csv_has_required_columns(tmp_path, monkeypatch):
    import benchmarks.aggregate_gurobi_default as AG
    monkeypatch.setattr(AG, "RESULTS", tmp_path)
    monkeypatch.setattr(AG, "COMPARISON_CSV", tmp_path / "comparison.csv")

    row = {col: 0 for col in AG.CSV_COLUMNS}
    AG.write_comparison_csv([row])

    import csv
    with open(tmp_path / "comparison.csv") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == AG.CSV_COLUMNS
        assert len(list(reader)) == 1
