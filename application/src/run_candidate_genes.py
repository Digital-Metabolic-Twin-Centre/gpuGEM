#!/usr/bin/env python3
"""
Rank candidate disease genes from a patient's biomarker pattern.

Examples
--------
Kynurenine pathway, GPU LP::

    python run_candidate_genes.py "C02470[bc],incr;kynate[bc],incr" \\
        --label kynurenic --out ../results/kynurenic_gpugem.csv

Phenylketonuria, CPU baseline for comparison::

    python run_candidate_genes.py "phe_L[bc],increased;tyr_L[bc],decreased" \\
        --backend gurobi --label pku --out ../results/pku_gurobi.csv

17-alpha-hydroxylase deficiency::

    python run_candidate_genes.py \\
        "k[bc],decreased;tststerone[bc],decreased;estradiol[bc],decreased" \\
        --label cyp17 --out ../results/cyp17_gpugem.csv
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cugem_app import data as dat  # noqa: E402
from cugem_app.pipeline import run_query  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "biomarkers",
        help='Semicolon-separated "metabolite,direction" tokens, e.g. '
             '"phe_L[bc],increased;tyr_L[bc],decreased". Directions accept '
             'incr/increased/up and decr/decreased/down.',
    )
    p.add_argument(
        "--backend", choices=["gpugem", "gurobi"], default="gpugem",
        help="LP solver for the biomarker-demand problem (default: gpugem). "
             "The minimum-norm QP uses Gurobi either way.",
    )
    p.add_argument("--label", default="patient", help="Label for this query.")
    p.add_argument("--out", default="results.csv", help="Output CSV path.")
    p.add_argument(
        "--data-dir", type=Path, default=dat.DEFAULT_DATA_DIR,
        help="Directory holding the Harvey .mat files (default: application/data).",
    )
    p.add_argument(
        "--wt-method", choices=["QP", "LP"], default="QP",
        help="Which precomputed wild-type solution to compare against.",
    )
    p.add_argument("--top", type=int, default=20, help="Rows to print (default: 20).")
    p.add_argument(
        "--timings-json", type=Path, default=None,
        help="Also write stage timings and solver settings to this JSON file.",
    )
    p.add_argument("--verbose", action="store_true", help="Show solver output.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    result = run_query(
        args.biomarkers,
        backend=args.backend,
        data_dir=args.data_dir,
        wt_method=args.wt_method,
        label=args.label,
        verbose=args.verbose,
    )

    print()
    print(result.summary())
    print()

    if result.ranking.empty:
        print("No candidate gene passed the flux-reduction filters.")
        return 1

    display = [
        "Disease", "Gene", "FluxReductionPercentage",
        "sumFluxWT", "sumFluxD", "NRxns", "Causal",
    ]
    print(f"top {min(args.top, len(result.ranking))} of {len(result.ranking)} candidates")
    print(result.ranking[display].head(args.top).to_string(index=False))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    result.ranking.to_csv(out, index=False)
    print(f"\nwrote {len(result.ranking)} rows to {out}")

    if args.timings_json:
        args.timings_json.parent.mkdir(parents=True, exist_ok=True)
        args.timings_json.write_text(json.dumps({
            "query": args.biomarkers,
            "label": args.label,
            "backend": result.backend,
            "objective": result.objective,
            "timings_s": result.timings,
            "solver_info": result.solver_info,
            "warnings": result.warnings,
            "n_candidates": len(result.ranking),
        }, indent=2, default=str))
        print(f"wrote timings to {args.timings_json}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
