"""Regenerate the matlab_python_lifting_comparison figure from the committed
comparison.csv. No GPU/solver/MATLAB needed.

    python -m benchmarks.make_matlab_python_lifting_figure

See specs/015-matlab-python-lifting-comparison/ (Constitution Principle VI).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
CSV = HERE / "results" / "matlab_python_lifting" / "comparison.csv"
FIGURES = HERE / "figures"
OUT_PNG = FIGURES / "matlab_python_lifting_comparison.png"
OUT_PDF = FIGURES / "matlab_python_lifting_comparison.pdf"

PIPELINE_ORDER = ["matlab", "python"]
PIPELINE_LABEL = {"matlab": "MATLAB (reformulate.m + Gurobi)", "python": "Python (gpugem + Gurobi)"}
# Reused verbatim from make_residual_tradeoff_figures.py::CONFIG_COLOR -- already
# CVD-validated for this exact use (research.md R7).
PIPELINE_COLOR = {"matlab": "#4c72b0", "python": "#dd8452"}


def _load_models(df):
    models = df[["model", "n_cols"]].copy()
    models = models.sort_values("n_cols").reset_index(drop=True)
    return models


def main():
    FIGURES.mkdir(exist_ok=True)
    df = pd.read_csv(CSV)
    models = _load_models(df)
    df = df.set_index("model").reindex(models["model"]).reset_index()

    labels = ["%s\n(%s vars)" % (r.model, format(int(r.n_cols), ",")) for r in models.itertuples()]
    x = np.arange(len(models))
    w = 0.34

    fig, ax = plt.subplots(figsize=(max(8.0, 1.6 * len(models)), 5.0))
    value_col = {"matlab": "matlab_solve_s", "python": "python_solve_s"}
    for i, pipeline in enumerate(PIPELINE_ORDER):
        values = df[value_col[pipeline]].to_numpy(dtype=np.float64)
        offset = (i - 0.5) * w
        bars = ax.bar(x + offset, values, w, label=PIPELINE_LABEL[pipeline],
                       color=PIPELINE_COLOR[pipeline], edgecolor="black", linewidth=0.4)
        for rect, v in zip(bars, values):
            h = rect.get_height()
            if np.isfinite(h) and h > 0:
                ax.annotate("%.3g" % v, (rect.get_x() + rect.get_width() / 2, h),
                            ha="center", va="bottom", fontsize=6.4,
                            xytext=(0, 1.5), textcoords="offset points")

    all_values = df[["matlab_solve_s", "python_solve_s"]].to_numpy(dtype=np.float64)
    max_value = np.nanmax(all_values) if np.isfinite(all_values).any() else 1.0

    failed = ~df["verified_correct"].astype(bool)
    for j, is_failed in enumerate(failed):
        if is_failed:
            pair = df.loc[j, ["matlab_solve_s", "python_solve_s"]].to_numpy(dtype=np.float64)
            top = np.nanmax(pair)
            ax.annotate("disagreement\n(see comparison.csv)",
                        (x[j], top if np.isfinite(top) else 0.0),
                        ha="center", va="bottom", fontsize=6.0, color="#c44e52",
                        xytext=(0, 16), textcoords="offset points", fontweight="bold")

    ax.set_yscale("log")
    # Headroom above the tallest bar so the per-bar value labels and any
    # "disagreement" annotation never collide with the title (log scale, so
    # this is a multiplicative margin, not additive).
    ax.set_ylim(top=max_value * 30)
    ax.set_ylabel("Lift + Gurobi solve time (s, log scale)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_title("MATLAB (reformulate.m) vs Python (gpugem) lifted-model solve time")

    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=300, bbox_inches="tight")
    fig.savefig(OUT_PDF, bbox_inches="tight")
    print("wrote", OUT_PNG)
    print("wrote", OUT_PDF)


if __name__ == "__main__":
    main()
