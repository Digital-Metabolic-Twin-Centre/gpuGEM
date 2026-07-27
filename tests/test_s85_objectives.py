"""Tests for the S85 multi-objective sweep's objective registry and
aggregation/outlier math -- no GPU or Gurobi license required.

Registry tests need the S85 .mat file (MWBM_DIR / mWBM_S85_male.mat) to
resolve reaction names; they are skipped if it isn't available locally.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from benchmarks import s85_objectives as O
from benchmarks import models as M

_S85_SOURCE = Path(M.REGISTRY["S85"]["source"])
requires_s85_mat = pytest.mark.skipif(
    not _S85_SOURCE.exists(), reason="mWBM_S85_male.mat not available (set MWBM_DIR)"
)


# --- registry structure (no model file needed) -----------------------------

def test_at_least_twenty_objectives():
    assert len(O.OBJECTIVES) >= 20


def test_reactions_are_unique():
    reactions = [o["reaction"] for o in O.OBJECTIVES]
    assert len(set(reactions)) == len(reactions)


def test_exactly_one_baseline():
    baselines = [o for o in O.OBJECTIVES if o["is_baseline"]]
    assert len(baselines) == 1


def test_every_objective_has_required_fields():
    required = {"id", "reaction", "category", "rationale", "is_baseline"}
    for o in O.OBJECTIVES:
        assert required.issubset(o.keys())
        assert o["category"] in {"whole_body", "organ_biomass",
                                  "immune_cell_biomass", "microbiome"}


def test_ids_are_unique():
    ids = [o["id"] for o in O.OBJECTIVES]
    assert len(set(ids)) == len(ids)


# --- registry resolves against the real S85 model ---------------------------

@requires_s85_mat
def test_all_reactions_resolve_in_s85_model():
    O.validate_objectives()  # raises ValueError on any unresolved reaction


@requires_s85_mat
def test_get_objective_roundtrip():
    obj = O.get_objective("whole_body")
    assert obj["reaction"] == "Whole_body_objective_rxn"
    with pytest.raises(KeyError):
        O.get_objective("does_not_exist")


# --- aggregation / outlier math on synthetic timing data --------------------

def _fake_result(objective_id, gurobi_s, cuopt_s, both_feasible=True, is_baseline=False):
    return {
        "objective": {"id": objective_id, "reaction": objective_id, "category": "organ_biomass",
                       "rationale": "synthetic", "is_baseline": is_baseline},
        "gurobi": {"solve_s_median": gurobi_s, "feasible": both_feasible},
        "cuopt": {"solve_s_median": cuopt_s, "feasible": both_feasible},
        "both_feasible": both_feasible,
    }


def test_summary_stats_exclude_non_gated_rows():
    from benchmarks import aggregate_sweep as AG

    results = [
        _fake_result("a", gurobi_s=10.0, cuopt_s=100.0, is_baseline=True),
        _fake_result("b", gurobi_s=20.0, cuopt_s=200.0),
        _fake_result("c", gurobi_s=999.0, cuopt_s=1.0, both_feasible=False),  # excluded
    ]
    summary = AG.summarize(results)

    assert summary["n_objectives_total"] == 3
    assert summary["n_objectives_gated"] == 2
    assert summary["gurobi_solve_s_mean"] == pytest.approx(15.0)
    assert summary["cuopt_solve_s_mean"] == pytest.approx(150.0)
    assert summary["baseline_ratio"] == pytest.approx(10.0)


def test_outlier_detection_flags_ratio_outside_band():
    from benchmarks import aggregate_sweep as AG

    results = [
        _fake_result("a", gurobi_s=10.0, cuopt_s=100.0, is_baseline=True),  # ratio 10
        _fake_result("b", gurobi_s=10.0, cuopt_s=90.0),   # ratio 9
        _fake_result("c", gurobi_s=10.0, cuopt_s=110.0),  # ratio 11
        _fake_result("d", gurobi_s=10.0, cuopt_s=5.0),    # ratio 0.5 -- outlier (faster)
        _fake_result("e", gurobi_s=10.0, cuopt_s=1000.0),  # ratio 100 -- outlier (slower)
    ]
    summary = AG.summarize(results)
    outlier_ids = {o["id"] for o in summary["outliers"]}

    assert outlier_ids == {"d", "e"}
    directions = {o["id"]: o["direction"] for o in summary["outliers"]}
    assert directions["d"] == "faster"
    assert directions["e"] == "slower"


def test_summary_handles_all_non_gated():
    from benchmarks import aggregate_sweep as AG

    results = [_fake_result("a", gurobi_s=1.0, cuopt_s=1.0, both_feasible=False)]
    summary = AG.summarize(results)

    assert summary["n_objectives_gated"] == 0
    assert summary["gurobi_solve_s_mean"] is None
    assert summary["cuopt_solve_s_mean"] is None
    assert summary["outliers"] == []
