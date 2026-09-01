"""Presentation-sized runtime comparison: Gurobi vs cuOpt vs HiGHS, across all
ten benchmark models, from already-committed results only (no solver needed).

Large fonts throughout -- built for a slide/projector, not a print column;
see benchmarks/make_figure.py for the publication-track (Constitution
Principle VI-compliant) version of the cuOpt/Gurobi comparison.

Data sources (already saved, never re-solved here):
    benchmarks/results/benchmark.csv                        -- Gurobi, cuOpt
    benchmarks/results/highs_baseline/highs_baseline.json    -- HiGHS

    python -m benchmarks.make_presentation_solvetime_figure
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
BENCHMARK_CSV = HERE / "results" / "benchmark.csv"
HIGHS_JSON = HERE / "results" / "highs_baseline" / "highs_baseline.json"
OUT = HERE / "figures" / "presentation_solvetime_comparison.png"

CONFIG_ORDER = ["gurobi", "cuopt", "highs"]
CONFIG_LABEL = {"gurobi": "Gurobi", "cuopt": "cuOpt", "highs": "HiGHS"}
# Validated together via the dataviz skill's validate_palette.py (light mode):
# all checks pass. Gurobi/cuOpt reuse this project's established colors
# (make_figure.py); HiGHS is the third seaborn-deep-family hue.
CONFIG_COLOR = {"gurobi": "#c44e52", "cuopt": "#4c72b0", "highs": "#55a868"}

OBJ_TOL = 1e-6


def _fmt(v: float) -> str:
    """Presentation-friendly number format -- never scientific notation, so a
    value like 2320 reads as "2,320" instead of "2.32e+03" from a distance."""
    if v >= 100:
        return "{:,.0f}".format(v)
    if v >= 1:
        return "{:.1f}".format(v)
    return "{:.3g}".format(v)


def load_data():
    df = pd.read_csv(BENCHMARK_CSV)
    highs = json.loads(HIGHS_JSON.read_text())["results"]
    highs_by_model = {r["model"]: r for r in highs}

    rows = []
    for _, r in df.iterrows():
        model = r["model"]
        h = highs_by_model.get(model)
        highs_solve_s = h["solve_s"] if h else None
        highs_ok = None
        if h is not None:
            gobj = r["gurobi_obj"]
            hobj = h["objective"]
            agree = abs(gobj - hobj) / max(1.0, abs(gobj), abs(hobj)) <= OBJ_TOL
            highs_ok = bool(h["status"] == "kOptimal" and agree)
        rows.append({
            "model": model, "n_cols": r["n_cols"],
            "gurobi_solve_s": r["gurobi_solve_s_median"],
            "cuopt_solve_s": r["cuopt_solve_s_median"],
            "cuopt_ok": bool(r["both_feasible"]),
            "highs_solve_s": highs_solve_s,
            "highs_ok": highs_ok,
        })
    out = pd.DataFrame(rows).sort_values("n_cols").reset_index(drop=True)
    return out


def main():
    df = load_data()
    labels = ["%s\n(%s vars)" % (r.model, format(int(r.n_cols), ",")) for r in df.itertuples()]
    x = np.arange(len(df))
    n_configs = len(CONFIG_ORDER)
    w = 0.8 / n_configs

    plt.rcParams.update({"font.size": 20})
    fig, ax = plt.subplots(figsize=(26.0, 13.0))

    value_col = {"gurobi": "gurobi_solve_s", "cuopt": "cuopt_solve_s", "highs": "highs_solve_s"}
    ok_col = {"cuopt": "cuopt_ok", "highs": "highs_ok"}

    for i, config in enumerate(CONFIG_ORDER):
        values = df[value_col[config]].to_numpy(dtype=np.float64)
        present = np.isfinite(values)
        if not present.any():
            continue
        offset = (i - (n_configs - 1) / 2) * w
        bars = ax.bar(x[present] + offset, values[present], w, label=CONFIG_LABEL[config],
                       color=CONFIG_COLOR[config], edgecolor="black", linewidth=0.8)
        for rect, v in zip(bars, values[present]):
            h = rect.get_height()
            ax.annotate(_fmt(v), (rect.get_x() + rect.get_width() / 2, h),
                        ha="center", va="bottom", fontsize=15, fontweight="bold",
                        xytext=(0, 3), textcoords="offset points")

        if config in ok_col:
            ok = df[ok_col[config]].to_numpy()
            idx_present = np.where(present)[0]
            for rect, row_idx in zip(bars, idx_present):
                if ok[row_idx] is False:
                    ax.annotate("FAILED", (rect.get_x() + rect.get_width() / 2, rect.get_height()),
                                ha="center", va="bottom", fontsize=15, color="#c44e52",
                                xytext=(0, 24), textcoords="offset points", fontweight="bold")

    ax.set_yscale("log")
    ax.set_ylabel("LP solve time (s, log scale)", fontsize=26, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=19)
    ax.tick_params(axis="y", labelsize=20)
    ax.set_title("Solve time across genome-scale models: Gurobi vs cuOpt vs HiGHS",
                 fontsize=30, fontweight="bold", pad=22)
    ax.grid(axis="y", which="major", alpha=0.25, linewidth=1.0)

    ax.legend(frameon=False, fontsize=24, loc="upper left", ncol=3)
    fig.tight_layout()
    fig.savefig(OUT, dpi=200, bbox_inches="tight")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
