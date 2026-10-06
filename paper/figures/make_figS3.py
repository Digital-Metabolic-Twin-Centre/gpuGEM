"""Supplementary Figure S3: objective invariance on PMM2.

    python paper/figures/make_figS3.py [--outdir DIR]

  a  Solve time for each of the 50 biologically distinct objectives,
     ordered by gpuGEM solve time and coloured by objective class, with the
     Gurobi barrier time for the same objective drawn as an open outline
  b  The same times normalised by their mean, with the coefficient of
     variation for each solver

Data:
  benchmarks/results/objective_panel/objective_runtime.csv   (solve times)
  benchmarks/results/objective_panel/benchmark_details.csv   (objective class)

No generator for this figure survived in the repository.  This script is a
reconstruction: the plotted values and the bar ordering are taken from the
committed results and reproduce the published figure, and the layout and
palette were recovered from the published PDF
(paper figure figS3_objective_invariance.pdf).
"""
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent))   # allow plain "python make_*.py"
import _common as C

#: Personalised model carrying the objective panel in this figure.
MODEL = "S85"

FIG_W_IN, FIG_H_IN = 7.216, 3.096
mpl.rcParams.update({
    "font.size":        6.0,
    "axes.labelsize":   8.0,
    "xtick.labelsize":  6.0,
    "ytick.labelsize":  6.0,
    "legend.fontsize":  6.0,
    "axes.linewidth":   0.8,
    "pdf.fonttype":     42,
    "ps.fonttype":      42,
})

C_GPU = "#1F6FB4"
C_GUROBI = "#C1502E"
#: Objective classes, in legend order, with their fill colours.
CLASSES = [("organ_biomass",       "#1F6FB4", "organ biomass"),
           ("immune_cell_biomass", "#7FB2E5", "immune cell biomass"),
           ("microbiome_taxon",    "#2E8B57", "microbiome taxon"),
           ("whole_body",          "#B85CA0", "whole body")]


def load():
    run = pd.read_csv(C.RESULTS / "objective_panel" / "objective_runtime.csv")
    run = run[run.model == MODEL]
    W = run.pivot_table(index="objective_id", columns="solver", values="runtime_s_median")

    det = pd.read_csv(C.RESULTS / "objective_panel" / "benchmark_details.csv")
    cat = (det[det.model == MODEL].drop_duplicates("objective_id")
           .set_index("objective_id").category)
    W["category"] = cat
    assert W.category.notna().all(), "objective class missing for some objectives"
    # Longest gpuGEM solve at the top of the panel.
    return W.sort_values("cuopt", ascending=False)


def build(W):
    fig = plt.figure(figsize=(FIG_W_IN, FIG_H_IN))
    ax_a = fig.add_axes([33.16/519.57, 67.14/222.92, 259.60/519.57, 128.85/222.92])
    ax_b = fig.add_axes([339.30/519.57, 67.14/222.92, 173.07/519.57, 128.85/222.92])

    # ---- a: per-objective solve time -------------------------------------
    y = np.arange(len(W))[::-1]          # first row at the top
    fill = dict((k, c) for k, c, _ in CLASSES)
    ax_a.barh(y, W.cuopt.values, height=0.79, zorder=3,
              color=[fill[c] for c in W.category], lw=0)
    ax_a.barh(y, W.gurobi.values, height=0.79, zorder=4,
              facecolor="none", edgecolor=C_GUROBI, lw=0.6)
    ax_a.set_xlabel("solve time (s)")
    ax_a.set_yticks([])
    ax_a.set_ylim(-1.0, len(W))
    ax_a.margins(x=0.02)
    ax_a.spines[["top", "right", "left"]].set_visible(False)

    wb = W.index[W.category == "whole_body"][0]
    ax_a.annotate("whole-body objective", (W.cuopt[wb] * 0.985, y[W.index.get_loc(wb)]),
                  ha="right", va="center", fontsize=5.6, color="white", zorder=6)

    handles = [Patch(facecolor=c, label=l) for _, c, l in CLASSES]
    handles.append(Line2D([], [], color=C_GUROBI, lw=0.9, label="Gurobi barrier (outline)"))
    fig.legend(handles=handles, ncol=3, frameon=False, fontsize=6.0,
               loc="lower center", bbox_to_anchor=(0.315, 0.005),
               handlelength=1.3, columnspacing=1.4)

    # ---- b: normalised distribution and dispersion ------------------------
    N = W[["cuopt", "gurobi"]] / W[["cuopt", "gurobi"]].mean()
    rng = np.random.default_rng(0)
    cols = {"cuopt": C_GPU, "gurobi": C_GUROBI}
    for i, s in enumerate(["cuopt", "gurobi"]):
        v = N[s].values
        parts = ax_b.violinplot([v], positions=[i], widths=0.62, showextrema=False)
        for b in parts["bodies"]:
            b.set_facecolor(C.tint(cols[s], 0.25)); b.set_alpha(1.0); b.set_edgecolor("none")
        ax_b.plot(i + rng.uniform(-0.10, 0.10, v.size), v, "o",
                  color=C.tint(cols[s], 0.85), ms=2.6, mew=0)
        cv = 100 * v.std(ddof=1) / v.mean()
        ax_b.text(i, 1.02, "CV = %.1f%%" % cv, transform=ax_b.get_xaxis_transform(),
                  ha="center", va="bottom", fontsize=5.6, color=cols[s])
    ax_b.axhline(1.0, color="0.4", ls=":", lw=0.8)
    ax_b.set_xticks([0, 1])
    ax_b.set_xticklabels(["gpuGEM\n(GPU)", "Gurobi\n(CPU)"])
    ax_b.set_ylabel("solve time / mean")
    ax_b.set_xlim(-0.6, 1.6)
    ax_b.margins(y=0.06)
    ax_b.spines[["top", "right"]].set_visible(False)

    for ax, tag, dx in ((ax_a, "a", -0.055), (ax_b, "b", -0.085)):
        ax.text(dx, 1.09, tag, transform=ax.transAxes, fontsize=9,
                fontweight="bold", va="top", ha="left")
    return fig


if __name__ == "__main__":
    args = C.outdir_arg(__doc__.splitlines()[0])
    C.save(build(load()), "figS3_objective_invariance", args.outdir)
