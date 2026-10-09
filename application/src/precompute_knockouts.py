#!/usr/bin/env python3
"""
Precompute gene-knockout signatures for every candidate disease gene.

Run this once. It solves one aggregated linear programme per gene (roughly 450
solves, rather than one per gene-metabolite pair) and writes a table that
query_knockouts.py then reads with no solving at all.

Expect this to take a while: it is hundreds of whole-body LPs. It needs Gurobi
but not a GPU, for the reason given in cugem_app/knockouts.py.

Examples
--------
    python precompute_knockouts.py                 # 2 workers
    python precompute_knockouts.py --workers 1     # single process
    python precompute_knockouts.py --workers 4     # if your licence allows
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cugem_app import data as dat  # noqa: E402
from cugem_app.knockouts import (  # noqa: E402
    DEFAULT_SIGNATURE_FILE,
    precompute_signatures,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        "--workers", type=int, default=2,
        help="Parallel worker processes (default: 2). Each holds its own Gurobi "
             "environment, so keep this within your licence's concurrency limit.",
    )
    p.add_argument(
        "--data-dir", type=Path, default=dat.DEFAULT_DATA_DIR,
        help="Directory holding the Harvey .mat files (default: application/data).",
    )
    p.add_argument(
        "--out", type=Path, default=DEFAULT_SIGNATURE_FILE,
        help="Output .npz path (default: application/data/knockout_signatures.npz).",
    )
    args = p.parse_args(argv)

    if args.workers < 1:
        p.error("--workers must be at least 1")

    t0 = time.time()
    out = precompute_signatures(
        data_dir=args.data_dir, out_file=args.out, n_workers=args.workers
    )
    print(f"done in {(time.time() - t0) / 60:.1f} min -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
