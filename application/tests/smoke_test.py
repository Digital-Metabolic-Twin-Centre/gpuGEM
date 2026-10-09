"""
Offline checks for the application library.

Exercises everything that needs neither a GPU nor a Gurobi licence: data
loading, the wild-type objective setup, biomarker parsing, the array
augmentation handed to ``gpugem.solve``, and the scoring stage. Run it with::

    python application/tests/smoke_test.py

One line per check; exits non-zero on the first failure.
"""

from __future__ import annotations

import resource
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cugem_app import biomarkers as bm  # noqa: E402
from cugem_app import data as dat  # noqa: E402
from cugem_app import gpugem_backend as gg  # noqa: E402
from cugem_app import scoring  # noqa: E402

QUERIES = [
    "C02470[bc],incr;kynate[bc],incr",
    "phe_L[bc],increased;tyr_L[bc],decreased",
    "k[bc],decreased;tststerone[bc],decreased;estradiol[bc],decreased",
]


def rss_gb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6


def main() -> int:
    t = time.perf_counter()
    wbm_raw = dat.load_model()
    assert wbm_raw.S.shape[1] == wbm_raw.C.shape[1] == wbm_raw.n_rxns
    print(f"[ok] load_model             {time.perf_counter() - t:5.1f}s  "
          f"rss {rss_gb():.2f}GB  S={wbm_raw.S.shape} C={wbm_raw.C.shape}")
    print(f"[ok] constraint senses      csense={sorted(set(wbm_raw.csense.tolist()))}  "
          f"dsense={sorted(set(wbm_raw.dsense.tolist()))}")

    wbm = dat.setup_wildtype_objective(wbm_raw)
    whole = dat.whole_body_indices(wbm)
    assert len(whole) >= 1
    assert np.all(wbm.lb[whole] == 1.0) and np.all(wbm.ub[whole] == 1.0)
    assert np.count_nonzero(wbm.c) == len(whole)
    assert wbm_raw.c is not wbm.c and wbm_raw.lb is not wbm.lb, "setup must not mutate its input"
    print(f"[ok] wildtype objective     {wbm.rxns[whole[0]]!r} pinned at 1.0, "
          f"objective nnz={np.count_nonzero(wbm.c)}")

    t = time.perf_counter()
    pre = dat.load_precomputed()
    assert len(pre.fbaWT_v) == wbm.n_rxns
    print(f"[ok] load_precomputed       {time.perf_counter() - t:5.1f}s  "
          f"WT nonzero={np.count_nonzero(pre.fbaWT_v)}  rxnGen={pre.rxnGenMatrix.shape}")

    dl = dat.load_disease_list()
    print(f"[ok] load_disease_list      rows={len(dl)}  "
          f"distinct genes={len({e.gene_id for e in dl})}")

    for q in QUERIES:
        d, e, w = bm.parse_biomarkers(q, wbm.mets, wbm.rxns)
        assert d or e, q
        print(f"[ok] parse_biomarkers       {len(d)} demand, {len(e)} exchange  <- {q}")
        for warn in w:
            print(f"     warning: {warn}")

    d, e, _ = bm.parse_biomarkers(QUERIES[0], wbm.mets, wbm.rxns)
    arr = gg.build_augmented_arrays(wbm, d, e)
    n_aug = wbm.n_rxns + len(d)
    assert arr["S"].shape == (wbm.n_mets, n_aug)
    assert arr["C"].shape == (wbm.C.shape[0], n_aug)
    assert len(arr["lb"]) == len(arr["ub"]) == len(arr["c"]) == n_aug
    assert np.allclose(arr["S"].tocsc()[:, wbm.n_rxns:].sum(axis=0), -1.0), \
        "each demand column must drain exactly one unit"
    assert np.array_equal(arr["c"][wbm.n_rxns:], [s.obj for s in d])
    assert np.all(arr["d_lb"] <= arr["d_ub"])
    print(f"[ok] build_augmented_arrays S={arr['S'].shape} C={arr['C'].shape}  "
          f"demand obj={arr['c'][wbm.n_rxns:]}  "
          f"coupling finite lb/ub={int(np.isfinite(arr['d_lb']).sum())}/"
          f"{int(np.isfinite(arr['d_ub']).sum())}")

    t = time.perf_counter()
    rank = scoring.score_genes(wbm, pre, dl, pre.fbaWT_v * 0.5,
                               objective_value=1.0, patient_label="smoke")
    assert not rank.empty
    assert rank["FluxReductionPercentage"].is_monotonic_decreasing
    assert np.allclose(rank["FluxReductionPercentage"], 50.0), \
        "halving every flux must give a uniform 50% reduction"
    print(f"[ok] score_genes            {time.perf_counter() - t:5.1f}s  rows={len(rank)}  "
          f"causal={int(rank['Causal'].sum())}  uniform halving -> FRP 50.0")

    rank0 = scoring.score_genes(wbm, pre, dl, np.zeros(wbm.n_rxns), patient_label="ko")
    assert np.allclose(rank0["FluxReductionPercentage"], 100.0)
    assert rank0["sumFluxWT"].is_monotonic_decreasing, "ties must break on sumFluxWT"
    print(f"[ok] score_genes (knockout) rows={len(rank0)}  all FRP=100.0, "
          f"tie-break on sumFluxWT verified")

    print(f"\nall offline checks passed    peak rss {rss_gb():.2f}GB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
