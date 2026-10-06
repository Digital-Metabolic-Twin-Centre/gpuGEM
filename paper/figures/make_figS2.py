"""Supplementary Figure S2: numerical agreement between solvers.

    python paper/figures/make_figS2.py [--outdir DIR]

  a  Relative objective difference against Gurobi, per model
  b  Maximum constraint residual (all rows and bounds) vs model size

Data:
  benchmarks/results/benchmark.csv                       (gpuGEM and Gurobi
                                                          objectives, residuals)
  benchmarks/results/highs_baseline/highs_baseline.json  (HiGHS objective,
                                                          residual)

The published 23 Sep figure had no generator in the repository; this script
is the reproduction path, and it takes the PMM1-PMM6 labels from
data/pmm_model_mapping.csv so that a renumbering cannot leave the figure out
of step with the text.
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent))   # allow plain "python make_*.py"
import _common as C

C_GPU = "#0072B2"      # gpuGEM
C_SIMPLEX = "#D55E00"  # HiGHS dual simplex
C_GUROBI = "#666666"   # Gurobi barrier
C_STUB = "0.62"        # exact-agreement stub

FBA_TOL = 1e-6         # FBA optimality tolerance
GATE = 1e-4            # residual acceptance gate
A_FLOOR = 1e-18        # panel-a axis floor (zeros cannot sit on a log axis)


def load():
    D = C.benchmark()[["model", "n_cols", "obj_rel_diff", "gurobi_obj",
                       "gurobi_residual_inf", "cuopt_residual_inf"]].copy()
    hb = C.highs_baseline()
    D["highs_residual_inf"] = D.model.map(hb.residual_inf)
    # HiGHS objective agreement, measured against Gurobi like obj_rel_diff
    D["highs_rel_diff"] = (D.model.map(hb.objective) - D.gurobi_obj).abs() / D.gurobi_obj.abs()
    D["label"] = C.labels_for(D.model)
    return D


def build(D):
    fig, (ax_a, ax_b) = plt.subplots(2, 1, figsize=(7.0, 6.6))

    # ---- a: relative objective difference vs Gurobi ----------------------
    x = np.arange(len(D))
    series = [(-0.13, D.obj_rel_diff.values,   C_GPU,     "o", "gpuGEM vs Gurobi"),
              (0.13,  D.highs_rel_diff.values, C_SIMPLEX, "s", "HiGHS vs Gurobi")]
    for dx, v, col, mk, lab in series:
        nz = v > 0
        ax_a.vlines(x[nz] + dx, A_FLOOR, v[nz], color=C.tint(col, 0.55), lw=1.3, zorder=2)
        ax_a.plot(x[nz] + dx, v[nz], mk, color=col, ms=6.0, ls="none", label=lab, zorder=3)

    # one centred stub per model where both comparisons are identically zero
    both0 = (D.obj_rel_diff.values == 0) & (D.highs_rel_diff.values == 0)
    ax_a.vlines(x[both0], A_FLOOR, A_FLOOR * 12, color=C_STUB, lw=3.2, zorder=2)
    for dx, v, _, _, _ in series:          # a series zero on its own sits at its dodge
        lone = (v == 0) & ~both0
        ax_a.vlines(x[lone] + dx, A_FLOOR, A_FLOOR * 12, color=C_STUB, lw=2.6, zorder=2)

    ax_a.axhline(FBA_TOL, color="0.35", lw=1.0, ls="--", zorder=1)
    ax_a.text(-0.45, FBA_TOL * 1.7, "FBA optimality tolerance",
              ha="left", va="bottom", fontsize=7.4, color="0.35")
    ax_a.set_yscale("log")
    ax_a.set_ylim(A_FLOOR, 1e-5)
    ax_a.set_xlim(-0.6, len(D) - 0.4)
    ax_a.set_xticks(x)
    ax_a.set_xticklabels(C.italic_ecoli(D.label), fontsize=7.6, rotation=45, ha="right")
    ax_a.set_ylabel("|relative objective difference|")
    handles = [Line2D([], [], color=c, marker=m, ls="none", ms=6.0, label=l)
               for _, _, c, m, l in series]
    handles.append(Line2D([], [], color=C_STUB, lw=2.6,
                          label="exact agreement (difference identically 0)"))
    ax_a.legend(handles=handles, frameon=False, fontsize=7.4, loc="center right")

    # ---- b: max constraint residual vs model size ------------------------
    for v, col, mk, lab in [(D.gurobi_residual_inf, C_GUROBI,  "v", "Gurobi barrier"),
                            (D.highs_residual_inf,  C_SIMPLEX, "s", "HiGHS dual simplex"),
                            (D.cuopt_residual_inf,  C_GPU,     "o", "gpuGEM")]:
        ax_b.plot(D.n_cols, v, mk, color=col, ms=6.0, ls="none", label=lab, zorder=3)

    ax_b.axhline(GATE, color="0.35", lw=1.0, ls="--", zorder=1)
    ax_b.text(D.n_cols.min() * 0.85, GATE * 1.45, "acceptance gate",
              ha="left", va="bottom", fontsize=7.4, color="0.35")
    ax_b.set_xscale("log")
    ax_b.set_yscale("log")
    ax_b.set_xlabel("LP variables")
    ax_b.set_ylabel("Max constraint residual")
    ax_b.legend(frameon=False, fontsize=7.4, loc="lower right")

    for ax, tag in ((ax_a, "a"), (ax_b, "b")):
        ax.text(-0.09, 1.02, tag, transform=ax.transAxes,
                fontsize=11, fontweight="bold", va="bottom", ha="left")

    fig.tight_layout()
    return fig


if __name__ == "__main__":
    args = C.outdir_arg(__doc__.splitlines()[0])
    C.save(build(load()), "figS2_numerical_agreement", args.outdir, tight=True)
