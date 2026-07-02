"""Basic solver tests using a small synthetic LP."""

import numpy as np
import pytest
import scipy.sparse as sp


@pytest.fixture
def tiny_lp():
    """Minimal feasible LP: 4 reactions, 3 metabolites, no coupling constraints."""
    # S: 3 metabolites × 4 reactions
    S = sp.csr_matrix(np.array([
        [ 1, -1,  0,  0],
        [ 0,  1, -1,  0],
        [ 0,  0,  1, -1],
    ], dtype=np.float64))
    b  = np.zeros(3)
    lb = np.zeros(4)
    ub = np.ones(4) * 10.0
    c  = np.array([0., 0., 0., 1.])   # maximise v4
    return dict(S=S, b=b, lb=lb, ub=ub, c=c, maximize=True)


def test_solve_optimal(tiny_lp):
    import gpugem
    result = gpugem.solve(**tiny_lp, time_limit=10.0)
    assert result.status in ("Optimal", "TimeLimit")
    assert result.objective is not None
    assert result.fluxes is not None
    assert len(result.fluxes) == 4


def test_feasibility_metrics(tiny_lp):
    import gpugem
    result = gpugem.solve(**tiny_lp, time_limit=10.0, check_feasibility=True)
    assert "stoich_max_residual" in result.feasibility
    assert result.feasibility["stoich_max_residual"] < 1e-3


def test_objective_value(tiny_lp):
    import gpugem
    result = gpugem.solve(**tiny_lp, time_limit=10.0)
    if result.status == "Optimal":
        assert abs(result.objective - 10.0) < 1e-3   # max flux = upper bound = 10


def test_cuopt_override(tiny_lp):
    """Extra cuOpt kwargs are accepted without error."""
    import gpugem
    result = gpugem.solve(**tiny_lp, time_limit=10.0, pdlp_solver_mode=0)
    assert result.status in ("Optimal", "TimeLimit", "NoTermination")


def test_fba_solver_stateful(tiny_lp):
    import gpugem
    solver = gpugem.FBASolver(**tiny_lp, time_limit=10.0)
    r1 = solver.solve()
    # Re-solve with a different objective
    c_new = np.array([1., 0., 0., 0.])
    r2 = solver.solve(c=c_new)
    assert r1.status in ("Optimal", "TimeLimit")
    assert r2.status in ("Optimal", "TimeLimit")


def test_default_settings_small_model():
    from gpugem._defaults import default_settings
    s = default_settings(n_vars=50_000)
    assert "presolve" not in s   # no PaPILO for small models
    assert s["per_constraint_residual"] == 1


def test_default_settings_large_model():
    from gpugem._defaults import default_settings
    s = default_settings(n_vars=200_000)
    assert s.get("presolve") == 1   # PaPILO required for large models
    assert s["per_constraint_residual"] == 1
