"""Supplementary Figure S1: scaling and speed-up across the ten benchmark models.

    python paper/figures/make_figS1.py [--outdir DIR]

  a  LP solve time vs model size for the three solvers
  b  Speed-up of gpuGEM over each CPU baseline, same x axis

Data:
  benchmarks/results/benchmark.csv                       (gpuGEM, Gurobi barrier)
  benchmarks/results/highs_baseline/highs_baseline.json  (HiGHS, default method)

No generator for this figure survived in the repository.  This script is a
reconstruction: the plotted values are taken from the committed results and
agree with the published figure to machine precision, and the layout, palette
and annotation placement were recovered from the published PDF
(paper figure figS1_scaling_speedup.pdf).  Cosmetic details may differ
marginally from the original.
"""
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent))   # allow plain "python make_*.py"
import _common as C

# Page geometry measured from the published PDF: 514.2 x 195.6 pt.
FIG_W_IN, FIG_H_IN = 7.14, 2.72
mpl.rcParams.update({
    "font.size":        6.0,
    "axes.labelsize":   7.0,
    "xtick.labelsize":  6.0,
    "ytick.labelsize":  6.0,
    "legend.fontsize":  6.0,
    "axes.linewidth":   0.8,
    "pdf.fonttype":     42,
    "ps.fonttype":      42,
})

C_HIGHS = "#D95F02"   # HiGHS CPU baseline
C_GPU = "#1F6FB4"     # gpuGEM
C_GUROBI = "0.5"      # Gurobi barrier

#: Size range with no available models, between the whole-body reference
#: models (~8e4 variables) and the smallest personalised model (~6.9e5).
#: Shaded in panel b of the published figure.
GAP_SPAN = (8.0e4, 6.9e5)


def load():
    D = C.benchmark()[["model", "n_cols", "gurobi_solve_s_median",
                       "cuopt_solve_s_median"]].copy()
    D["highs_s"] = D.model.map(C.highs_baseline().solve_s)
    D["sp_highs"] = D.highs_s / D.cuopt_solve_s_median
    D["sp_gurobi"] = D.gurobi_solve_s_median / D.cuopt_solve_s_median
    D["label"] = C.labels_for(D.model)
    return D


def build(D):
    fig = plt.figure(figsize=(FIG_W_IN, FIG_H_IN))
    gs = fig.add_gridspec(1, 2, left=0.0801, right=0.9860, bottom=0.1641,
                          top=0.8338, wspace=0.1910)
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    x = D.n_cols.values

    # ---- a: solve time vs model size ------------------------------------
    ax_a.plot(x, D.gurobi_solve_s_median, "-o", color=C_GUROBI, ms=3.2, lw=1.0,
              label="Gurobi barrier (CPU, proprietary)")
    ax_a.plot(x, D.highs_s, "-s", color=C_HIGHS, ms=3.2, lw=1.0,
              label="HiGHS (CPU, open source)")
    ax_a.plot(x, D.cuopt_solve_s_median, "-D", color=C_GPU, ms=3.6, lw=1.3, zorder=4,
              label="gpuGEM (GPU, open source)")
    ax_a.set_xscale("log"); ax_a.set_yscale("log")
    ax_a.set_xlabel("LP variables")
    ax_a.set_ylabel("solve time (s)")
    ax_a.legend(frameon=False, loc="upper left", handlelength=1.6,
                borderaxespad=0.3, labelspacing=0.35)
    ax_a.margins(0.08)

    # ---- b: speed-up over each CPU baseline ------------------------------
    ax_b.axvspan(*GAP_SPAN, color=C_GPU, alpha=0.1, lw=0, zorder=0)
    ax_b.axhline(1.0, color="0.35", ls="--", lw=0.8, zorder=1)
    ax_b.plot(x, D.sp_highs, "s", color=C_HIGHS, ms=3.6, ls="none", zorder=3,
              label="vs HiGHS")
    ax_b.plot(x, D.sp_gurobi, "o", mfc="none", mec=C_GUROBI, mew=0.9, ms=3.8,
              ls="none", zorder=3, label="vs Gurobi barrier")
    ax_b.set_xscale("log"); ax_b.set_yscale("log")
    ax_b.set_xlabel("LP variables")
    ax_b.set_ylabel("speed-up (CPU / gpuGEM)")

    for name, off, ha in (("PMM1", (0, 7), "center"), ("iML1515", (0, -9), "center")):
        r = D[D.label == name].iloc[0]
        y = r.sp_highs if name == "PMM1" else r.sp_gurobi
        ax_b.annotate(name, (r.n_cols, y), textcoords="offset points", xytext=off,
                      ha=ha, va="center", fontsize=5.6, color="0.35")
    ax_b.legend(frameon=False, loc="lower right", handlelength=1.6,
                borderaxespad=0.3, labelspacing=0.35)
    ax_b.margins(0.08)

    for ax, tag in ((ax_a, "a"), (ax_b, "b")):
        ax.text(-0.17, 1.10, tag, transform=ax.transAxes, fontsize=9,
                fontweight="bold", va="top", ha="left")
        ax.spines[["top", "right"]].set_visible(False)
    return fig


if __name__ == "__main__":
    args = C.outdir_arg(__doc__.splitlines()[0])
    C.save(build(load()), "figS1_scaling_speedup", args.outdir)
