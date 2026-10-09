#!/usr/bin/env python3
"""
Rank diseases against a patient's biomarkers using precomputed knockout
signatures.

This does no solving. It compares the requested biomarker directions against
the table built by precompute_knockouts.py, so it answers in milliseconds and
needs neither Gurobi nor a GPU.

Examples
--------
    python query_knockouts.py "phe_L[bc],increased;tyr_L[bc],decreased" --label PAH
    python query_knockouts.py "C02470[bc],incr;kynate[bc],incr" --top 20
    python query_knockouts.py --search phenylalanine
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cugem_app import data as dat  # noqa: E402
from cugem_app.knockouts import (  # noqa: E402
    DEFAULT_NAME_CACHE,
    DEFAULT_SIGNATURE_FILE,
    query_signatures,
    search_metabolites,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        "biomarkers", nargs="?",
        help='Biomarkers as "met[bc],incr;met[bc],decr".',
    )
    p.add_argument("--label", default="patient", help="Label for the output rows.")
    p.add_argument("--top", type=int, default=15, help="Rows to print (default: 15).")
    p.add_argument("--out", type=Path, help="Write the full ranking to this CSV.")
    p.add_argument(
        "--search", metavar="KEYWORD",
        help="Instead of ranking, list blood metabolites matching KEYWORD.",
    )
    p.add_argument(
        "--signatures", type=Path, default=DEFAULT_SIGNATURE_FILE,
        help="Signature .npz (default: application/data/knockout_signatures.npz).",
    )
    p.add_argument("--data-dir", type=Path, default=dat.DEFAULT_DATA_DIR)
    p.add_argument(
        "--include-essential", action="store_true",
        help="Keep genes whose knockout makes the model infeasible. They match "
             "any decrease and normally swamp the ranking.",
    )
    args = p.parse_args(argv)

    if args.search:
        hits = search_metabolites(args.search, args.signatures, DEFAULT_NAME_CACHE)
        if not hits:
            print(f"no blood metabolite matches {args.search!r}")
            return 1
        print(f"{len(hits)} match(es):")
        for met_id, name in hits:
            print(f"  {met_id:28s} {name}")
        return 0

    if not args.biomarkers:
        p.error("give biomarkers to rank, or --search to look up a metabolite id")

    ranking = query_signatures(
        args.biomarkers,
        patient_label=args.label,
        sig_file=args.signatures,
        data_dir=args.data_dir,
        exclude_infeasible=not args.include_essential,
    )

    if ranking.empty:
        print("no gene reproduces any of the requested biomarker directions")
        return 1

    cols = ["Disease", "Gene", "MatchScore", "MatchCount", "TotalBiomarkers"]
    print(f"\ntop {min(args.top, len(ranking))} of {len(ranking)} rows\n")
    print(ranking[cols].head(args.top).to_string(index=False))

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        ranking.to_csv(args.out, index=False)
        print(f"\nfull ranking -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
