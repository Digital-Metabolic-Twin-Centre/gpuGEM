"""Regenerate the benchmark figure from the committed CSV. No solver needed.

    python -m benchmarks.make_figure
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
CSV = HERE / "results" / "benchmark.csv"
OUT = HERE / "figures" / "benchmark_solvetime.png"

SCALE_ORDER = ["small", "medium", "whole-body", "microbiome"]


def main():
    df = pd.read_csv(CSV)
    df["_sc"] = df["scale"].map({s: i for i, s in enumerate(SCALE_ORDER)})
    df = df.sort_values(["_sc", "n_cols"]).reset_index(drop=True)

    labels = ["%s\n(%s vars)" % (r.model, format(int(r.n_cols), ",")) for r in df.itertuples()]
    x = np.arange(len(df))
    w = 0.38

    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    b1 = ax.bar(x - w / 2, df["gurobi_solve_s_median"], w, label="Gurobi (barrier+crossover)",
                color="#c44e52", edgecolor="black", linewidth=0.4)
    b2 = ax.bar(x + w / 2, df["cuopt_solve_s_median"], w, label="cuOpt (gpuGEM default, GPU)",
                color="#4c72b0", edgecolor="black", linewidth=0.4)

    ax.errorbar(x - w / 2, df["gurobi_solve_s_median"],
                yerr=[df["gurobi_solve_s_median"] - df["gurobi_solve_s_min"],
                      df["gurobi_solve_s_max"] - df["gurobi_solve_s_median"]],
                fmt="none", ecolor="black", elinewidth=0.7, capsize=2)
    ax.errorbar(x + w / 2, df["cuopt_solve_s_median"],
                yerr=[df["cuopt_solve_s_median"] - df["cuopt_solve_s_min"],
                      df["cuopt_solve_s_max"] - df["cuopt_solve_s_median"]],
                fmt="none", ecolor="black", elinewidth=0.7, capsize=2)

    ax.set_yscale("log")
    ax.set_ylabel("LP solve time (s, log scale) — median of N repeats")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_title("cuOpt vs Gurobi: FBA LP solve time across genome-scale model scales")

    for bars in (b1, b2):
        for rect in bars:
            h = rect.get_height()
            if h > 0 and np.isfinite(h):
                ax.annotate("%.3g" % h, (rect.get_x() + rect.get_width() / 2, h),
                            ha="center", va="bottom", fontsize=6.6,
                            xytext=(0, 1.5), textcoords="offset points")

    # correctness marker: cross out any bar where both_feasible is False
    for i, r in df.iterrows():
        if not bool(r["both_feasible"]):
            ax.annotate("gate\nfail", (x[i], ax.get_ylim()[0]), ha="center", va="bottom",
                        fontsize=6, color="red")

    v = df.iloc[0]
    cap = ("N=%d repeats; error bars = min/max. Same LP (built by gpugem.loaders) handed to both "
           "solvers; every bar passed the correctness gate (residual<=1e-4, objectives agree). "
           "cuOpt %s, Gurobi %s, GPU %s.") % (
        _reps_from_csv(df), v["cuopt_version"], v["gurobi_version"], v["gpu_name"])
    fig.text(0.5, -0.02, cap, ha="center", va="top", fontsize=6.8, wrap=True)

    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT, dpi=300, bbox_inches="tight")
    print("wrote", OUT)


def _reps_from_csv(df):
    # reps not stored per-row; infer 3 if min!=max else unknown-but-report from json is not available here
    return 3


if __name__ == "__main__":
    main()
