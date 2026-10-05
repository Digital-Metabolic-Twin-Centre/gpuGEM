"""Extend the residual-tradeoff violation/solve-time figures with a fourth
configuration, HiGHS, alongside the three already there (cuOpt shipped
default, cuOpt per_constraint_residual=0, Gurobi). No solver needed -- reads
already-committed results only:

    benchmarks/results/residual_tradeoff/comparison.csv         -- existing 3 configs
    benchmarks/results/highs_baseline/highs_baseline.json       -- HiGHS

Writes to NEW filenames (does not overwrite residual_tradeoff_violations.png/
residual_tradeoff_solvetime.png or touch make_residual_tradeoff_figures.py/
comparison.csv) -- those remain the committed record of the original
three-configuration investigation; this is a derived, four-configuration view
built on top of it.

    python -m benchmarks.make_residual_tradeoff_figures_with_highs
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
CSV = HERE / "results" / "residual_tradeoff" / "comparison.csv"
HIGHS_JSON = HERE / "results" / "highs_baseline" / "highs_baseline.json"
FIGURES = HERE / "figures"
VIOLATIONS_OUT = FIGURES / "residual_tradeoff_violations_with_highs.png"
SOLVETIME_OUT = FIGURES / "residual_tradeoff_solvetime_with_highs.png"

SCALE_ORDER = ["small", "medium", "whole-body", "microbiome"]
CONFIG_ORDER = ["shipped_default", "residual_0", "gurobi", "highs"]
CONFIG_LABEL = {
    "shipped_default": "cuOpt (gpugem shipped default)",
    "residual_0": "cuOpt (per_constraint_residual=0)",
    "gurobi": "Gurobi",
    "highs": "HiGHS",
}
# shipped_default/residual_0/gurobi reused verbatim from
# make_residual_tradeoff_figures.py; highs is the same green already
# validated together with this project's red/blue in
# make_presentation_solvetime_figure.py. Validated together (all 4, light
# mode) via the dataviz skill's validate_palette.py: all checks pass.
CONFIG_COLOR = {
    "shipped_default": "#4c72b0",
    "residual_0": "#dd8452",
    "gurobi": "#c44e52",
    "highs": "#55a868",
}

NON_RECOMMENDATION_NOTICE = (
    "per_constraint_residual=0 results are shown for comparison only; they are not validated "
    "for correctness and are not a recommended configuration."
)


def _load_data():
    df = pd.read_csv(CSV)
    highs = json.loads(HIGHS_JSON.read_text())["results"]

    model_scale = df.drop_duplicates("model").set_index("model")[["scale", "n_cols"]]
    highs_rows = []
    for r in highs:
        model = r["model"]
        if model not in model_scale.index:
            continue  # only add HiGHS for models already in this comparison
        highs_rows.append({
            "model": model,
            "scale": model_scale.loc[model, "scale"],
            "n_cols": model_scale.loc[model, "n_cols"],
            "configuration": "highs",
            "solve_s": r["solve_s"],
            "residual_inf": r["residual_inf"],
        })
    return pd.concat([df, pd.DataFrame(highs_rows)], ignore_index=True)


def _load_models(df):
    models = df.drop_duplicates("model")[["model", "scale", "n_cols"]].copy()
    models["_sc"] = models["scale"].map({s: i for i, s in enumerate(SCALE_ORDER)})
    models = models.sort_values(["_sc", "n_cols"]).reset_index(drop=True)
    return models


def _floor_for_log(values, floor=None):
    values = np.asarray(values, dtype=np.float64)
    positive = values[values > 0]
    floor = floor if floor is not None else (positive.min() / 10.0 if positive.size else 1e-12)
    return np.where(values > 0, values, floor), floor


def _bar_figure(df, models, value_col, ylabel, title, out_path, log_floor=None):
    labels = ["%s\n(%s vars)" % (r.model, format(int(r.n_cols), ",")) for r in models.itertuples()]
    x = np.arange(len(models))
    n_configs = len(CONFIG_ORDER)
    w = 0.8 / n_configs

    plt.rcParams.update({"font.size": 20})
    fig, ax = plt.subplots(figsize=(max(20.0, 3.1 * len(models)), 11.5))
    bars_by_config = {}
    for i, config in enumerate(CONFIG_ORDER):
        sub = df[df["configuration"] == config].set_index("model").reindex(models["model"])
        raw = sub[value_col].to_numpy(dtype=np.float64)
        plotted, floor = _floor_for_log(raw, log_floor)
        offset = (i - (n_configs - 1) / 2) * w
        hatch = "///" if config == "residual_0" else None
        bars = ax.bar(x + offset, plotted, w, label=CONFIG_LABEL[config],
                       color=CONFIG_COLOR[config], edgecolor="black", linewidth=0.8,
                       hatch=hatch)
        bars_by_config[config] = (bars, raw)

    ax.set_yscale("log")
    ax.set_ylabel(ylabel, fontsize=26, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=18)
    ax.tick_params(axis="y", labelsize=20)
    ax.set_title(title, fontsize=28, fontweight="bold", pad=22)
    ax.grid(axis="y", which="major", alpha=0.25, linewidth=1.0)

    # rotated 90deg so 4 labels per model group stay legible without colliding
    # horizontally at the larger font size (unlike the compact non-presentation figure)
    for config, (bars, raw) in bars_by_config.items():
        for rect, v in zip(bars, raw):
            h = rect.get_height()
            if np.isfinite(h) and h > 0:
                ax.annotate("%.3g" % v, (rect.get_x() + rect.get_width() / 2, h),
                            ha="left", va="bottom", fontsize=13, fontweight="bold",
                            rotation=90, xytext=(0, 4), textcoords="offset points")

    ax.margins(y=0.18)
    fig.text(0.5, -0.02, NON_RECOMMENDATION_NOTICE, ha="center", va="top",
              fontsize=15, wrap=True, style="italic")

    ax.legend(frameon=False, fontsize=22, loc="upper left", ncol=2)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    print("wrote", out_path)


def main():
    FIGURES.mkdir(exist_ok=True)
    df = _load_data()
    models = _load_models(df)

    _bar_figure(
        df, models, value_col="residual_inf",
        ylabel="Worst-row constraint violation ||S v - b||_inf (log scale)",
        title="cuOpt shipped default vs per_constraint_residual=0 vs Gurobi vs HiGHS: "
              "constraint violation",
        out_path=VIOLATIONS_OUT,
    )
    _bar_figure(
        df, models, value_col="solve_s",
        ylabel="LP solve time (s, log scale)",
        title="cuOpt shipped default vs per_constraint_residual=0 vs Gurobi vs HiGHS: solve time",
        out_path=SOLVETIME_OUT,
    )


if __name__ == "__main__":
    from benchmarks._deps import run_main
    run_main(main)
