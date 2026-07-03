"""Tests for coefficient decomposition helpers."""

import numpy as np
import scipy.sparse as sp


def test_decompose_stoichiometry_preserves_original_rows():
    from gpugem.scaling import decompose_stoichiometry, remap_fluxes

    S = sp.csr_matrix(
        np.array(
            [
                [1e-6, 2.0, 10000.0],
                [-3.0, -1e-5, 4.0],
            ],
            dtype=np.float64,
        )
    )
    x = np.array([7.0, -2.0, 0.5])

    S_scaled, mapping = decompose_stoichiometry(S, min_abs=0.1, max_abs=100.0)

    x_scaled = np.zeros(S_scaled.shape[1])
    x_scaled[: S.shape[1]] = x
    for entry in mapping.split_entries:
        original_flux = x[entry["col"]]
        downstream = original_flux
        for aux_col, factor in zip(reversed(entry["aux_cols"]), reversed(entry["factors"])):
            downstream = factor * downstream
            x_scaled[aux_col] = downstream

    residual = S_scaled @ x_scaled
    np.testing.assert_allclose(residual[: S.shape[0]], S @ x, rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(residual[S.shape[0] :], 0.0, atol=1e-12)
    np.testing.assert_allclose(remap_fluxes(x_scaled, mapping), x)


def test_scale_model_extends_arrays_and_coupling_columns():
    import gpugem

    model = {
        "S": sp.csr_matrix([[1e-6, 10000.0]]),
        "b": np.zeros(1),
        "lb": np.array([-10.0, 0.0]),
        "ub": np.array([10.0, 100.0]),
        "c": np.array([1.0, 0.0]),
        "C": sp.csr_matrix([[1.0, 0.0]]),
        "d_lb": np.array([-np.inf]),
        "d_ub": np.array([5.0]),
        "maximize": True,
    }

    scaled, mapping = gpugem.scale_model(model, min_abs=0.1, max_abs=100.0)

    assert scaled["S"].shape[0] > model["S"].shape[0]
    assert scaled["S"].shape[1] > model["S"].shape[1]
    assert scaled["C"].shape[1] == scaled["S"].shape[1]
    assert scaled["b"].shape[0] == scaled["S"].shape[0]
    assert scaled["lb"].shape[0] == scaled["S"].shape[1]
    assert scaled["ub"].shape[0] == scaled["S"].shape[1]
    assert scaled["c"].shape[0] == scaled["S"].shape[1]
    assert mapping.n_original_vars == 2
    assert mapping.aux_bound == 100.0
    assert np.all(scaled["c"][mapping.aux_var_indices] == 0.0)
    assert np.all(scaled["lb"][mapping.aux_var_indices] == -100.0)
    assert np.all(scaled["ub"][mapping.aux_var_indices] == 100.0)
