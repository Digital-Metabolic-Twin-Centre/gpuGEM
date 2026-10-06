"""Figure 1 of the manuscript: the four-panel headline comparison.

    python paper/figures/make_fig1.py [--outdir DIR]

Panels, and the committed results each is drawn from:

  a  LP solve time vs model size, ten models, four solver configurations
       benchmarks/results/benchmark.csv                     (gpuGEM, Gurobi)
       benchmarks/results/highs_baseline/highs_baseline.json (HiGHS simplex)
       paper/figures/data/highs_ipm_fig1.csv                 (HiGHS IPM)
  b  Speed-up of gpuGEM over each CPU baseline, per model
       derived from the panel-a series
  c  Maximum stoichiometric residual per model and configuration
       benchmarks/results/residual_tradeoff/comparison.csv
  d  Solve-time distribution over 50 objectives on PMM1
       benchmarks/results/objective_panel/objective_runtime.csv

The figure is authored at the journal double-column measure (178 mm) so it
is placed at scale 1.0 and every label prints at its nominal size.
"""
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent))   # allow plain "python make_*.py"
import _common as C

# Page size, panel geometry and type sizes reproduce the figure embedded in
# the manuscript; they were measured off that PDF.
FIG_W_IN = 10.975
FIG_H_IN = 8.701
mpl.rcParams.update({
    "font.size":        7.0,
    "axes.labelsize":   8.0,
    "xtick.labelsize":  6.0,
    "ytick.labelsize":  6.0,
    "legend.fontsize":  7.4,
    "axes.linewidth":   0.7,
    "xtick.major.width": 0.7,
    "ytick.major.width": 0.7,
    "xtick.minor.width": 0.5,
    "ytick.minor.width": 0.5,
    "pdf.fonttype":     42,
    "ps.fonttype":      42,
})

#: Objective panel shown in panel d.  PMM1 is the smallest personalised model.
PANEL_D_MODEL = "S84"


def load():
    """Assemble the three panel tables from the committed benchmark results."""
    D = C.benchmark()[["model", "n_cols", "gurobi_solve_s_median",
                       "cuopt_solve_s_median", "gurobi_residual_inf"]].copy()
    D["highs_simplex_s"] = D.model.map(C.highs_baseline().solve_s)

    ipm = C.highs_ipm()
    D["ipm_s"] = D.model.map(ipm.ipm_s)
    D["ipm_usable"] = D.model.isin(ipm.index[ipm.ipm_usable.astype(bool)])
    # Runs that finished with a non-optimal status are shown as open markers
    # in panel a and excluded from the speed-up panel.
    D["ipm_plot"] = D.ipm_s.where(D.ipm_usable)
    D["label"] = C.labels_for(D.model)

    D["sp_simplex"] = D.highs_simplex_s / D.cuopt_solve_s_median
    D["sp_ipm"] = D.ipm_plot / D.cuopt_solve_s_median
    D["sp_gurobi"] = D.gurobi_solve_s_median / D.cuopt_solve_s_median

    rt = pd.read_csv(C.RESULTS / "residual_tradeoff" / "comparison.csv")
    RC = (rt.pivot_table(index="model", columns="configuration",
                         values="residual_inf", aggfunc="first")
            .reindex(D.model.values))

    run = pd.read_csv(C.RESULTS / "objective_panel" / "objective_runtime.csv")
    run = run[run.model == PANEL_D_MODEL]
    PD = run.pivot_table(index="objective_id", columns="solver",
                         values="runtime_s_median")
    PD = PD / PD.mean()
    return D, RC, PD


def build(D, RC, PD):
    fig = plt.figure(figsize=(FIG_W_IN, FIG_H_IN))
    gs = fig.add_gridspec(2, 2, hspace=0.340, wspace=0.260,
                          left=0.066, right=0.991, top=0.966, bottom=0.071)
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[1, 0])
    ax_d = fig.add_subplot(gs[1, 1])

    x = D.n_cols.values

    # ---- a: solve time vs model size -----------------------------------
    ax_a.plot(x, D.highs_simplex_s, "-s", color=C.C_SIMPLEX, ms=4.0, lw=1.2,
              label="HiGHS dual simplex (open-source CPU)")
    ok = D.ipm_usable.values
    ax_a.plot(x[ok], D.ipm_plot.values[ok], "^", color=C.C_IPM, ms=4.3, ls="none", zorder=6,
              label="HiGHS interior point (correct status)")
    bad = (~D.ipm_usable.values) & D.ipm_s.notna().values
    ax_a.plot(x[bad], D.ipm_s.values[bad], "^", mfc="none", mec=C.C_IPM, mew=1.0, ms=4.6, zorder=7,
              ls="none", label="HiGHS interior point (wrong status)")
    ax_a.plot(x, D.gurobi_solve_s_median, "-v", color=C.C_GUROBI, ms=4.0, lw=1.2,
              label="Gurobi barrier (commercial CPU)")
    ax_a.plot(x, D.cuopt_solve_s_median, "-o", color=C.C_GPU, ms=5.0, lw=1.8, zorder=4,
              label="gpuGEM (GPU, open source)")
    ax_a.set_xscale("log"); ax_a.set_yscale("log")
    ax_a.set_xlabel("Model size (variables)")
    ax_a.set_ylabel("LP solve time (s)")
    ax_a.axvline(1e4, color="0.75", ls=":", lw=0.9, zorder=0)
    ax_a.text(1.15e4, 3e-3, "10$^{4}$", color="0.5", fontsize=8.0)
    ax_a.legend(frameon=False, fontsize=7.4, loc="upper left")
    ax_a.margins(0.06)

    # ---- b: speed-up per model -----------------------------------------
    xb = np.arange(len(D))
    ax_b.axhline(1.0, color="0.35", lw=0.9, zorder=1)
    series = [(-0.22, D.sp_simplex, C.C_SIMPLEX, "s", "vs HiGHS dual simplex"),
              (0.00,  D.sp_ipm,     C.C_IPM,     "^", "vs HiGHS interior point"),
              (0.22,  D.sp_gurobi,  C.C_GUROBI,  "v", "vs Gurobi barrier")]
    for dx, vals, col, mk, lab in series:
        v = vals.values
        m = ~np.isnan(v)
        ax_b.vlines(xb[m] + dx, 1.0, v[m], color=C.tint(col, 0.55), lw=1.0, zorder=2)
        ax_b.plot(xb[m] + dx, v[m], mk, color=col, ms=4.6, ls="none", label=lab, zorder=3)
    ax_b.set_yscale("log")
    ax_b.set_xticks(xb)
    ax_b.set_xticklabels(C.italic_ecoli(D.label), fontsize=7.6, rotation=45, ha="right")
    ax_b.set_ylabel("Speed-up over CPU baseline (×)")
    ax_b.legend(frameon=False, fontsize=7.4, loc="lower right", ncol=1)
    ax_b.margins(x=0.05, y=0.10)

    # ---- c: stoichiometric residual -------------------------------------
    xc = np.arange(len(D))
    ax_c.axhspan(1e-15, 1e-4, color="0.92", zorder=0)
    ax_c.axhline(1e-4, color="0.35", ls="--", lw=0.9, zorder=1)
    floor = 1e-14
    for vals, col, mk, lab in [
            (RC.gurobi.values,          C.C_GUROBI,  "o", "Gurobi barrier"),
            (RC.shipped_default.values, C.C_GPU,     "s", "gpuGEM, shipped default"),
            (RC.residual_0.values,      C.C_NOTOL,   "^", "gpuGEM, residual tolerance off")]:
        v = np.where(np.asarray(vals, float) <= 0, floor, np.asarray(vals, float))
        ax_c.plot(xc, v, mk, color=col, ms=4.6, ls="none", label=lab, zorder=3)
    ax_c.set_yscale("log")
    ax_c.set_xticks(xc)
    ax_c.set_xticklabels(C.italic_ecoli(D.label), fontsize=7.6, rotation=45, ha="right")
    ax_c.set_ylabel("Max. stoichiometric residual")
    ax_c.text(0.985, 0.055, "feasible", transform=ax_c.transAxes, ha="right",
              fontsize=7.6, color="0.45")
    ax_c.text(0.985, 0.62, "acceptance criterion 10$^{-4}$", transform=ax_c.transAxes,
              ha="right", fontsize=7.6, color="0.35")
    ax_c.set_ylim(3e-15, 3e3)
    ax_c.legend(frameon=False, fontsize=7.4, loc="upper left")
    ax_c.margins(x=0.05)

    # ---- d: objective panel on PMM1 --------------------------------------
    rng = np.random.default_rng(0)
    cols = {"cuopt": C.C_GPU, "gurobi": C.C_GUROBI}
    names = {"cuopt": "gpuGEM\n(GPU)", "gurobi": "Gurobi\n(CPU)"}
    for i, s in enumerate(["cuopt", "gurobi"]):
        v = PD[s].dropna().values
        parts = ax_d.violinplot([v], positions=[i], widths=0.62, showextrema=False)
        for b in parts["bodies"]:
            b.set_facecolor(C.tint(cols[s], 0.22)); b.set_alpha(1.0); b.set_edgecolor("none")
        ax_d.plot(i + rng.uniform(-0.10, 0.10, v.size), v, "o", color=C.tint(cols[s], 0.85),
                  ms=3.0, mew=0)
    ax_d.axhline(1.0, color="0.4", ls=":", lw=0.8)
    ax_d.set_xticks([0, 1]); ax_d.set_xticklabels([names[s] for s in ["cuopt", "gurobi"]])
    ax_d.set_ylabel("Solve time / mean")
    ax_d.set_xlim(-0.6, 1.6)
    ax_d.margins(y=0.10)

    for ax, L in [(ax_a, "a"), (ax_b, "b"), (ax_c, "c"), (ax_d, "d")]:
        ax.text(-0.155, 1.055, L, transform=ax.transAxes, fontsize=14,
                fontweight="bold", va="top", ha="left")
        ax.spines[["top", "right"]].set_visible(False)
    return fig


if __name__ == "__main__":
    args = C.outdir_arg(__doc__.splitlines()[0])
    C.save(build(*load()), "fig1_main_fourpanel", args.outdir)
