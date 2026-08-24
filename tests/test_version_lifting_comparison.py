"""Tests for the version x lifting runtime comparison's missing-combination
determination and CSV row-building logic -- no GPU or Gurobi required.
"""
from __future__ import annotations

import json

import pandas as pd
import pytest

from benchmarks import run_version_lifting_comparison as ORC
from benchmarks import aggregate_version_lifting_comparison as AG


# --- missing_combinations (T004) ----------------------------------------------

def test_missing_combinations_recognizes_already_existing_old_unlifted(tmp_path, monkeypatch):
    csv_path = tmp_path / "benchmark.csv"
    pd.DataFrame({"model": ["e_coli_core"], "gurobi_obj": [1.0]}).to_csv(csv_path, index=False)
    monkeypatch.setattr(ORC, "BENCHMARK_CSV", csv_path)
    monkeypatch.setattr(ORC, "MODEL_LIFTING_DIR", tmp_path / "no_such_dir")

    missing = ORC.missing_combinations("e_coli_core")

    assert ("old", False) not in missing
    assert ("new", False) in missing
    assert ("old", True) in missing
    assert ("new", True) in missing


def test_missing_combinations_recognizes_already_existing_old_lifted(tmp_path, monkeypatch):
    csv_path = tmp_path / "benchmark.csv"
    pd.DataFrame({"model": ["S85"], "gurobi_obj": [1.0]}).to_csv(csv_path, index=False)
    monkeypatch.setattr(ORC, "BENCHMARK_CSV", csv_path)

    ml_dir = tmp_path / "model_lifting"
    ml_dir.mkdir()
    (ml_dir / "S85.json").write_text(json.dumps({"comparison": {"verified_correct": False}}))
    monkeypatch.setattr(ORC, "MODEL_LIFTING_DIR", ml_dir)

    missing = ORC.missing_combinations("S85")

    assert ("old", True) not in missing
    assert len(missing) == 2  # only new-unlifted, new-lifted remain
    assert set(missing) == {("new", False), ("new", True)}


def test_missing_combinations_all_four_when_nothing_exists(tmp_path, monkeypatch):
    csv_path = tmp_path / "benchmark.csv"
    pd.DataFrame({"model": ["OtherModel"], "gurobi_obj": [1.0]}).to_csv(csv_path, index=False)
    monkeypatch.setattr(ORC, "BENCHMARK_CSV", csv_path)
    monkeypatch.setattr(ORC, "MODEL_LIFTING_DIR", tmp_path / "no_such_dir")

    missing = ORC.missing_combinations("iML1515")

    assert set(missing) == {("old", False), ("new", False), ("old", True), ("new", True)}


# --- aggregate_version_lifting_comparison row-building (T006) -----------------

def _base_row():
    return pd.Series({
        "model": "iML1515", "n_cols": 2712, "gurobi_solve_s_median": 0.03,
        "cuopt_solve_s_median": 3.75, "both_feasible": True, "gurobi_obj": 1.0,
    })


def test_row_for_out_of_scope_model_has_all_new_columns_none():
    row = AG._row_for_model(
        pd.Series({"model": "S9", "n_cols": 1, "gurobi_solve_s_median": 1.0,
                   "cuopt_solve_s_median": 1.0, "both_feasible": True, "gurobi_obj": 1.0}),
        gurobi_objective=1.0,
    )
    assert row["cuopt_new_unlifted_solve_s_median"] is None
    assert row["cuopt_old_lifted_solve_s_median"] is None
    assert row["cuopt_new_lifted_solve_s_median"] is None
    # base (already-recorded) columns are still populated
    assert row["cuopt_old_unlifted_solve_s_median"] == 1.0


def test_row_for_in_scope_model_pulls_specs013_result(tmp_path, monkeypatch):
    ml_dir = tmp_path / "model_lifting"
    ml_dir.mkdir()
    (ml_dir / "iML1515.json").write_text(json.dumps(
        {"comparison": {"lifted_solve_s": 5.5, "verified_correct": True}}))
    monkeypatch.setattr(AG, "MODEL_LIFTING_DIR", ml_dir)
    monkeypatch.setattr(AG, "VERSION_LIFTING_DIR", tmp_path / "no_such_dir")

    row = AG._row_for_model(_base_row(), gurobi_objective=1.0)

    assert row["cuopt_old_lifted_solve_s_median"] == 5.5
    assert row["cuopt_old_lifted_verified_correct"] is True


def test_row_never_drops_a_failed_combination(tmp_path, monkeypatch):
    """Regression: a verified_correct=False result (mirroring the known S85
    case) must still produce a populated row, never silently omitted."""
    ml_dir = tmp_path / "model_lifting"
    ml_dir.mkdir()
    (ml_dir / "S85.json").write_text(json.dumps(
        {"comparison": {"lifted_solve_s": 450.9, "verified_correct": False}}))
    monkeypatch.setattr(AG, "MODEL_LIFTING_DIR", ml_dir)
    monkeypatch.setattr(AG, "VERSION_LIFTING_DIR", tmp_path / "no_such_dir")

    row = AG._row_for_model(
        pd.Series({"model": "S85", "n_cols": 874634, "gurobi_solve_s_median": 52.6,
                   "cuopt_solve_s_median": 509.4, "both_feasible": True, "gurobi_obj": 1.0}),
        gurobi_objective=1.0,
    )

    assert row["cuopt_old_lifted_solve_s_median"] == 450.9
    assert row["cuopt_old_lifted_verified_correct"] is False  # present, not None/omitted


def test_row_computes_gate_for_freshly_solved_combinations(tmp_path, monkeypatch):
    vl_dir = tmp_path / "version_lifting"
    vl_dir.mkdir()
    (vl_dir / "iML1515.json").write_text(json.dumps({
        "new_unlifted": {"solve_s": 2.1, "status": "Optimal", "objective": 1.0,
                          "residual_inf": 1e-8},
    }))
    monkeypatch.setattr(AG, "VERSION_LIFTING_DIR", vl_dir)
    monkeypatch.setattr(AG, "MODEL_LIFTING_DIR", tmp_path / "no_such_dir")

    row = AG._row_for_model(_base_row(), gurobi_objective=1.0)

    assert row["cuopt_new_unlifted_solve_s_median"] == 2.1
    assert row["cuopt_new_unlifted_verified_correct"] is True


def test_row_gate_fails_on_objective_mismatch(tmp_path, monkeypatch):
    vl_dir = tmp_path / "version_lifting"
    vl_dir.mkdir()
    (vl_dir / "iML1515.json").write_text(json.dumps({
        "new_unlifted": {"solve_s": 2.1, "status": "Optimal", "objective": 2.0,
                          "residual_inf": 1e-8},
    }))
    monkeypatch.setattr(AG, "VERSION_LIFTING_DIR", vl_dir)
    monkeypatch.setattr(AG, "MODEL_LIFTING_DIR", tmp_path / "no_such_dir")

    row = AG._row_for_model(_base_row(), gurobi_objective=1.0)

    assert row["cuopt_new_unlifted_verified_correct"] is False
