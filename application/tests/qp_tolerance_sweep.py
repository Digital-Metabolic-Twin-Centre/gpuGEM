#!/usr/bin/env python3
"""
Does the minimum-norm QP actually pin a unique patient flux?

Stage 3 exists so that the patient solution does not depend on which optimal
vertex the LP happened to stop at. That only works if the QP is solved tightly
enough to reach its own optimum. This script tests the claim directly: run the
same case through both backends at a series of barrier convergence tolerances
and measure how far apart the two answers are.

If the QP does its job, the gap between backends should fall towards zero as
the tolerance tightens. If it does not, the reported ranking depends on the
solver, which matters for anyone trying to reproduce the published numbers.

    python qp_tolerance_sweep.py --case cyp17 --tols 1e-4 1e-6 1e-8
"""

from __future__ import annotations

import argparse
import importlib
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cugem_app import data as dat  # noqa: E402

CASES = {
    "pah": "phe_L[bc],increased;tyr_L[bc],decreased",
    "kynurenic": "C02470[bc],incr;kynate[bc],incr",
    "cyp17": "k[bc],decreased;tststerone[bc],decreased;estradiol[bc],decreased",
}
KEY = ["Disease", "Gene"]


def run_at_tolerance(biomarkers: str, backend: str, tol: float,
                     data_dir: Path, label: str):
    """Re-import the backend so the module-level tolerance is picked up."""
    os.environ["CUGEM_QP_BARCONVTOL"] = repr(tol)
    import cugem_app.gurobi_backend as gb
    import cugem_app.pipeline as pl
    importlib.reload(gb)
    importlib.reload(pl)
    assert gb.QP_BAR_CONV_TOL == tol, (gb.QP_BAR_CONV_TOL, tol)

    t0 = time.time()
    res = pl.run_query(biomarkers, backend=backend, data_dir=data_dir, label=label)
    return res.ranking, time.time() - t0, res.timings.get("qp", float("nan"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cases", nargs="+", default=["cyp17"], choices=sorted(CASES))
    p.add_argument("--tols", type=float, nargs="+", default=[1e-4, 1e-6, 1e-8])
    p.add_argument("--data-dir", type=Path, default=dat.DEFAULT_DATA_DIR)
    p.add_argument("--out", type=Path, default=Path("qp_tolerance_sweep.csv"))
    args = p.parse_args(argv)

    rows = []
    for case in args.cases:
        biomarkers = CASES[case]
        print(f"\n=== {case}: {biomarkers} ===", flush=True)
        for tol in args.tols:
            out = {"case": case, "tol": tol}
            runs = {}
            for backend in ("gurobi", "gpugem"):
                try:
                    df, wall, t_qp = run_at_tolerance(
                        biomarkers, backend, tol, args.data_dir, case)
                except Exception as exc:
                    print(f"  tol {tol:.0e}  {backend:7s} FAILED: "
                          f"{type(exc).__name__}: {exc}", flush=True)
                    continue
                for col in KEY:
                    df[col] = df[col].astype(str).str.strip()
                runs[backend] = df
                out[f"{backend}_rows"] = len(df)
                out[f"{backend}_qp_s"] = round(t_qp, 2)
                out[f"{backend}_lp_s"] = round(wall, 2)

            if len(runs) == 2:
                m = runs["gurobi"].merge(runs["gpugem"], on=KEY,
                                         suffixes=("_cpu", "_gpu"))
                d = np.abs(m["FluxReductionPercentage_cpu"]
                           - m["FluxReductionPercentage_gpu"])
                out["shared_rows"] = len(m)
                out["max_pct_gap"] = float(d.max())
                out["median_pct_gap"] = float(d.median())
                out["frac_within_0.5pt"] = float((d <= 0.5).mean())
                print(f"  tol {tol:.0e}  shared {len(m):4d}  "
                      f"max gap {d.max():9.4f} pts  "
                      f"median {d.median():9.6f}  "
                      f"within 0.5pt {100 * (d <= 0.5).mean():5.1f}%", flush=True)
            rows.append(out)
            pd.DataFrame(rows).to_csv(args.out, index=False)

    print(f"\n-> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
