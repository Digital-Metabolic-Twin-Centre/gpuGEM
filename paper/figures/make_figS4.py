"""Supplementary Figure S4: runtime against PDLP iteration count.

    python paper/figures/make_figS4.py [--outdir DIR]

All ten benchmark models.  Data: benchmarks/results/benchmark.csv
(cuopt_solve_s_median, cuopt_iters, n_cols).

No generator for this figure survived in the repository; this script is the
reproduction path.  Label offsets are keyed by model identifier rather than
by paper label, so a renumbering of PMM1-PMM6 moves the label text without
moving the annotation geometry.
"""
import numpy as np
import matplotlib.pyplot as plt

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent))   # allow plain "python make_*.py"
import _common as C

C_GPU = "#1f77b4"
C_LAB = "0.35"

#: model id -> (label offset in points, draw a leader line, horizontal alignment)
PLACE = {
    "e_coli_core": ((10, -13), False, "left"),
    "Harvetta":    ((-10, -17), False, "right"),
    "Harvey":      ((11, -4), False, "left"),
    "S84":         ((12, -2), False, "left"),
    "iML1515":     ((-10, 9), False, "right"),
    "S15":         ((-13, 0), False, "right"),
    # S9/S83/S85 are near-coincident; fan their labels out on leaders
    "S9":          ((-4, 32), True, "right"),
    "S83":         ((10, -34), True, "left"),
    "S85":         ((30, -12), True, "left"),
    "S23":         ((12, 2), False, "left"),
}


def load():
    d = C.benchmark()[["model", "n_cols", "cuopt_solve_s_median", "cuopt_iters"]].copy()
    d = d.rename(columns={"cuopt_solve_s_median": "solve_s", "cuopt_iters": "iters"})
    d["label"] = C.labels_for(d.model)
    return d


def build(d):
    fig, ax = plt.subplots(figsize=(6.4, 5.4))
    ax.plot(d.iters, d.solve_s, "o", color=C_GPU, ms=9, ls="none", zorder=3)

    for _, r in d.iterrows():
        off, leader, ha = PLACE[r.model]
        style = dict(fontsize=9, color=C_LAB,
                     style="italic" if r.label.startswith("E. coli") else "normal")
        ax.annotate(r.label, (r.iters, r.solve_s), textcoords="offset points",
                    xytext=off, ha=ha,
                    va="center", zorder=4,
                    arrowprops=dict(arrowstyle="-", color="0.65", lw=0.7,
                                    shrinkA=0, shrinkB=5) if leader else None,
                    **style)

    # correlations are reported in the caption, not drawn on the panel
    lt, li, ln = np.log10(d.solve_s), np.log10(d.iters), np.log10(d.n_cols)
    r_it = np.corrcoef(lt, li)[0, 1]
    r_sz = np.corrcoef(lt, ln)[0, 1]

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("PDLP iterations")
    ax.set_ylabel("gpuGEM solve time (s)")
    ax.margins(0.16)
    fig.tight_layout()
    return fig, r_it, r_sz


if __name__ == "__main__":
    args = C.outdir_arg(__doc__.splitlines()[0])
    fig, r_it, r_sz = build(load())
    C.save(fig, "figS4_iteration_mechanism", args.outdir, tight=True)
    print("r_iter=%.3f r_size=%.3f  (reported in the caption)" % (r_it, r_sz))
