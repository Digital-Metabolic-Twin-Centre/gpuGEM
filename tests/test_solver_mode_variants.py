"""Tests for the S85 solver-mode experiment's variant registry and
comparison/speedup math -- no GPU or Gurobi license required.
"""
from __future__ import annotations

import pytest

from benchmarks import solver_mode_variants as V


# --- registry structure ------------------------------------------------------

def test_ids_are_unique():
    ids = [v["id"] for v in V.SOLVER_MODE_VARIANTS]
    assert len(set(ids)) == len(ids)


def test_exactly_one_baseline():
    baselines = [v for v in V.SOLVER_MODE_VARIANTS if v["is_baseline"]]
    assert len(baselines) == 1
    assert baselines[0]["id"] == "baseline"


def test_baseline_has_no_overrides():
    baseline = V.get_variant("baseline")
    assert baseline["cuopt_kwargs"] == {}


def test_expected_four_variants():
    ids = {v["id"] for v in V.SOLVER_MODE_VARIANTS}
    assert ids == {"baseline", "methodical1", "concurrent", "barrier_cold"}


def test_every_variant_has_required_fields():
    required = {"id", "cuopt_kwargs", "rationale", "is_baseline"}
    for v in V.SOLVER_MODE_VARIANTS:
        assert required.issubset(v.keys())
        assert isinstance(v["cuopt_kwargs"], dict)


def test_get_variant_roundtrip():
    v = V.get_variant("methodical1")
    assert v["cuopt_kwargs"] == {"pdlp_solver_mode": 2}
    with pytest.raises(KeyError):
        V.get_variant("does_not_exist")


# --- registry resolves against cuOpt's live parameter registry --------------

def test_all_cuopt_kwargs_are_real_parameters():
    V.validate_variants()  # raises ValueError on any unknown parameter name


# --- speedup / best-candidate math on synthetic results ---------------------

def _fake_result(variant_id, solve_s, verified_correct=True, completed=True, is_baseline=False):
    return {
        "variant": {"id": variant_id, "cuopt_kwargs": {}, "rationale": "synthetic",
                    "is_baseline": is_baseline},
        "outcome": "Completed" if completed else "DidNotComplete",
        "solve_s": solve_s if completed else None,
        "verified_correct": verified_correct and completed,
    }


def test_speedup_and_best_candidate_selection():
    from benchmarks import aggregate_solver_modes as AG

    results = [
        _fake_result("baseline", 500.0, is_baseline=True),
        _fake_result("methodical1", 250.0),   # 2x speedup
        _fake_result("concurrent", 100.0),    # 5x speedup -- best
        _fake_result("barrier_cold", 600.0),  # slower than baseline
    ]
    summary = AG.summarize(results)

    assert summary["baseline_solve_s"] == pytest.approx(500.0)
    candidates = {c["id"]: c for c in summary["candidates"]}
    assert candidates["methodical1"]["speedup"] == pytest.approx(2.0)
    assert candidates["concurrent"]["speedup"] == pytest.approx(5.0)
    assert candidates["barrier_cold"]["speedup"] == pytest.approx(500.0 / 600.0)
    assert summary["best_candidate_id"] == "concurrent"
    assert summary["best_candidate_speedup"] == pytest.approx(5.0)
    assert summary["any_did_not_complete"] is False


def test_no_candidate_beats_baseline_reported_plainly():
    from benchmarks import aggregate_solver_modes as AG

    results = [
        _fake_result("baseline", 500.0, is_baseline=True),
        _fake_result("methodical1", 600.0),
        _fake_result("concurrent", 550.0),
        _fake_result("barrier_cold", 700.0),
    ]
    summary = AG.summarize(results)

    assert summary["best_candidate_id"] is None
    assert summary["best_candidate_speedup"] is None


def test_incorrect_candidate_not_eligible_as_best():
    from benchmarks import aggregate_solver_modes as AG

    results = [
        _fake_result("baseline", 500.0, is_baseline=True),
        _fake_result("methodical1", 10.0, verified_correct=False),  # fast but wrong
        _fake_result("concurrent", 400.0),                          # slower but correct
        _fake_result("barrier_cold", 700.0),
    ]
    summary = AG.summarize(results)

    # The fast-but-wrong candidate must never be selected as best.
    assert summary["best_candidate_id"] == "concurrent"


def test_did_not_complete_candidate_flagged_not_dropped():
    from benchmarks import aggregate_solver_modes as AG

    results = [
        _fake_result("baseline", 500.0, is_baseline=True),
        _fake_result("methodical1", 250.0),
        _fake_result("concurrent", 100.0),
        _fake_result("barrier_cold", None, completed=False),  # crashed/timed out
    ]
    summary = AG.summarize(results)

    assert summary["any_did_not_complete"] is True
    candidates = {c["id"]: c for c in summary["candidates"]}
    assert candidates["barrier_cold"]["solve_s"] is None
    assert candidates["barrier_cold"]["speedup"] is None
    # A variant that didn't complete must still appear -- not silently dropped.
    assert "barrier_cold" in candidates
