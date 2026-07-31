"""Regenerate the two population-pyramid-style violation-distribution figures from the
committed per_constraint_residual=0 results. No solver needed.

    python -m benchmarks.make_violation_distribution_figures
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import PchipInterpolator

from benchmarks.make_residual_tradeoff_figures import NON_RECOMMENDATION_NOTICE

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results" / "residual_tradeoff"
FIGURES = HERE / "figures"
EQUATIONS_OUT = FIGURES / "violation_distribution_equations.png"
CONSTRAINTS_OUT = FIGURES / "violation_distribution_constraints.png"

# Continuous, perceptually-uniform sequential ramp keyed to model-size rank (dark ->
# light tracks smallest -> largest), matching the flowing multi-hue style of Our World
# in Data's population-pyramid chart. Deliberately a different hue family from the
# CONFIG_COLOR categorical palette (blue/orange/red) used by
# make_residual_tradeoff_figures.py, since this figure encodes a different thing
# (model identity/size, not configuration identity).
CMAP = plt.get_cmap("viridis")
INK = "#2b2b2b"
MUTED = "#6b6b6b"
GRID = "#e4e4e0"
_TEXT_HALO = [pe.withStroke(linewidth=2.6, foreground="white")]


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


def _bin_mids(edges):
    edges = np.asarray(edges, dtype=np.float64)
    return np.sqrt(edges[:-1] * edges[1:])


def _smooth_curve(edges, counts, n_points=400):
    """Monotone-safe interpolation of a binned count profile onto a fine log-scale y
    grid, tapering to zero at both ends -- turns the blocky per-bin histogram into a
    flowing contour (matplotlib PCHIP: no overshoot, so it never invents a negative
    count). This is a rendering smoothing only; the binned counts themselves (what
    gets persisted and tested) are untouched."""
    edges = np.asarray(edges, dtype=np.float64)
    counts = np.asarray(counts, dtype=np.float64)
    mids = _bin_mids(edges)

    log_y = np.concatenate(([np.log10(edges[0])], np.log10(mids), [np.log10(edges[-1])]))
    x = np.concatenate(([0.0], counts, [0.0]))

    interp = PchipInterpolator(log_y, x)
    y_fine_log = np.linspace(log_y[0], log_y[-1], n_points)
    x_fine = np.clip(interp(y_fine_log), 0.0, None)
    y_fine = 10 ** y_fine_log
    return y_fine, x_fine


def _label_anchor(ax, y, x, placed_px, min_px=85):
    """Pick the widest available point along a curve for a direct label, skipping any
    point too close (in rendered pixels) to an already-placed label -- keeps every
    model's name individually legible even when several models' peaks coincide.
    min_px is sized for label text width, not just the anchor point, since two
    adjacent anchors can still produce overlapping strings.

    x is signed (negative on the shortfall/left side, positive on excess/right), so
    "widest" means largest magnitude, not largest signed value -- sorting by -x alone
    would treat the shortfall side's near-zero tail as "best" and its true (very
    negative) peak as "worst".

    Ties (most commonly: a curve that's exactly zero everywhere) are broken by
    ascending index rather than left to argsort's unspecified tie order -- otherwise
    two identical all-zero curves can each resolve to a different, effectively
    arbitrary index and land anywhere on the axis, including on top of each other.
    """
    order = np.lexsort((np.arange(len(x)), -np.abs(x)))
    fallback = None
    for idx in order:
        if idx < 3 or idx > len(y) - 4:
            continue
        pt = ax.transData.transform((x[idx], y[idx]))
        if fallback is None:
            fallback = (idx, pt)
        if all(np.hypot(pt[0] - p[0], pt[1] - p[1]) >= min_px for p in placed_px):
            return idx, pt
    return fallback if fallback is not None else (order[0], ax.transData.transform((x[order[0]], y[order[0]])))


def _label_angle(ax, y, x, idx):
    """Local slope of the curve at idx, in on-screen degrees, so the label follows
    the contour the way the reference chart's year labels ride their flow lines.

    A line's slope and slope+180 look identical as a rotation *except* text at the
    two is one upright and one upside-down; normalizing into (-90, 90] always picks
    the upright, left-to-right-readable one, whichever side of the axis it's on."""
    i0, i1 = max(idx - 4, 0), min(idx + 4, len(y) - 1)
    p0 = ax.transData.transform((x[i0], y[i0]))
    p1 = ax.transData.transform((x[i1], y[i1]))
    angle = np.degrees(np.arctan2(p1[1] - p0[1], p1[0] - p0[0]))
    return (angle + 90) % 180 - 90


def _pyramid_figure(entries, out_path, title, subtitle):
    n = len(entries)
    fig, ax = plt.subplots(figsize=(max(10.5, 1.15 * n), 7.4))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    edges = np.asarray(entries[0][2]["bin_edges"], dtype=np.float64)

    curves = [(_smooth_curve(edges, h["shortfall_counts"]), _smooth_curve(edges, h["excess_counts"]))
              for _, _, h in entries]
    peaks = [max(x_sf.max(), x_ex.max()) for (_, x_sf), (_, x_ex) in curves]
    global_peak = max(peaks) if peaks else 0.0
    # A model's peak is "negligible" -- not a meaningful label anchor -- either in
    # absolute terms (a handful of rows) or relative to this figure's own dominant
    # model: the two figures span very different x-axis scales (tens of thousands vs.
    # thousands), so a fixed row-count threshold that works for one badly under- or
    # over-fires on the other (research/spec doesn't fix a shared count; this is a
    # rendering-legibility choice, not a data threshold).
    negligible_cutoff = max(15.0, 0.03 * global_peak)

    placed_px = []
    negligible_rank = 0
    for rank, (model, n_cols, hist) in enumerate(entries):
        frac = 0.12 + 0.80 * (rank / max(n - 1, 1))
        color = CMAP(frac)

        (y_sf, x_sf), (y_ex, x_ex) = curves[rank]
        # Kept semi-transparent (not the reference chart's near-opaque fill) because,
        # unlike nested year-over-year population curves, these models' distributions
        # aren't monotonically nested -- an opaque top layer would fully hide a
        # smaller model's band wherever a larger one happens to overlap it (FR-007).
        ax.fill_betweenx(y_sf, 0, -x_sf, color=color, alpha=0.42, linewidth=0, zorder=rank)
        ax.fill_betweenx(y_ex, 0, x_ex, color=color, alpha=0.42, linewidth=0, zorder=rank)
        ax.plot(-x_sf, y_sf, color=color, linewidth=0.9, alpha=0.95, zorder=rank + 0.5)
        ax.plot(x_ex, y_ex, color=color, linewidth=0.9, alpha=0.95, zorder=rank + 0.5)

        if peaks[rank] >= negligible_cutoff:
            # Label whichever side is wider for this model.
            if x_sf.max() >= x_ex.max():
                y_c, x_c = y_sf, -x_sf
            else:
                y_c, x_c = y_ex, x_ex
            idx, pt = _label_anchor(ax, y_c, x_c, placed_px, min_px=115)
            placed_px.append(pt)
            angle = _label_angle(ax, y_c, x_c, idx)
            x_lab, y_lab = x_c[idx], y_c[idx]
        else:
            # Negligible or zero violations: nothing to peak-label. Stack these on
            # their own shelves near the axis floor -- log scale gives every decade
            # equal pixel height, so a handful of shelves stays individually
            # readable rather than every near-zero model competing for the same
            # meaningless (x ~ 0) spot. Geometric (not linear) spacing so the shelves
            # stay evenly spread in *decades* regardless of how many there are.
            y_lab = edges[0] * 10 ** (0.5 * (negligible_rank + 1))
            x_lab, angle = 0.0, 0.0
            placed_px.append(ax.transData.transform((x_lab, y_lab)))
            negligible_rank += 1

        ax.annotate(model, (x_lab, y_lab), color=INK, fontsize=8, fontweight="medium",
                     rotation=angle, rotation_mode="anchor", ha="center", va="center",
                     path_effects=_TEXT_HALO, zorder=100)

    ax.set_yscale("log")
    ax.set_ylim(edges[0], edges[-1])
    ax.set_ylabel("Violation magnitude (log scale)", color=MUTED, fontsize=10)
    ax.axvline(0, color=INK, linewidth=1.0, zorder=99)

    xmax = max(abs(v) for v in ax.get_xlim())
    ax.set_xlim(-xmax, xmax)

    ax.grid(axis="x", color=GRID, linewidth=1.0, zorder=0)
    ax.grid(axis="y", visible=False)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=8)

    fmt = lambda v, _pos: format(int(abs(v)), ",")
    ax.xaxis.set_major_formatter(plt.FuncFormatter(fmt))
    ax_top = ax.secondary_xaxis("top")
    ax_top.xaxis.set_major_formatter(plt.FuncFormatter(fmt))
    ax_top.tick_params(colors=MUTED, labelsize=8)
    ax_top.spines["top"].set_visible(False)

    fig.text(0.27, 0.075, "falls short of required balance", ha="center", va="top",
              fontsize=11, color=MUTED)
    fig.text(0.73, 0.075, "exceeds required balance", ha="center", va="top",
              fontsize=11, color=MUTED)

    fig.text(0.06, 0.965, title, ha="left", va="top", fontsize=16, color=INK, weight="bold")
    fig.text(0.06, 0.925, subtitle, ha="left", va="top", fontsize=10.5, color=MUTED)
    fig.text(0.06, 0.025, NON_RECOMMENDATION_NOTICE, ha="left", va="bottom",
              fontsize=7.5, color=MUTED, style="italic", wrap=True)

    fig.subplots_adjust(top=0.87, bottom=0.15, left=0.075, right=0.97)
    fig.savefig(out_path, dpi=300, facecolor="white")
    print("wrote", out_path)


def main():
    FIGURES.mkdir(exist_ok=True)

    eq_entries = _load_entries("violation_histogram_equations")
    _pyramid_figure(
        eq_entries, EQUATIONS_OUT,
        "Mass-balance equation violations under per_constraint_residual=0",
        "Distribution of violated stoichiometric rows by magnitude, one flowing band per "
        "model (darker = smaller model, brighter = larger).",
    )

    con_entries = _load_entries("violation_histogram_constraints")
    if con_entries:
        _pyramid_figure(
            con_entries, CONSTRAINTS_OUT,
            "Coupling constraint violations under per_constraint_residual=0",
            "Distribution of violated coupling rows by magnitude, models with a coupling "
            "block only (darker = smaller model, brighter = larger).",
        )
    else:
        print("no models with a coupling block found; skipping", CONSTRAINTS_OUT)


if __name__ == "__main__":
    main()
