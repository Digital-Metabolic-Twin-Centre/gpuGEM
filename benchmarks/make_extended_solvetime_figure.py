"""Regenerate the extended cuOpt-version x lifting solve-time comparison from
the committed CSV. No solver needed.

Writes to the SAME output path as make_figure.py (benchmark_solvetime.png) --
this is a deliberate supersession for the six in-scope models, not a separate
figure (specs/014-version-lifting-runtime-comparison/research.md R6).
make_figure.py itself is unmodified and remains independently runnable,
regenerating today's narrower 2-bar view from benchmark.csv alone.

    python -m benchmarks.make_extended_solvetime_figure
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
CSV = HERE / "results" / "version_lifting_comparison.csv"
OUT = HERE / "figures" / "benchmark_solvetime.png"

CONFIG_ORDER = ["gurobi", "cuopt_old_unlifted", "cuopt_new_unlifted",
                "cuopt_old_lifted", "cuopt_new_lifted"]
CONFIG_LABEL = {
    "gurobi": "Gurobi (barrier+crossover)",
    "cuopt_old_unlifted": "cuOpt 26.6.0 (unlifted)",
    "cuopt_new_unlifted": "cuOpt 26.8.0 (unlifted)",
    "cuopt_old_lifted": "cuOpt 26.6.0 (lifted)",
    "cuopt_new_lifted": "cuOpt 26.8.0 (lifted)",
}
# Validated together via the dataviz skill's validate_palette.py (light mode):
# all checks pass (lightness band, chroma floor, CVD separation >= 12 target;
# the sub-3:1 contrast WARN on two slots is mitigated by the direct
# per-bar value-label annotations every bar already carries below).
# Gurobi/cuopt_old_unlifted reuse this project's own established colors from
# make_figure.py/make_gurobi_default_figure.py for visual consistency across
# this project's figures; the three new slots are validated dataviz-skill hues.
CONFIG_COLOR = {
    "gurobi": "#c44e52",
    "cuopt_old_unlifted": "#4c72b0",
    "cuopt_new_unlifted": "#1baf7a",
    "cuopt_old_lifted": "#eda100",
    "cuopt_new_lifted": "#4a3aa7",
}
VALUE_COL = {
    "gurobi": "gurobi_solve_s_median",
    "cuopt_old_unlifted": "cuopt_old_unlifted_solve_s_median",
    "cuopt_new_unlifted": "cuopt_new_unlifted_solve_s_median",
    "cuopt_old_lifted": "cuopt_old_lifted_solve_s_median",
    "cuopt_new_lifted": "cuopt_new_lifted_solve_s_median",
}
GATE_COL = {
    "cuopt_old_unlifted": "cuopt_old_unlifted_verified_correct",
    "cuopt_new_unlifted": "cuopt_new_unlifted_verified_correct",
    "cuopt_old_lifted": "cuopt_old_lifted_verified_correct",
    "cuopt_new_lifted": "cuopt_new_lifted_verified_correct",
}


def main():
    df = pd.read_csv(CSV)
    df = df.sort_values("n_cols").reset_index(drop=True)

    labels = ["%s\n(%s vars)" % (r.model, format(int(r.n_cols), ",")) for r in df.itertuples()]
    x = np.arange(len(df))
    # Fixed at the full configuration set's size, NOT how many happen to be
    # present in the data right now -- offsets must stay stable as more
    # combinations get solved, or bars silently drift to the wrong tick
    # (caught by visual inspection: with a partial run, deriving this from
    # the data's current max made a present config's offset exceed half a
    # tick spacing, rendering it under the *next* model's label instead).
    n_configs = len(CONFIG_ORDER)
    w = 0.8 / n_configs

    fig, ax = plt.subplots(figsize=(max(11.0, 1.8 * len(df)), 5.2))

    for i, config in enumerate(CONFIG_ORDER):
        values = df[VALUE_COL[config]].to_numpy(dtype=np.float64)
        present = np.isfinite(values)
        if not present.any():
            continue
        offset = (i - (n_configs - 1) / 2) * w
        bars = ax.bar(x[present] + offset, values[present], w, label=CONFIG_LABEL[config],
                       color=CONFIG_COLOR[config], edgecolor="black", linewidth=0.4)
        for rect, v in zip(bars, values[present]):
            h = rect.get_height()
            ax.annotate("%.3g" % v, (rect.get_x() + rect.get_width() / 2, h),
                        ha="center", va="bottom", fontsize=6.0,
                        xytext=(0, 1.5), textcoords="offset points")

        if config in GATE_COL:
            gate = df[GATE_COL[config]].astype("boolean").fillna(True)
            failed = ~gate
            idx_present = np.where(present)[0]
            for rect, row_idx in zip(bars, idx_present):
                if failed.iloc[row_idx]:
                    ax.annotate("FAILED", (rect.get_x() + rect.get_width() / 2, rect.get_height()),
                                ha="center", va="bottom", fontsize=5.6, color="#c44e52",
                                xytext=(0, 8), textcoords="offset points", fontweight="bold")

    ax.set_yscale("log")
    ax.set_ylabel("LP solve time (s, log scale)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_title("cuOpt vs Gurobi: solve time across cuOpt version and lifting "
                  "(e_coli_core → S85)")

    ax.legend(frameon=False, fontsize=7.5, ncol=2)
    fig.tight_layout()
    fig.savefig(OUT, dpi=300, bbox_inches="tight")
    print("wrote", OUT)


if __name__ == "__main__":
    from benchmarks._deps import run_main
    run_main(main)
