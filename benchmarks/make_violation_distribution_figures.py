"""Regenerate the two population-pyramid-style violation-distribution figures from the
committed per_constraint_residual=0 results. No solver needed.

    python -m benchmarks.make_violation_distribution_figures
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from benchmarks.make_residual_tradeoff_figures import NON_RECOMMENDATION_NOTICE
from benchmarks.violation_histogram import MAGNITUDE_BIN_EDGES

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results" / "residual_tradeoff"
FIGURES = HERE / "figures"
EQUATIONS_OUT = FIGURES / "violation_distribution_equations.png"
CONSTRAINTS_OUT = FIGURES / "violation_distribution_constraints.png"

# Single-hue, ordinal ramp keyed to model-size rank -- deliberately a different hue family
# from the CONFIG_COLOR categorical palette (blue/orange/red) used by
# make_residual_tradeoff_figures.py, since this figure's color encodes a different thing
# (model identity/size, not configuration identity).
CMAP = plt.get_cmap("Purples")


def _load_entries(field):
    """Return [(model, n_cols, histogram), ...] sorted ascending by n_cols, skipping
    models whose `field` is null (e.g. constraint histograms for BiGG models with no
    coupling block)."""
    entries = []
    for path in sorted(RESULTS.glob("*.json")):
        if path.name == "comparison.csv":
            continue
        d = json.loads(path.read_text())
        hist = d["residual_0"].get(field)
        if hist is None:
            continue
        entries.append((d["model"], d["n_cols"], hist))
    entries.sort(key=lambda e: e[1])
    return entries


def _stairs_xy(edges, counts, sign):
    """Step-function (y, x) pairs for one side of the mirrored histogram; x is signed
    so shortfall plots negative (left) and excess plots positive (right)."""
    y = np.repeat(edges, 2)[1:-1]
    x = sign * np.repeat(np.asarray(counts, dtype=np.float64), 2)
    return y, x


def _bin_mids(edges):
    edges = np.asarray(edges, dtype=np.float64)
    return np.sqrt(edges[:-1] * edges[1:])


def _pyramid_figure(entries, out_path, title, row_population_label):
    n = len(entries)
    fig, ax = plt.subplots(figsize=(max(9.5, 1.2 * n), 7.0))

    edges = np.asarray(entries[0][2]["bin_edges"], dtype=np.float64)
    mids = _bin_mids(edges)

    for rank, (model, n_cols, hist) in enumerate(entries):
        frac = 0.35 + 0.60 * (rank / max(n - 1, 1))
        color = CMAP(frac)

        y_sf, x_sf = _stairs_xy(edges, hist["shortfall_counts"], -1)
        y_ex, x_ex = _stairs_xy(edges, hist["excess_counts"], 1)
        ax.fill_betweenx(y_sf, 0, x_sf, color=color, alpha=0.4, linewidth=0)
        ax.fill_betweenx(y_ex, 0, x_ex, color=color, alpha=0.4, linewidth=0)

        shortfall = np.asarray(hist["shortfall_counts"])
        excess = np.asarray(hist["excess_counts"])
        combined = shortfall + excess
        idx = int(np.argmax(combined)) if combined.max() > 0 else 0
        y_label = mids[idx]
        if excess[idx] >= shortfall[idx]:
            x_label, ha = excess[idx] * 1.05 + 0.5, "left"
        else:
            x_label, ha = -(shortfall[idx] * 1.05 + 0.5), "right"

        ax.plot(x_label, y_label, "o", color=color, markersize=5, markeredgecolor="black",
                 markeredgewidth=0.3, clip_on=False)
        ax.annotate(model, (x_label, y_label), ha=ha, va="center", fontsize=7,
                     color="#333333", xytext=(6 if ha == "left" else -6, 0),
                     textcoords="offset points")

    ax.set_yscale("log")
    ax.set_ylim(edges[0], edges[-1])
    ax.set_ylabel("Violation magnitude (log scale)")
    ax.set_xlabel("Shortfall count (left)  <->  Excess count (right)")
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_title(title)

    handles = [plt.Line2D([0], [0], marker="o", linestyle="", markersize=6,
                            color=CMAP(0.35 + 0.60 * (r / max(n - 1, 1))),
                            label="%s (%s vars)" % (m, format(int(c), ",")))
               for r, (m, c, _) in enumerate(entries)]
    ax.legend(handles=handles, frameon=False, fontsize=7, loc="upper left",
              bbox_to_anchor=(1.01, 1.0), title="%s, smallest -> largest" % row_population_label)

    fig.text(0.5, -0.02, NON_RECOMMENDATION_NOTICE, ha="center", va="top",
              fontsize=7.2, wrap=True, style="italic")

    fig.tight_layout()
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    print("wrote", out_path)


def main():
    FIGURES.mkdir(exist_ok=True)

    eq_entries = _load_entries("violation_histogram_equations")
    _pyramid_figure(
        eq_entries, EQUATIONS_OUT,
        "per_constraint_residual=0: mass-balance equation violations by model",
        "model",
    )

    con_entries = _load_entries("violation_histogram_constraints")
    if con_entries:
        _pyramid_figure(
            con_entries, CONSTRAINTS_OUT,
            "per_constraint_residual=0: coupling constraint violations by model",
            "model",
        )
    else:
        print("no models with a coupling block found; skipping", CONSTRAINTS_OUT)


if __name__ == "__main__":
    main()
