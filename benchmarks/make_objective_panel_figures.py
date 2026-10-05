"""Regenerate the objective-panel figures (one per model) from the committed
objective_runtime.csv / benchmark_details.csv. No solver needed.

    python -m benchmarks.make_objective_panel_figures
"""
from __future__ import annotations

import sys
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
sys.path.insert(0, str(HERE.parent))

from benchmarks import models as M

RESULTS = HERE / "results" / "objective_panel"
RUNTIME_CSV = RESULTS / "objective_runtime.csv"
DETAILS_CSV = RESULTS / "benchmark_details.csv"
FIGURES = HERE / "figures"

# Reused verbatim from make_residual_tradeoff_figures.py / make_gurobi_default_figure.py --
# already CVD-validated for this exact use (research R8).
SOLVER_COLOR = {"cuopt": "#4c72b0", "gurobi": "#dd8452"}
SOLVER_LABEL = {"cuopt": "cuOpt", "gurobi": "Gurobi"}


def _figure_for_model(model, runtime_df, details_df, out_path):
    sub = runtime_df[runtime_df["model"] == model]
    if sub.empty:
        return False
    det = details_df[details_df["model"] == model].set_index(["objective_id", "solver"])

    objective_ids = list(dict.fromkeys(sub["objective_id"]))  # preserve panel order
    x = np.arange(len(objective_ids))
    w = 0.38

    fig, ax = plt.subplots(figsize=(max(9.0, 0.5 * len(objective_ids)), 5.0))
    for i, solver in enumerate(("cuopt", "gurobi")):
        ssub = sub[sub["solver"] == solver].set_index("objective_id").reindex(objective_ids)
        values = ssub["runtime_s_median"].to_numpy(dtype=np.float64)
        offset = (i - 0.5) * w
        bars = ax.bar(x + offset, values, w, label=SOLVER_LABEL[solver],
                       color=SOLVER_COLOR[solver], edgecolor="black", linewidth=0.4)
        for rect, oid, v in zip(bars, objective_ids, values):
            both_feasible = det.loc[(oid, solver), "both_feasible"] if (oid, solver) in det.index else True
            if not both_feasible:
                ax.annotate("FAILED", (rect.get_x() + rect.get_width() / 2, rect.get_height()),
                            ha="center", va="bottom", fontsize=6.0, color="#c44e52",
                            xytext=(0, 8), textcoords="offset points", fontweight="bold")

    # Every objective_candidates/<model>.csv panel's first row is, by
    # construction, the reaction already used as that model's published
    # single-objective result -- no REGISTRY lookup needed.
    baseline_rxn = objective_ids[0] if objective_ids else None
    labels = objective_ids
    ax.set_yscale("log")
    ax.set_ylabel("LP solve time (s, log scale)")
    ax.set_xticks(x)
    tick_labels = ax.set_xticklabels(labels, fontsize=7, rotation=60, ha="right")
    if baseline_rxn:
        for lbl, oid in zip(tick_labels, objective_ids):
            if oid == baseline_rxn:
                lbl.set_fontweight("bold")
                lbl.set_color("#c44e52")
    ax.set_title("%s: objective-panel credibility check (already-published objective in red)" % model)

    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return True


def main():
    if not RUNTIME_CSV.exists() or not DETAILS_CSV.exists():
        raise FileNotFoundError(
            "%s / %s not found -- run benchmarks.aggregate_objective_panel first" % (
                RUNTIME_CSV, DETAILS_CSV))
    FIGURES.mkdir(exist_ok=True)
    runtime_df = pd.read_csv(RUNTIME_CSV)
    details_df = pd.read_csv(DETAILS_CSV)

    written = []
    for model in M.ALL_MODELS:
        out_path = FIGURES / ("objective_panel_%s.png" % model)
        if _figure_for_model(model, runtime_df, details_df, out_path):
            written.append(out_path)
            print("wrote", out_path)

    if not written:
        print("no results yet -- nothing to plot")


if __name__ == "__main__":
    from benchmarks._deps import run_main
    run_main(main)
