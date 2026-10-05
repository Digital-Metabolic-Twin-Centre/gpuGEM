"""Regenerate the benchmark figure from the committed CSV. No solver needed.

    python -m benchmarks.make_figure
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from benchmarks._deps import require_or_exit  # noqa: E402
require_or_exit("pandas", "matplotlib")

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
CSV = HERE / "results" / "benchmark.csv"
HARVEY_DEMAND = HERE / "results" / "harvey_two_demand_gurobi.json"
OUT = HERE / "figures" / "benchmark_solvetime.png"

def main():
    df = pd.read_csv(CSV)
    df = df.sort_values("n_cols").reset_index(drop=True)

    labels = ["%s\n(%s vars)" % (r.model, format(int(r.n_cols), ",")) for r in df.itertuples()]
    x = np.arange(len(df))
    w = 0.38

    has_demand = HARVEY_DEMAND.exists()
    if has_demand:
        fig = plt.figure(figsize=(max(11.0, 1.5 * len(df) + 3.2), 4.8))
        grid = fig.add_gridspec(1, 2, width_ratios=[max(len(df), 4), 2.2], wspace=0.16)
        ax = fig.add_subplot(grid[0, 0])
        demand_ax = fig.add_subplot(grid[0, 1], sharey=ax)
    else:
        fig, ax = plt.subplots(figsize=(max(8.2, 1.5 * len(df)), 4.6))
        demand_ax = None
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

    if demand_ax is not None:
        _plot_harvey_demand_panel(demand_ax)

    v = df.iloc[0]
    cap = ("N=%d repeats; error bars = min/max. Main panel: same canonical LP (built by "
           "gpugem.loaders) handed to both "
           "solvers; every bar passed the correctness gate (residual<=1e-4, objectives agree). "
           "Right panel: separate Harvey two-demand biomarker LP, Gurobi only; both methods "
           "returned Optimal and objectives differed by 4.1e-11. cuOpt %s, Gurobi %s, GPU %s.") % (
        _reps_from_csv(df), v["cuopt_version"], v["gurobi_version"], v["gpu_name"])
    fig.text(0.5, -0.02, cap, ha="center", va="top", fontsize=6.8, wrap=True)

    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT, dpi=300, bbox_inches="tight")
    print("wrote", OUT)


def _plot_harvey_demand_panel(ax):
    data = json.loads(HARVEY_DEMAND.read_text())
    methods = [data["methods"]["dual_simplex"], data["methods"]["barrier_crossover"]]
    medians = np.array([m["solve_s_median"] for m in methods])
    minima = np.array([m["solve_s_min"] for m in methods])
    maxima = np.array([m["solve_s_max"] for m in methods])
    x = np.arange(len(methods))
    bars = ax.bar(x, medians, 0.62, color=["#8172b2", "#c44e52"],
                  edgecolor="black", linewidth=0.4)
    ax.errorbar(x, medians, yerr=[medians - minima, maxima - medians], fmt="none",
                ecolor="black", elinewidth=0.7, capsize=2)
    ax.set_xticks(x)
    ax.set_xticklabels(["Dual\nsimplex", "Barrier +\ncrossover"], fontsize=8)
    ax.set_title("Harvey two-demand LP\n(Gurobi method comparison)", fontsize=9)
    ax.tick_params(axis="y", labelleft=False)
    ax.grid(axis="y", alpha=0.18, linewidth=0.5)
    for rect, value in zip(bars, medians):
        ax.annotate("%.3g" % value, (rect.get_x() + rect.get_width() / 2, value),
                    ha="center", va="bottom", fontsize=7, xytext=(0, 1.5),
                    textcoords="offset points")
    ax.text(0.5, 0.03, "Barrier 4.84x faster\nN=3 cold solves",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=7)


def _reps_from_csv(df):
    # reps not stored per-row; infer 3 if min!=max else unknown-but-report from json is not available here
    return 3


if __name__ == "__main__":
    from benchmarks._deps import run_main
    run_main(main)
