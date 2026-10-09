#!/usr/bin/env python
"""Gene-level comparison of candidate rankings produced by the two LP engines.

The pipeline emits one row per disease-gene pair: a gene that is causal for
several inborn errors appears once per disease.  A claim about "the top N
candidate genes" is therefore not a claim about the first N rows.  This script
reduces each ranking to one row per gene, keeping that gene's best-scoring
disease entry, and reports the agreement between the two engines at gene level.

It regenerates Supplementary Table S10 of the manuscript.

Usage
-----
    python compare_rankings.py --results-dir <dir> --out-dir <dir>

``--results-dir`` holds ``<case>_<backend>.csv`` files as written by
``verify_against_reference.py``; backends are ``gurobi`` and ``gpugem``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

# Ranking key, in the order the pipeline sorts by.
SORT_KEYS = ["FluxReductionPercentage", "sumFluxWT"]

# Columns that identify and score a candidate.  IEMRxns is excluded: it holds a
# long reaction list and is not needed for the comparison.
KEEP = ["Disease", "Gene", "FluxReductionPercentage", "sumFluxWT", "sumFluxD",
        "Causal", "CompositeScore"]

CASE_LABELS = {
    "pah": "PAH deficiency",
    "kynurenic": "Kynureninase deficiency",
    "cyp17": "CYP17A1 deficiency",
}
CAUSAL_GENE = {"pah": "PAH", "kynurenic": "KYNU", "cyp17": "CYP17A1"}


def load_gene_ranking(path: Path) -> pd.DataFrame:
    """Read a results CSV and reduce it to one ranked row per gene.

    Exact duplicate rows are dropped first; the raw output of every case
    contains one.  Genes are then ranked by the pipeline's sort order and
    reduced to their best-scoring disease entry.
    """
    df = pd.read_csv(path)
    missing = [c for c in KEEP if c not in df.columns]
    if missing:
        raise ValueError(f"{path.name} is missing columns: {missing}")
    df = df[KEEP].drop_duplicates()
    df["Gene"] = df["Gene"].astype(str).str.strip()
    ranked = (
        df.sort_values(SORT_KEYS, ascending=False)
          .drop_duplicates("Gene", keep="first")
          .reset_index(drop=True)
    )
    ranked["rank"] = np.arange(1, len(ranked) + 1)
    return ranked


def compare(cpu: pd.DataFrame, gpu: pd.DataFrame) -> dict:
    """Agreement statistics between two gene-level rankings."""
    merged = cpu.merge(gpu, on="Gene", suffixes=("_cpu", "_gpu"))
    if len(merged) > min(len(cpu), len(gpu)):      # guards against key blow-up
        raise AssertionError("merge inflated the row count; duplicate genes remain")
    rho, pval = spearmanr(merged["rank_cpu"], merged["rank_gpu"])

    def prefix_depth(same_order: bool) -> int:
        depth = 0
        for k in range(1, min(len(cpu), len(gpu)) + 1):
            a, b = list(cpu.head(k)["Gene"]), list(gpu.head(k)["Gene"])
            if (a == b) if same_order else (set(a) == set(b)):
                depth = k
        return depth

    return {
        "n_cpu": len(cpu),
        "n_gpu": len(gpu),
        "n_shared": len(merged),
        "spearman_rho": round(float(rho), 3),
        "spearman_p": float(pval),
        "top10_overlap": len(set(cpu.head(10)["Gene"]) & set(gpu.head(10)["Gene"])),
        "top20_overlap": len(set(cpu.head(20)["Gene"]) & set(gpu.head(20)["Gene"])),
        "deepest_identical_set": prefix_depth(same_order=False),
        "deepest_identical_order": prefix_depth(same_order=True),
    }


def rank_of(ranking: pd.DataFrame, gene: str):
    hit = ranking.index[ranking["Gene"] == gene]
    return int(ranking.loc[hit[0], "rank"]) if len(hit) else None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--results-dir", type=Path, required=True,
                   help="Directory of <case>_<backend>.csv result files.")
    p.add_argument("--out-dir", type=Path, default=Path("."),
                   help="Where to write the table and summary CSVs.")
    p.add_argument("--cases", nargs="+", default=list(CASE_LABELS),
                   help="Cases to compare.")
    p.add_argument("--top", type=int, default=10,
                   help="Number of top genes to tabulate per case.")
    args = p.parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    table_rows, summary_rows = [], []
    for case in args.cases:
        paths = {b: args.results_dir / f"{case}_{b}.csv" for b in ("gurobi", "gpugem")}
        for b, path in paths.items():
            if not path.exists():
                print(f"missing: {path}", file=sys.stderr)
                return 1
        cpu, gpu = (load_gene_ranking(paths["gurobi"]), load_gene_ranking(paths["gpugem"]))

        stats = compare(cpu, gpu)
        stats.update(
            case=case,
            query=CASE_LABELS.get(case, case),
            causal_gene=CAUSAL_GENE.get(case),
            causal_rank_gurobi=rank_of(cpu, CAUSAL_GENE.get(case, "")),
            causal_rank_gpugem=rank_of(gpu, CAUSAL_GENE.get(case, "")),
        )
        summary_rows.append(stats)

        gpu_lookup = gpu.set_index("Gene")[["rank", "FluxReductionPercentage"]]
        for _, row in cpu.head(args.top).iterrows():
            hit = gpu_lookup.loc[row["Gene"]] if row["Gene"] in gpu_lookup.index else None
            table_rows.append({
                "Query": CASE_LABELS.get(case, case),
                "Gene": row["Gene"],
                "Rank_gurobi": int(row["rank"]),
                "FluxReduction_gurobi": round(row["FluxReductionPercentage"], 2),
                "Rank_gpugem": int(hit["rank"]) if hit is not None else None,
                "FluxReduction_gpugem": round(hit["FluxReductionPercentage"], 2) if hit is not None else None,
            })

    table = pd.DataFrame(table_rows)
    summary = pd.DataFrame(summary_rows)[
        ["case", "query", "n_cpu", "n_gpu", "n_shared", "spearman_rho", "spearman_p",
         "top10_overlap", "top20_overlap", "deepest_identical_set",
         "deepest_identical_order", "causal_gene", "causal_rank_gurobi",
         "causal_rank_gpugem"]
    ]
    table.to_csv(args.out_dir / "tableS10_ranking.csv", index=False)
    summary.to_csv(args.out_dir / "tableS10_summary.csv", index=False)

    print(table.to_string(index=False))
    print()
    print(summary.drop(columns=["spearman_p"]).to_string(index=False))
    print(f"\nwritten to {args.out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
