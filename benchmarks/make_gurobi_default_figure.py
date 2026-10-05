"""Regenerate the gurobi_default_comparison figure from the committed
comparison.csv. No solver needed.

    python -m benchmarks.make_gurobi_default_figure
"""
from __future__ import annotations

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
CSV = HERE / "results" / "gurobi_default" / "comparison.csv"
FIGURES = HERE / "figures"
OUT = FIGURES / "gurobi_default_comparison.png"

SCALE_ORDER = ["small", "medium", "whole-body", "microbiome"]
CONFIG_ORDER = ["cuopt", "gurobi_barrier", "gurobi_default"]
CONFIG_LABEL = {
    "cuopt": "cuOpt",
    "gurobi_barrier": "Gurobi (barrier)",
    "gurobi_default": "Gurobi (default settings)",
}
# Reused verbatim from make_residual_tradeoff_figures.py::CONFIG_COLOR -- already
# CVD-validated for this exact use (research R5).
CONFIG_COLOR = {
    "cuopt": "#4c72b0",
    "gurobi_barrier": "#dd8452",
    "gurobi_default": "#c44e52",
}


def _load_models(df):
    models = df[["model", "scale", "n_cols"]].copy()
    models["_sc"] = models["scale"].map({s: i for i, s in enumerate(SCALE_ORDER)})
    models = models.sort_values(["_sc", "n_cols"]).reset_index(drop=True)
    return models


def main():
    FIGURES.mkdir(exist_ok=True)
    df = pd.read_csv(CSV)
    models = _load_models(df)
    df = df.set_index("model").reindex(models["model"]).reset_index()

    labels = ["%s\n(%s vars)" % (r.model, format(int(r.n_cols), ",")) for r in models.itertuples()]
    x = np.arange(len(models))
    w = 0.26

    fig, ax = plt.subplots(figsize=(max(9.5, 1.5 * len(models)), 5.0))
    value_col = {
        "cuopt": "cuopt_solve_s",
        "gurobi_barrier": "gurobi_barrier_solve_s",
        "gurobi_default": "gurobi_default_solve_s",
    }
    for i, config in enumerate(CONFIG_ORDER):
        values = df[value_col[config]].to_numpy(dtype=np.float64)
        offset = (i - 1) * w
        bars = ax.bar(x + offset, values, w, label=CONFIG_LABEL[config],
                       color=CONFIG_COLOR[config], edgecolor="black", linewidth=0.4)
        for rect, v in zip(bars, values):
            h = rect.get_height()
            if np.isfinite(h) and h > 0:
                ax.annotate("%.3g" % v, (rect.get_x() + rect.get_width() / 2, h),
                            ha="center", va="bottom", fontsize=6.4,
                            xytext=(0, 1.5), textcoords="offset points")

        if config == "gurobi_default":
            failed = ~df["both_feasible"].astype(bool)
            for rect, is_failed in zip(bars, failed):
                if is_failed:
                    ax.annotate("FAILED\ncorrectness gate",
                                (rect.get_x() + rect.get_width() / 2, rect.get_height()),
                                ha="center", va="bottom", fontsize=6.0, color="#c44e52",
                                xytext=(0, 10), textcoords="offset points", fontweight="bold")

    ax.set_yscale("log")
    ax.set_ylabel("LP solve time (s, log scale)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_title("cuOpt vs Gurobi (barrier) vs Gurobi (default settings): solve time")

    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT, dpi=300, bbox_inches="tight")
    print("wrote", OUT)


if __name__ == "__main__":
    from benchmarks._deps import run_main
    run_main(main)
