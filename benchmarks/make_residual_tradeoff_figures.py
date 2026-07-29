"""Regenerate the residual-tradeoff figures from the committed comparison.csv.
No solver needed.

    python -m benchmarks.make_residual_tradeoff_figures
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
CSV = HERE / "results" / "residual_tradeoff" / "comparison.csv"
FIGURES = HERE / "figures"
VIOLATIONS_OUT = FIGURES / "residual_tradeoff_violations.png"
SOLVETIME_OUT = FIGURES / "residual_tradeoff_solvetime.png"

SCALE_ORDER = ["small", "medium", "whole-body", "microbiome"]
CONFIG_ORDER = ["shipped_default", "residual_0", "gurobi"]
CONFIG_LABEL = {
    "shipped_default": "cuOpt (gpugem shipped default)",
    "residual_0": "cuOpt (per_constraint_residual=0)",
    "gurobi": "Gurobi",
}
CONFIG_COLOR = {
    "shipped_default": "#4c72b0",
    "residual_0": "#dd8452",
    "gurobi": "#c44e52",
}

NON_RECOMMENDATION_NOTICE = (
    "per_constraint_residual=0 results are shown for comparison only; they are not validated "
    "for correctness and are not a recommended configuration."
)


def _load_models():
    df = pd.read_csv(CSV)
    models = df.drop_duplicates("model")[["model", "scale", "n_cols"]].copy()
    models["_sc"] = models["scale"].map({s: i for i, s in enumerate(SCALE_ORDER)})
    models = models.sort_values(["_sc", "n_cols"]).reset_index(drop=True)
    return df, models


def _floor_for_log(values, floor=None):
    """Floor non-positive/zero values for log-scale plotting only; the true
    (unmodified) value stays in the CSV and in per-bar annotations."""
    values = np.asarray(values, dtype=np.float64)
    positive = values[values > 0]
    floor = floor if floor is not None else (positive.min() / 10.0 if positive.size else 1e-12)
    return np.where(values > 0, values, floor), floor


def _bar_figure(df, models, value_col, ylabel, title, out_path, log_floor=None):
    labels = ["%s\n(%s vars)" % (r.model, format(int(r.n_cols), ",")) for r in models.itertuples()]
    x = np.arange(len(models))
    w = 0.26

    fig, ax = plt.subplots(figsize=(9.5, 5.0))
    bars_by_config = {}
    for i, config in enumerate(CONFIG_ORDER):
        sub = df[df["configuration"] == config].set_index("model").reindex(models["model"])
        raw = sub[value_col].to_numpy(dtype=np.float64)
        plotted, floor = _floor_for_log(raw, log_floor)
        offset = (i - 1) * w
        hatch = "///" if config == "residual_0" else None
        bars = ax.bar(x + offset, plotted, w, label=CONFIG_LABEL[config],
                       color=CONFIG_COLOR[config], edgecolor="black", linewidth=0.4,
                       hatch=hatch)
        bars_by_config[config] = (bars, raw)

    ax.set_yscale("log")
    ax.set_ylabel(ylabel)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_title(title)

    for config, (bars, raw) in bars_by_config.items():
        for rect, v in zip(bars, raw):
            h = rect.get_height()
            if np.isfinite(h) and h > 0:
                ax.annotate("%.3g" % v, (rect.get_x() + rect.get_width() / 2, h),
                            ha="center", va="bottom", fontsize=6.4,
                            xytext=(0, 1.5), textcoords="offset points")

    fig.text(0.5, -0.03, NON_RECOMMENDATION_NOTICE, ha="center", va="top",
              fontsize=7.2, wrap=True, style="italic")

    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    print("wrote", out_path)


def main():
    FIGURES.mkdir(exist_ok=True)
    df, models = _load_models()

    _bar_figure(
        df, models, value_col="residual_inf",
        ylabel="Worst-row constraint violation ||S v - b||_inf (log scale)",
        title="cuOpt shipped default vs per_constraint_residual=0 vs Gurobi: constraint violation",
        out_path=VIOLATIONS_OUT,
    )
    _bar_figure(
        df, models, value_col="solve_s",
        ylabel="LP solve time (s, log scale)",
        title="cuOpt shipped default vs per_constraint_residual=0 vs Gurobi: solve time",
        out_path=SOLVETIME_OUT,
    )


if __name__ == "__main__":
    main()
