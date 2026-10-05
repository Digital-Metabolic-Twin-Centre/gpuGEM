"""Tests for gpugem.lifting -- the faithful reformulate.m port.

Correctness is checked generically: given a chosen x_original, the auxiliary
block of a lifted matrix is (by construction) upper-triangular and invertible,
so solving it for the corresponding auxiliary values and plugging both back
into the lifted system's *original* rows must reproduce exactly what solving
the *unlifted* system would give. This validates the transform end-to-end for
any constructed example -- including the row-shared, multiple-large-entries
case reformulate.m specifically optimizes for -- without needing to hand-derive
a closed-form solution per test case.
"""
from __future__ import annotations

import numpy as np
import pytest
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from gpugem.lifting import LiftingMapping, lift_coupling, lift_mass_balance, map_back


def _assert_reproduces_original(S, S_lifted, b, b_lifted, x_original, n_aux_rows):
    """Solve the lifted system's auxiliary rows for x_aux, then confirm the
    lifted system's original rows reproduce S @ x_original exactly."""
    n_mets, n_rxns = S.shape
    n_aux_vars = S_lifted.shape[1] - n_rxns
    x_original = np.asarray(x_original, dtype=np.float64)

    if n_aux_rows == 0:
        np.testing.assert_allclose(S_lifted @ x_original, S @ x_original)
        return

    aux_block = S_lifted[n_mets:, n_rxns:].tocsc()
    orig_block = S_lifted[n_mets:, :n_rxns]
    rhs = -(orig_block @ x_original)
    x_aux = spla.spsolve(aux_block, rhs)

    x_lifted = np.concatenate([x_original, np.atleast_1d(x_aux)])
    residual = S_lifted @ x_lifted - b_lifted

    np.testing.assert_allclose(residual[:n_mets], S @ x_original - b, atol=1e-9)
    np.testing.assert_allclose(residual[n_mets:], 0.0, atol=1e-9)


# --- lift_mass_balance (T007) -------------------------------------------------

def test_lift_mass_balance_single_large_entry_one_level():
    # |value| = 5e4, big=1000 -> dum = floor(log(5e4)/log(1000)) = 1 (single level)
    S = sp.csr_matrix(np.array([[1.0, 5e4]]))
    b = np.zeros(1)

    S_lifted, b_lifted, mapping = lift_mass_balance(S, b, big=1000.0)

    assert mapping.mass_balance_lifted_rows == [0]
    assert mapping.n_aux_vars == 1
    assert mapping.n_aux_rows == 1
    assert np.abs(S_lifted.tocoo().data).max() <= 1000.0 + 1e-6
    _assert_reproduces_original(S, S_lifted, b, b_lifted, [2.0, 0.3], mapping.n_aux_rows)


def test_lift_mass_balance_single_large_entry_multi_level_chain():
    # |value| = 1e10, big=1000 -> dum = floor(log(1e10)/log(1000)) = 3
    S = sp.csr_matrix(np.array([[1.0, 1e10]]))
    b = np.zeros(1)

    S_lifted, b_lifted, mapping = lift_mass_balance(S, b, big=1000.0)

    assert mapping.n_aux_vars == 3
    assert mapping.n_aux_rows == 3
    assert np.abs(S_lifted.tocoo().data).max() <= 1000.0 + 1e-3
    _assert_reproduces_original(S, S_lifted, b, b_lifted, [1.0, -0.7], mapping.n_aux_rows)


def test_lift_mass_balance_shared_chain_multiple_entries_same_row():
    """Two large entries in the same row with different levels must share one
    chain (reformulate.m's row-sharing optimization), not get two independent
    chains -- exercised by using big=100 so the two entries need different
    dum levels (dum=1 and dum=2)."""
    # |v1| = 5e3 -> dum=1 at big=100; |v2| = 5e5 -> dum=2 at big=100
    S = sp.csr_matrix(np.array([[5e3, 5e5, 1.0]]))
    b = np.zeros(1)

    S_lifted, b_lifted, mapping = lift_mass_balance(S, b, big=100.0)

    # a shared chain of length max(dum)=2 -> exactly 2 aux vars/rows, not
    # 1+2=3 (which independent chains per entry would require)
    assert mapping.n_aux_vars == 2
    assert mapping.n_aux_rows == 2
    _assert_reproduces_original(S, S_lifted, b, b_lifted, [3.0, -1.0, 0.5], mapping.n_aux_rows)


def test_lift_mass_balance_ignores_nonhomogeneous_rows():
    S = sp.csr_matrix(np.array([[5e4, 1.0]]))
    b = np.array([2.0])  # b != 0 -- not a candidate, per reformulate.m's own precondition

    S_lifted, b_lifted, mapping = lift_mass_balance(S, b, big=1000.0)

    assert mapping.mass_balance_lifted_rows == []
    assert mapping.n_aux_vars == 0
    np.testing.assert_allclose(S_lifted.toarray(), S.toarray())


def test_lift_mass_balance_no_op_when_nothing_exceeds_big():
    S = sp.csr_matrix(np.array([[1.0, 2.0], [3.0, -1.0]]))
    b = np.zeros(2)

    S_lifted, b_lifted, mapping = lift_mass_balance(S, b, big=1000.0)

    assert mapping.mass_balance_lifted_rows == []
    assert mapping.n_aux_vars == 0
    assert mapping.n_aux_rows == 0
    np.testing.assert_allclose(S_lifted.toarray(), S.toarray())
    np.testing.assert_allclose(b_lifted, b)


# --- lift_coupling (T008) ------------------------------------------------------

def _base_mapping(n_vars, n_stoich_rows):
    return LiftingMapping(
        n_original_vars=n_vars,
        n_original_stoich_rows=n_stoich_rows,
        n_original_coupling_rows=None,
        big=1000.0,
        n_aux_vars=0,
        n_aux_rows=0,
    )


def test_lift_coupling_matching_pattern_is_lifted():
    # row: v0 - 5e4*v1 <= 0  (homogeneous, opposite sign, 2 nonzeros -> matches)
    C = sp.csr_matrix(np.array([[1.0, -5e4]]))
    d_lb = np.array([-1e30])
    d_ub = np.array([0.0])
    mapping = _base_mapping(n_vars=2, n_stoich_rows=1)

    C_lifted, d_lb_l, d_ub_l, out_mapping = lift_coupling(C, d_lb, d_ub, 1000.0, mapping)

    assert out_mapping.coupling_lifted_rows == [0]
    assert out_mapping.n_aux_vars > 0
    assert np.abs(C_lifted.tocoo().data).max() <= 1000.0 + 1e-6

    # reconstruct: pick v1, solve aux chain, confirm original row reproduced
    x_original = np.array([0.0, 2.0])  # v0 irrelevant to reconstructing v1's contribution
    n_orig_cols = 2
    aux_block = C_lifted[1:, n_orig_cols:].tocsc()
    orig_block = C_lifted[1:, :n_orig_cols]
    rhs = -(orig_block @ x_original)
    x_aux = spla.spsolve(aux_block, rhs) if aux_block.shape[0] else np.zeros(0)
    x_full = np.concatenate([x_original, np.atleast_1d(x_aux)])
    row0 = C_lifted[0, :].toarray().ravel() @ x_full
    expected = (C @ x_original)[0]
    np.testing.assert_allclose(row0, expected, atol=1e-9)


def test_lift_coupling_same_sign_row_not_lifted():
    C = sp.csr_matrix(np.array([[1.0, 5e4]]))  # same sign -- doesn't match pattern
    d_lb = np.array([-1e30])
    d_ub = np.array([0.0])
    mapping = _base_mapping(n_vars=2, n_stoich_rows=1)

    C_lifted, *_ , out_mapping = lift_coupling(C, d_lb, d_ub, 1000.0, mapping)

    assert out_mapping.coupling_lifted_rows == []
    np.testing.assert_allclose(C_lifted.toarray(), C.toarray())


def test_lift_coupling_three_nonzero_row_not_lifted():
    C = sp.csr_matrix(np.array([[1.0, -5e4, 2.0]]))  # 3 nonzeros -- doesn't match pattern
    d_lb = np.array([-1e30])
    d_ub = np.array([0.0])
    mapping = _base_mapping(n_vars=3, n_stoich_rows=1)

    C_lifted, *_, out_mapping = lift_coupling(C, d_lb, d_ub, 1000.0, mapping)

    assert out_mapping.coupling_lifted_rows == []


def test_lift_coupling_only_lifts_the_larger_of_two_large_entries():
    """Documented reformulate.m behavior (not a gap introduced here): if a
    matching row has two entries both exceeding big, only the larger one is
    lifted -- the smaller stays in place, possibly still exceeding big."""
    C = sp.csr_matrix(np.array([[5e3, -5e6]]))
    d_lb = np.array([-1e30])
    d_ub = np.array([0.0])
    mapping = _base_mapping(n_vars=2, n_stoich_rows=1)

    C_lifted, *_, out_mapping = lift_coupling(C, d_lb, d_ub, 1000.0, mapping)

    assert out_mapping.coupling_lifted_rows == [0]
    # the smaller (5e3) entry is untouched and still exceeds big=1000
    row0 = C_lifted[0, :2].toarray().ravel()
    assert row0[0] == pytest.approx(5e3)


# --- map_back (T009) -----------------------------------------------------------

def test_map_back_returns_prefix_slice():
    mapping = LiftingMapping(
        n_original_vars=3, n_original_stoich_rows=1, n_original_coupling_rows=None,
        big=1000.0, n_aux_vars=2, n_aux_rows=2,
    )
    fluxes_lifted = np.array([1.0, 2.0, 3.0, 99.0, 98.0])

    result = map_back(fluxes_lifted, mapping)

    np.testing.assert_array_equal(result, [1.0, 2.0, 3.0])


def test_map_back_raises_clearly_on_too_short_input():
    mapping = LiftingMapping(
        n_original_vars=5, n_original_stoich_rows=1, n_original_coupling_rows=None,
        big=1000.0,
    )
    with pytest.raises(ValueError):
        map_back(np.array([1.0, 2.0]), mapping)


# --- gpugem.solve(..., lift=True) integration (T014-T015) ---------------------

def _e_coli_core_lp():
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from benchmarks import models as M

    pytest.importorskip(
        "cobra", reason='optional dependency missing: pip install "gpugem[cobra]"')
    lp, _ = M.build_lp("e_coli_core")
    return lp


def test_solve_lift_true_matches_lift_false_on_e_coli_core():
    """e_coli_core has no coefficient exceeding the default lift_big=1000.0,
    so lifting must be a safe no-op: same objective, same fluxes, and (since
    nothing was lifted) fluxes at exactly the original length -- spec User
    Story 2 Acceptance Scenario 1."""
    import gpugem

    lp = _e_coli_core_lp()

    r_unlifted = gpugem.solve(**lp, time_limit=30.0)
    r_lifted = gpugem.solve(**lp, time_limit=30.0, lift=True)

    assert r_unlifted.status == "Optimal"
    assert r_lifted.status == "Optimal"
    assert r_lifted.objective == pytest.approx(r_unlifted.objective, abs=1e-6)
    assert len(r_lifted.fluxes) == len(r_unlifted.fluxes) == lp["S"].shape[1]
    np.testing.assert_allclose(r_lifted.fluxes, r_unlifted.fluxes, atol=1e-5)


def test_solve_cobra_and_fbasolver_inherit_lift_with_zero_code_changes():
    """Regression test for the 'free integration' claim (research.md R4):
    solve_cobra and FBASolver both already forward arbitrary keyword
    arguments to solve(), so lift=True must work through them with no
    changes to solve_cobra.py or the FBASolver class."""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from benchmarks import models as M

    cobra = pytest.importorskip(
        "cobra", reason='optional dependency missing: pip install "gpugem[cobra]"')
    import gpugem

    cache = M.CACHE / "e_coli_core.xml"
    model = cobra.io.read_sbml_model(str(cache))

    r_direct = gpugem.solve(**M.build_lp("e_coli_core")[0], time_limit=30.0, lift=True)
    r_cobra = gpugem.solve_cobra(model, time_limit=30.0, lift=True)

    lp = M.build_lp("e_coli_core")[0]
    r_fba_solver = gpugem.FBASolver(**lp, time_limit=30.0, lift=True).solve()

    assert r_cobra.status == "Optimal"
    assert r_fba_solver.status == "Optimal"
    assert r_cobra.objective == pytest.approx(r_direct.objective, abs=1e-6)
    assert r_fba_solver.objective == pytest.approx(r_direct.objective, abs=1e-6)
