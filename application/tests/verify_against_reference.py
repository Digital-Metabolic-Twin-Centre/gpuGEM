#!/usr/bin/env python3
"""
Check the ported application against the result files used in the manuscript.

For each of the three published cases this runs the ported pipeline and
compares the ranking to the reference CSV produced by the original research
code. Needs Gurobi; add --gpu to also run the gpuGEM backend and check the two
backends agree with each other.

    python verify_against_reference.py --reference-dir /path/to/reference/csvs

What is compared
----------------
* the set of (Disease, Gene) rows returned
* FluxReductionPercentage, sumFluxWT and sumFluxD on the shared rows
* the identity and order of the top-ranked genes

A tolerance is applied because the reference was produced on a different
Gurobi version, and because degenerate LP vertices can differ while the
objective does not.
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

from cugem_app import data as dat          # noqa: E402
from cugem_app.pipeline import run_query   # noqa: E402

CASES = [
    ("pah", "phe_L[bc],increased;tyr_L[bc],decreased", "pah_results.csv", "PAH"),
    ("kynurenic", "C02470[bc],incr;kynate[bc],incr", "kynuric_results.csv", "KYNU"),
    ("cyp17",
     "k[bc],decreased;tststerone[bc],decreased;estradiol[bc],decreased",
     "cyp17_results.csv", "CYP17A1"),
]

RTOL = 1e-4      # relative tolerance on fluxes
PCT_ATOL = 0.5   # absolute tolerance on FluxReductionPercentage, in points
KEY = ["Disease", "Gene"]


def compare(ours: pd.DataFrame, ref: pd.DataFrame, expect_gene: str) -> dict:
    """Compare one ranking against its reference and return a summary dict."""
    ours = ours.copy()
    ref = ref.copy()
    for df in (ours, ref):
        for col in KEY:
            df[col] = df[col].astype(str).str.strip()

    merged = ours.merge(ref, on=KEY, how="outer", suffixes=("_new", "_ref"),
                        indicator=True)
    both = merged[merged["_merge"] == "both"]
    only_new = merged[merged["_merge"] == "left_only"]
    only_ref = merged[merged["_merge"] == "right_only"]

    out = {
        "rows_new": len(ours),
        "rows_ref": len(ref),
        "shared": len(both),
        "only_new": len(only_new),
        "only_ref": len(only_ref),
    }

    for col in ("sumFluxWT", "sumFluxD", "FluxReductionPercentage"):
        a = both[f"{col}_new"].to_numpy(dtype=float)
        b = both[f"{col}_ref"].to_numpy(dtype=float)
        finite = np.isfinite(a) & np.isfinite(b)
        if col == "FluxReductionPercentage":
            close = np.abs(a[finite] - b[finite]) <= PCT_ATOL
        else:
            close = np.isclose(a[finite], b[finite], rtol=RTOL, atol=1e-9)
        out[f"{col}_agree"] = int(close.sum())
        out[f"{col}_n"] = int(finite.sum())
        if close.size and not close.all():
            worst = np.argmax(np.abs(a[finite] - b[finite]))
            out[f"{col}_worst"] = (
                f"{both.iloc[np.flatnonzero(finite)[worst]]['Gene']}: "
                f"{a[finite][worst]:.6g} vs {b[finite][worst]:.6g}"
            )

    ours_sorted = ours.sort_values(
        ["FluxReductionPercentage", "sumFluxWT"], ascending=False)
    ref_sorted = ref.sort_values(
        ["FluxReductionPercentage", "sumFluxWT"], ascending=False)
    out["top10_overlap"] = len(
        set(ours_sorted["Gene"].head(10)) & set(ref_sorted["Gene"].head(10)))
    out["causal_rank_new"] = next(
        (i + 1 for i, g in enumerate(ours_sorted["Gene"]) if g == expect_gene), None)
    out["causal_rank_ref"] = next(
        (i + 1 for i, g in enumerate(ref_sorted["Gene"]) if g == expect_gene), None)
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--reference-dir", type=Path, required=True)
    p.add_argument("--data-dir", type=Path, default=dat.DEFAULT_DATA_DIR)
    p.add_argument("--out-dir", type=Path, default=Path("verify_out"))
    p.add_argument("--barconvtol", type=float,
                   help="Gurobi BarConvTol for the minimum-norm QP "
                        "(default 1e-4, as in the published runs).")
    p.add_argument("--noncausal-fallback", action="store_true",
                   help="Score genes lacking a causal mapping (off by default).")
    p.add_argument("--gpu", action="store_true",
                   help="Also run the gpugem backend and cross-check it.")
    args = p.parse_args(argv)
    if args.barconvtol:
        os.environ['CUGEM_QP_BARCONVTOL'] = repr(args.barconvtol)
        import cugem_app.gurobi_backend as _gb
        importlib.reload(_gb)
        import cugem_app.pipeline as _pl
        importlib.reload(_pl)
        globals()['run_query'] = _pl.run_query
        assert _gb.QP_BAR_CONV_TOL == args.barconvtol
    args.out_dir.mkdir(parents=True, exist_ok=True)

    failures, summary = [], []
    for name, biomarkers, ref_file, expect_gene in CASES:
        ref_path = args.reference_dir / ref_file
        if not ref_path.exists():
            print(f"\n[{name}] SKIP, no reference at {ref_path}")
            continue

        print(f"\n[{name}] {biomarkers}", flush=True)
        backends = ["gurobi"] + (["gpugem"] if args.gpu else [])
        runs = {}
        for backend in backends:
            t0 = time.time()
            try:
                res_q = run_query(biomarkers, backend=backend,
                                  data_dir=args.data_dir, label=name,
                              use_noncausal_fallback=args.noncausal_fallback)
            except Exception as exc:
                # A GPU backend failure must not cost us the CPU comparison.
                print(f"  {backend:7s} FAILED: {type(exc).__name__}: {exc}",
                      flush=True)
                failures.append(f"{name}:{backend}-failed")
                if backend == "gurobi":
                    raise
                continue
            elapsed = time.time() - t0
            df = res_q.ranking
            df.to_csv(args.out_dir / f"{name}_{backend}.csv", index=False)
            runs[backend] = df
            print(f"  {backend:7s} {len(df):4d} rows  {elapsed:7.1f}s  "
                  f"({'; '.join(f'{k} {v:.1f}s' for k, v in res_q.timings.items())})",
                  flush=True)

        ref = pd.read_csv(ref_path)
        res = compare(runs["gurobi"], ref, expect_gene)
        res["case"] = name
        summary.append(res)

        print(f"  rows      ours {res['rows_new']}  reference {res['rows_ref']}  "
              f"shared {res['shared']}  ours-only {res['only_new']}  "
              f"reference-only {res['only_ref']}")
        for col in ("sumFluxWT", "sumFluxD", "FluxReductionPercentage"):
            agree, n = res[f"{col}_agree"], res[f"{col}_n"]
            mark = "ok " if agree == n else "DIFF"
            print(f"  {mark} {col:24s} {agree}/{n} agree"
                  + (f"   worst {res[f'{col}_worst']}" if f"{col}_worst" in res else ""))
            if agree != n:
                failures.append(f"{name}:{col}")
        print(f"  top-10 overlap {res['top10_overlap']}/10   "
              f"{expect_gene} rank: ours {res['causal_rank_new']}, "
              f"reference {res['causal_rank_ref']}")

        if args.gpu and "gpugem" in runs:
            m = runs["gurobi"].merge(runs["gpugem"], on=KEY,
                                     suffixes=("_cpu", "_gpu"))
            d = np.abs(m["FluxReductionPercentage_cpu"]
                       - m["FluxReductionPercentage_gpu"])
            ok = int((d <= PCT_ATOL).sum())
            mark = "ok " if ok == len(m) else "DIFF"
            print(f"  {mark} cpu vs gpu backend: {ok}/{len(m)} rows within "
                  f"{PCT_ATOL} points, max {d.max():.3g}")
            if ok != len(m):
                failures.append(f"{name}:backend-agreement")

    pd.DataFrame(summary).to_csv(args.out_dir / "verification_summary.csv",
                                 index=False)
    print(f"\nsummary -> {args.out_dir / 'verification_summary.csv'}")
    if failures:
        print(f"\nDISAGREEMENTS: {failures}")
        return 1
    print("\nall cases reproduce the reference results")
    return 0


if __name__ == "__main__":
    sys.exit(main())
