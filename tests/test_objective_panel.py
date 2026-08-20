"""Tests for the cross-model objective-panel credibility benchmark:
reaction-lookup resolution (both model kinds), panel/settings loading, the
median-display-vs-all-repeats-gate distinction, and the two-CSV aggregation
logic -- no GPU/Gurobi required.
"""
from __future__ import annotations

import json

import numpy as np
import pytest


# --- _build_lp_with_objective (T005) -----------------------------------------

def test_build_lp_with_objective_resolves_cobra_kind_reaction():
    from benchmarks.objective_panel import _build_lp_with_objective

    lp, prov = _build_lp_with_objective("e_coli_core", "EX_ac_e")

    assert prov["objective_rxn"] == "EX_ac_e"
    assert lp["maximize"] is True
    assert np.count_nonzero(lp["c"]) == 1
    assert lp["c"][prov["objective_idx"]] == 1.0


def test_build_lp_with_objective_resolves_mat_kind_reaction(monkeypatch):
    from benchmarks import objective_panel as OP
    from benchmarks import models as M

    fake_rxns = np.array(["rxnA", "rxnB", "TargetRxn", "rxnD"])
    monkeypatch.setattr(M, "_mat_rxns", lambda path, model_key: fake_rxns)

    class _FakeLp(dict):
        pass

    fake_lp = {"S": np.zeros((2, 4)), "c": np.zeros(4), "maximize": False}
    monkeypatch.setattr(M, "build_lp", lambda name: (dict(fake_lp), {}))

    lp, prov = OP._build_lp_with_objective("Harvey", "TargetRxn")

    assert prov["objective_idx"] == 2
    assert prov["objective_rxn"] == "TargetRxn"
    assert lp["c"][2] == 1.0
    assert lp["maximize"] is True


def test_build_lp_with_objective_missing_reaction_raises_clearly(monkeypatch):
    from benchmarks import objective_panel as OP
    from benchmarks import models as M

    fake_rxns = np.array(["rxnA", "rxnB"])
    monkeypatch.setattr(M, "_mat_rxns", lambda path, model_key: fake_rxns)
    fake_lp = {"S": np.zeros((1, 2)), "c": np.zeros(2), "maximize": False}
    monkeypatch.setattr(M, "build_lp", lambda name: (dict(fake_lp), {}))

    with pytest.raises(ValueError):
        OP._build_lp_with_objective("Harvey", "NoSuchRxn")


# --- _load_panel / _load_settings (T006) -------------------------------------

def test_load_panel_reads_reaction_id_and_category_in_order(tmp_path, monkeypatch):
    import benchmarks.objective_panel as OP
    monkeypatch.setattr(OP, "CANDIDATES", tmp_path)

    (tmp_path / "FakeModel.csv").write_text(
        "reaction_id,category,other_col\n"
        "rxn1,cat_a,x\n"
        "rxn2,cat_b,y\n"
    )

    panel = OP._load_panel("FakeModel")

    assert panel == [
        {"reaction_id": "rxn1", "category": "cat_a"},
        {"reaction_id": "rxn2", "category": "cat_b"},
    ]


def test_load_panel_missing_file_raises_clearly(tmp_path, monkeypatch):
    import benchmarks.objective_panel as OP
    monkeypatch.setattr(OP, "CANDIDATES", tmp_path)

    with pytest.raises(FileNotFoundError):
        OP._load_panel("NoSuchModel")


def test_load_settings_reuses_published_values(tmp_path, monkeypatch):
    import benchmarks.objective_panel as OP
    monkeypatch.setattr(OP, "RESULTS_MAIN", tmp_path)

    d = {"reps": 3, "time_limit": 900.0, "res_tol": 1e-4, "obj_tol": 1e-6}
    (tmp_path / "FakeModel.json").write_text(json.dumps(d))

    settings = OP._load_settings("FakeModel")

    assert settings == d


def test_load_settings_missing_file_raises_clearly(tmp_path, monkeypatch):
    import benchmarks.objective_panel as OP
    monkeypatch.setattr(OP, "RESULTS_MAIN", tmp_path)

    with pytest.raises(FileNotFoundError):
        OP._load_settings("NoSuchModel")


# --- _summarize_solver's per-repeat gate (T009, research R7) ----------------

def _repeat(solve_s, objective, status="Optimal", residual_inf=1e-8, feasible=True, iters=10):
    return {"repeat": 0, "solve_s": solve_s, "objective": objective, "status": status,
            "iters": iters, "residual_inf": residual_inf, "feasible": feasible}


def test_summarize_solver_gates_on_every_repeat_not_the_median():
    """A combination with one individually-failing repeat must gate to
    feasible=False even if the median residual looks acceptable."""
    from benchmarks.run_objective_panel import _summarize_solver

    reps = [
        _repeat(1.0, 5.0, residual_inf=1e-8, feasible=True),
        _repeat(1.1, 5.0, residual_inf=1e-8, feasible=True),
        _repeat(1.2, None, status="Infeasible", residual_inf=1e-8, feasible=False),
    ]

    summary = _summarize_solver(reps)

    # median residual is fine (all three are 1e-8) -- but one repeat failed
    assert summary["residual_inf_median"] == pytest.approx(1e-8)
    assert summary["feasible"] is False


def test_summarize_solver_reports_medians_not_single_run_or_extremes():
    from benchmarks.run_objective_panel import _summarize_solver

    reps = [
        _repeat(10.0, 5.0, residual_inf=1e-6),
        _repeat(20.0, 5.0, residual_inf=2e-6),
        _repeat(30.0, 5.0, residual_inf=3e-6),
    ]

    summary = _summarize_solver(reps)

    assert summary["solve_s_median"] == pytest.approx(20.0)
    assert summary["residual_inf_median"] == pytest.approx(2e-6)
    assert summary["feasible"] is True


# --- aggregate_objective_panel row assembly (T014) ---------------------------

def _fake_objective_result(model="FakeModel", objective_id="rxn1", both_feasible=True):
    return {
        "model": model, "objective_id": objective_id, "reaction_id": objective_id,
        "category": "organ_biomass",
        "gurobi": {"solve_s_median": 5.0, "objective_median": 1.0, "status": "Optimal",
                   "residual_inf_median": 1e-7, "iters_median": 12, "feasible": both_feasible},
        "cuopt": {"solve_s_median": 50.0, "objective_median": 1.0, "status": "Optimal",
                  "residual_inf_median": 1e-6, "iters_median": 8000, "feasible": both_feasible},
        "obj_agree_with_cuopt": both_feasible,
        "both_feasible": both_feasible,
    }


def test_runtime_rows_contains_only_objective_value_and_runtime():
    from benchmarks.aggregate_objective_panel import runtime_rows, RUNTIME_COLUMNS

    rows = runtime_rows(_fake_objective_result())

    assert len(rows) == 2  # one per solver
    assert {r["solver"] for r in rows} == {"cuopt", "gurobi"}
    assert set(RUNTIME_COLUMNS) == {
        "model", "objective_id", "reaction_id", "solver",
        "objective_value_median", "runtime_s_median",
    }
    gurobi_row = next(r for r in rows if r["solver"] == "gurobi")
    assert gurobi_row["runtime_s_median"] == 5.0
    assert gurobi_row["objective_value_median"] == 1.0


def test_detail_rows_has_violation_and_correctness_columns():
    from benchmarks.aggregate_objective_panel import detail_rows

    rows = detail_rows(_fake_objective_result())

    cuopt_row = next(r for r in rows if r["solver"] == "cuopt")
    assert cuopt_row["residual_inf_median"] == 1e-6
    assert cuopt_row["iters_median"] == 8000
    assert cuopt_row["both_feasible"] is True


# --- failed combinations are never dropped (T016) ----------------------------

def test_failed_combination_still_produces_detail_rows():
    from benchmarks.aggregate_objective_panel import detail_rows

    rows = detail_rows(_fake_objective_result(both_feasible=False))

    assert len(rows) == 2
    assert all(r["both_feasible"] is False for r in rows)


def test_load_results_and_write_csvs_include_failed_combination(tmp_path, monkeypatch):
    import benchmarks.aggregate_objective_panel as AG

    monkeypatch.setattr(AG, "RESULTS", tmp_path)
    monkeypatch.setattr(AG, "RUNTIME_CSV", tmp_path / "objective_runtime.csv")
    monkeypatch.setattr(AG, "DETAILS_CSV", tmp_path / "benchmark_details.csv")
    monkeypatch.setattr(AG.M, "ALL_MODELS", ["FakeModel"])
    monkeypatch.setattr(AG.OP, "CANDIDATES", tmp_path)
    (tmp_path / "FakeModel.csv").write_text("reaction_id,category\nrxn1,organ_biomass\n")

    model_dir = tmp_path / "FakeModel"
    model_dir.mkdir()
    (model_dir / "rxn1.json").write_text(
        json.dumps(_fake_objective_result(objective_id="rxn1", both_feasible=False)))

    results = AG.load_results()
    AG.write_csvs(results)

    import csv as csv_mod
    with open(AG.DETAILS_CSV) as f:
        rows = list(csv_mod.DictReader(f))
    assert len(rows) == 2
    assert all(r["both_feasible"] == "False" for r in rows)


def test_load_results_preserves_panel_order_not_alphabetical_filename_order(tmp_path, monkeypatch):
    """Regression test: ATPM.json sorts before BIOMASS_*.json alphabetically,
    but the panel's actual first/baseline row is BIOMASS_* -- load_results
    must follow panel order, not glob-sorted filenames."""
    import benchmarks.aggregate_objective_panel as AG

    monkeypatch.setattr(AG, "RESULTS", tmp_path)
    monkeypatch.setattr(AG.M, "ALL_MODELS", ["FakeModel"])
    monkeypatch.setattr(AG.OP, "CANDIDATES", tmp_path)
    (tmp_path / "FakeModel.csv").write_text(
        "reaction_id,category\nBIOMASS_x,growth\nATPM,energy_maintenance\n")

    model_dir = tmp_path / "FakeModel"
    model_dir.mkdir()
    (model_dir / "ATPM.json").write_text(
        json.dumps(_fake_objective_result(objective_id="ATPM")))
    (model_dir / "BIOMASS_x.json").write_text(
        json.dumps(_fake_objective_result(objective_id="BIOMASS_x")))

    results = AG.load_results()

    assert [r["objective_id"] for r in results] == ["BIOMASS_x", "ATPM"]
