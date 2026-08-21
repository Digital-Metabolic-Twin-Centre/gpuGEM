"""Tests for the cuOpt-native settings-tuning investigation: candidate-registry
validation and the ranking/speedup math -- no GPU or Gurobi license required.
"""
from __future__ import annotations

import json

import numpy as np
import pytest
import scipy.sparse as sp

from benchmarks import cuopt_tuning_candidates as C
from benchmarks import aggregate_cuopt_tuning as AG
from benchmarks import cuopt_tuning_preprocessing as P


# --- registry structure (T004) -----------------------------------------------

def test_ids_are_unique():
    ids = [c["id"] for c in C.CANDIDATES]
    assert len(set(ids)) == len(ids)


def test_exactly_one_baseline_with_no_overrides():
    baselines = [c for c in C.CANDIDATES if c["id"] == "baseline"]
    assert len(baselines) == 1
    assert baselines[0]["cuopt_kwargs"] == {}
    assert baselines[0]["warm_start"] is False


def test_every_candidate_has_required_fields():
    required = {"id", "user_story", "cuopt_kwargs", "warm_start", "source_note",
                "requires_isolated_venv"}
    for c in C.CANDIDATES:
        assert required.issubset(c.keys())
        assert isinstance(c["cuopt_kwargs"], dict)
        assert isinstance(c["warm_start"], bool)
        assert c["user_story"] in {"US1", "US2", "US3"}
        assert c["source_note"]  # non-empty -- traceability, spec FR-011


def test_every_candidate_kwargs_are_real_cuopt_parameters():
    from cuopt.linear_programming.solver_settings.solver_settings import (
        get_solver_parameter_names,
    )
    names = set(get_solver_parameter_names())
    for c in C.CANDIDATES:
        bad = [k for k in c["cuopt_kwargs"] if k not in names]
        assert not bad, (c["id"], bad)


def test_every_warm_start_candidate_sets_presolve_off():
    """presolve=0 (fully OFF) is the only value that permits PDLP warm start,
    per research.md R4 -- a warm_start=True candidate that forgot this would
    silently fail at solve time."""
    for c in C.CANDIDATES:
        if c["warm_start"]:
            assert c["cuopt_kwargs"].get("presolve") == 0, c["id"]


def test_every_warm_start_candidate_uses_a_supported_solver_mode():
    """Only Stable2 (1) and Fast1 (3) support the explicit warm-start API,
    per the installed SolverSettings.set_pdlp_warm_start_data docstring."""
    for c in C.CANDIDATES:
        if c["warm_start"]:
            assert c["cuopt_kwargs"].get("pdlp_solver_mode") in (1, 3), c["id"]


def test_no_duplicate_of_004s_plain_concurrent_candidate():
    """specs/004-s85-solver-mode-experiment/ already published method=Concurrent
    with no other overrides; re-running that exact combination would contradict
    spec FR-001's "going beyond the specific settings already tried."""
    for c in C.CANDIDATES:
        if c["cuopt_kwargs"] == {"method": 0}:
            pytest.fail("duplicate of 004's already-published plain Concurrent candidate")


def test_get_candidate_looks_up_by_id():
    c = C.get_candidate("baseline")
    assert c["id"] == "baseline"
    with pytest.raises(KeyError):
        C.get_candidate("no-such-id")


def test_linked_results_reference_an_existing_prior_feature_path():
    for entry in C.LINKED_RESULTS:
        assert entry["result_path"].parts[-3:-1] == ("results", "residual_tradeoff")


# --- select_upgrade_candidates (T009) -----------------------------------------

def test_select_upgrade_candidates_picks_baseline_plus_fastest_verified_correct(tmp_path):
    (tmp_path / "baseline.json").write_text(json.dumps(
        {"solve_s": 500.0, "verified_correct": True}))
    (tmp_path / "pdlp_mode_fast1.json").write_text(json.dumps(
        {"solve_s": 200.0, "verified_correct": True}))
    (tmp_path / "pdlp_precision_mixed.json").write_text(json.dumps(
        {"solve_s": 50.0, "verified_correct": False}))  # faster but not correct -- excluded

    ids = C.select_upgrade_candidates(tmp_path)

    assert ids == ["baseline", "pdlp_mode_fast1"]


def test_select_upgrade_candidates_baseline_only_when_nothing_verified_correct(tmp_path):
    (tmp_path / "baseline.json").write_text(json.dumps(
        {"solve_s": 500.0, "verified_correct": True}))
    (tmp_path / "pdlp_mode_fast1.json").write_text(json.dumps(
        {"solve_s": 200.0, "verified_correct": False}))

    ids = C.select_upgrade_candidates(tmp_path)

    assert ids == ["baseline"]


def test_select_upgrade_candidates_handles_no_results_on_disk_yet(tmp_path):
    ids = C.select_upgrade_candidates(tmp_path)
    assert ids == ["baseline"]


# --- aggregate_cuopt_tuning ranking math (T018) -------------------------------

def _result(id_, solve_s, verified_correct=True, user_story="US1", speedup_note="x"):
    return {
        "id": id_, "user_story": user_story, "cuopt_version": "26.6.0",
        "cuopt_kwargs": {}, "phases": [], "status": "Optimal" if verified_correct else "TimeLimit",
        "solve_s": solve_s, "iterations": 100, "objective": 1.0,
        "residual_inf": 1e-6, "objective_agrees_with_gurobi": verified_correct,
        "verified_correct": verified_correct, "source_note": speedup_note, "error": None,
    }


def test_speedup_vs_baseline_and_vs_gurobi_computed_correctly():
    gurobi_solve_s = 50.0
    results = [
        _result("baseline", 500.0),
        _result("pdlp_mode_fast1", 100.0),
    ]

    summary = AG.summarize(results, gurobi_solve_s)

    row = next(r for r in summary["rows"] if r["candidate_id"] == "pdlp_mode_fast1")
    assert row["speedup_vs_baseline"] == pytest.approx(5.0)
    assert row["speedup_vs_gurobi"] == pytest.approx(0.5)


def test_best_candidate_selection_never_picks_a_verified_incorrect_result():
    """A candidate that's fast but fails the correctness gate must never win,
    regardless of how good its solve_s looks."""
    gurobi_solve_s = 50.0
    results = [
        _result("baseline", 500.0),
        _result("fast_but_wrong", 1.0, verified_correct=False),
        _result("slower_but_correct", 200.0, verified_correct=True),
    ]

    summary = AG.summarize(results, gurobi_solve_s)

    assert summary["best_candidate_id"] == "slower_but_correct"


def test_candidates_beating_gurobi_reported_explicitly_when_present():
    gurobi_solve_s = 50.0
    results = [
        _result("baseline", 500.0),
        _result("beats_gurobi", 40.0, verified_correct=True),
    ]

    summary = AG.summarize(results, gurobi_solve_s)

    assert summary["candidates_beating_gurobi"] == ["beats_gurobi"]
    # ranked first: verified_correct, highest speedup_vs_gurobi
    assert summary["rows"][0]["candidate_id"] == "beats_gurobi"


def test_no_candidate_beats_gurobi_reported_explicitly_not_omitted():
    gurobi_solve_s = 50.0
    results = [
        _result("baseline", 500.0),
        _result("close_but_not_there", 60.0, verified_correct=True),
    ]

    summary = AG.summarize(results, gurobi_solve_s)

    assert summary["candidates_beating_gurobi"] == []
    assert summary["closest_to_gurobi_id"] == "close_but_not_there"
    assert summary["closest_to_gurobi_speedup"] == pytest.approx(50.0 / 60.0)


def test_write_summary_produces_csv_with_gurobi_speedup_column(tmp_path, monkeypatch):
    monkeypatch.setattr(AG, "RESULTS", tmp_path)
    monkeypatch.setattr(AG, "SUMMARY_JSON", tmp_path / "summary.json")
    monkeypatch.setattr(AG, "SUMMARY_CSV", tmp_path / "summary.csv")

    results = [_result("baseline", 500.0), _result("pdlp_mode_fast1", 100.0)]
    summary = AG.summarize(results, 50.0)
    AG.write_summary(summary)

    import csv as csv_mod
    with open(tmp_path / "summary.csv") as f:
        rows = list(csv_mod.DictReader(f))
    assert "speedup_vs_gurobi" in rows[0]
    assert len(rows) == 2


# --- preprocessing transform/inverse exactness (T012, CPU-only) --------------

def _fake_lp():
    # a tiny, extreme-range LP -- mirrors S85's [1e-6, 2e5] characterization (R5)
    S = sp.csr_matrix(np.array([
        [1e-6, 0.0, 2e5],
        [0.0, 3.0, -1e-3],
    ]))
    return {
        "S": S, "b": np.array([1.0, 2.0]),
        "lb": np.array([0.0, 0.0, 0.0]), "ub": np.array([10.0, 10.0, 10.0]),
        "c": np.array([1.0, 2.0, 3.0]), "maximize": False,
    }


def test_preprocessing_transform_produces_better_conditioned_matrix():
    lp = _fake_lp()
    transformed, context = P.transform(lp)

    orig_range = np.abs(sp.csr_matrix(lp["S"]).data)
    new_range = np.abs(sp.csr_matrix(transformed["S"]).data)
    orig_ratio = orig_range.max() / orig_range.min()
    new_ratio = new_range.max() / new_range.min()
    assert new_ratio < orig_ratio


def test_preprocessing_inverse_exactly_recovers_original_lp_semantics():
    """A feasible point in the transformed space must map back to a point that
    satisfies the *original* S v = b to numerical precision -- this is the
    "not simplified, recovers the original result" requirement (spec FR-008),
    checked here on the pure linear-algebra transform before any solver runs."""
    lp = _fake_lp()
    transformed, context = P.transform(lp)

    # any feasible v' for the transformed system...
    S_t = sp.csr_matrix(transformed["S"])
    n = S_t.shape[1]
    v_prime = np.linalg.lstsq(S_t.toarray(), transformed["b"], rcond=None)[0]

    v_reconstructed = P.inverse(v_prime, context)

    S_orig = sp.csr_matrix(lp["S"])
    residual = np.max(np.abs(S_orig @ v_reconstructed - lp["b"]))
    assert residual < 1e-8


def test_preprocessing_inverse_handles_none_fluxes():
    context = {"col_scale": np.array([1.0, 2.0, 3.0])}
    assert P.inverse(None, context) is None


# --- load_results includes every user story (regression) ---------------------

def test_load_results_includes_preprocessing_candidate_not_silently_dropped(
        tmp_path, monkeypatch):
    """Regression: load_results originally only iterated C.CANDIDATES (US1/US2),
    silently dropping any PREPROCESSING_CANDIDATES (US3) result even when its
    JSON file existed on disk -- exactly the kind of silent omission spec
    FR-010 forbids."""
    monkeypatch.setattr(AG, "RESULTS", tmp_path)
    monkeypatch.setattr(AG, "S85_RESULT", tmp_path / "S85.json")
    (tmp_path / "S85.json").write_text(json.dumps(
        {"gurobi": {"solve_s_median": 50.0, "objective": 1.0},
         "res_tol": 1e-4, "obj_tol": 1e-6}))

    preproc_id = C.PREPROCESSING_CANDIDATES[0]["id"]
    (tmp_path / (preproc_id + ".json")).write_text(json.dumps(
        _result(preproc_id, 66.5, verified_correct=False, user_story="US3")))

    results = AG.load_results()

    assert any(r["id"] == preproc_id for r in results)
