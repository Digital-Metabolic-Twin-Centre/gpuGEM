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
import matplotlib.transforms as mtransforms
import numpy as np
from scipy.interpolate import PchipInterpolator

from benchmarks.make_residual_tradeoff_figures import NON_RECOMMENDATION_NOTICE

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results" / "residual_tradeoff"
FIGURES = HERE / "figures"
EQUATIONS_OUT = FIGURES / "violation_distribution_equations.png"
CONSTRAINTS_OUT = FIGURES / "violation_distribution_constraints.png"
EQUATIONS_JOURNAL_OUT = FIGURES / "violation_distribution_equations_journal.tiff"
CONSTRAINTS_JOURNAL_OUT = FIGURES / "violation_distribution_constraints_journal.tiff"
CAPTIONS_OUT = FIGURES / "violation_distribution_captions.md"

# Oxford Academic's *Bioinformatics* journal instructions for authors: figures at
# 350 dpi (combination color+line art; 1200 dpi is for pure line art only), sized to
# fit a single (86 mm) or double (178 mm) print column, submitted as .tif/.eps/.jpg/
# .gif. TIFF is used here rather than EPS -- EPS has no native alpha-transparency
# support, and this chart's overlapping-band design depends on it (BAND_ALPHA); a
# raster at journal DPI keeps the already-composited transparency intact instead of
# flattening or rejecting it. Double column (not single) because a legend-column
# chart with up to 10 series is illegible much narrower than that.
JOURNAL_DPI = 350
JOURNAL_WIDTH_IN = 178 / 25.4

INK = "#2b2b2b"
MUTED = "#6b6b6b"
# Safe to keep fairly high (vs. the 0.42 this replaces) now that smaller models draw
# in front of larger ones (see the zorder = n - 1 - rank assignment below) -- no band
# can be fully buried by a wider one anymore, so a more vivid fill no longer risks
# hiding a model's data (research R3).
BAND_ALPHA = 0.7
GRID = "#e4e4e0"

# Fixed, diverse categorical palette assigned by model-size rank (index 0 = smallest,
# never cycled), replacing an earlier single-hue ordinal ramp: that ramp passed the
# colorblind-safety checks but read as visually monotonous with 8-10 steps of "the
# same blue" (direct user feedback). The first 8 colors are the dataviz skill's own
# reference categorical palette (already validated, worst adjacent CVD delta-E 24.2);
# the last 2 (a cyan and a plum) were added by grid search over hue/lightness/chroma to
# maximize the worst-case CIE76 delta-E, simulated under protanopia/deuteranopia/
# tritanopia, against all 8 existing colors and each other -- a first attempt that
# picked 2 hues close to the existing magenta/violet (by raw hue angle) scored fine
# numerically but visually clustered in one part of the color wheel, so the search was
# re-run constrained to the two largest uncovered hue gaps instead. Verified with the
# dataviz skill's `validate_palette.py --pairs all` (all 10 colors can be neighbors in
# this chart, not just adjacent ranks): all checks pass; worst pair is still the
# original palette's own orange/green pair (CVD delta-E 11.2, floor-band, legal given
# this chart's existing direct labels as the required secondary encoding).
CATEGORICAL_PALETTE = [
    "#2a78d6",  # blue
    "#1baf7a",  # aqua
    "#eda100",  # yellow
    "#008300",  # green
    "#4a3aa7",  # violet
    "#e34948",  # red
    "#e87ba4",  # magenta
    "#eb6834",  # orange
    "#00b6ff",  # cyan
    "#8d4383",  # plum
]


def _rank_colors(n):
    """First n colors of the fixed categorical palette, one per model rank. Raises if
    a figure ever needs more models than the palette has slots -- silently cycling
    hues would make two unrelated models indistinguishable, which is worse than a
    loud failure telling us to deliberately extend and re-validate the palette."""
    if n > len(CATEGORICAL_PALETTE):
        raise ValueError(
            "need %d colors but CATEGORICAL_PALETTE only has %d -- extend and "
            "re-validate it (see the module docstring comment above), don't cycle" %
            (n, len(CATEGORICAL_PALETTE)))
    return CATEGORICAL_PALETTE[:n]


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


def _declutter_y(ax, items, min_gap_px=22):
    """items: [(key, y_ideal), ...]. Returns {key: y_final}, each on-screen Y at
    least `min_gap_px` from its neighbors (sorted order preserved), adjusted the
    minimum amount necessary -- an item that already has room keeps its ideal Y
    exactly. All labels now render in a single aligned right-margin column (straight,
    horizontal text, one shared x) rather than rotated and anchored directly on each
    model's own curve, so the only remaining placement problem is 1-D: don't let two
    labels' rows collide."""
    scored = sorted(((key, y, ax.transData.transform((0, y))[1]) for key, y in items),
                     key=lambda t: t[2])
    inv = ax.transData.inverted()
    result = {}
    prev_py = -np.inf
    for key, y, py in scored:
        target_py = max(py, prev_py + min_gap_px)
        prev_py = target_py
        result[key] = inv.transform((0, target_py))[1]
    return result


def _pyramid_figure(entries, out_path, title, subtitle, journal=False):
    """journal=True renders a submission-ready variant instead of the repo/browsing
    one: fixed double-column width (not scaled by model count), no title/subtitle/
    caveat baked into the image (those belong in the manuscript's external figure
    caption per standard journal convention -- see `main()`'s companion .md file),
    and saved as 350 dpi TIFF instead of 300 dpi PNG."""
    n = len(entries)
    if journal:
        fig, ax = plt.subplots(figsize=(JOURNAL_WIDTH_IN, 5.4))
    else:
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

    colors = _rank_colors(n)

    # Axis scale and limits MUST be finalized before any pixel-space label placement
    # (_declutter_y relies on ax.transData) -- transData reflects whatever scale is
    # *currently* set, so placing labels before switching to log here would silently
    # declutter them against a linear transform while the rendered axis is actually
    # log, scrambling the vertical ordering and spacing guarantees.
    ax.set_yscale("log")
    ax.set_ylim(edges[0], edges[-1])
    xmax = global_peak * 1.05 if global_peak > 0 else 1.0
    ax.set_xlim(-xmax, xmax)

    # Draw every band, and record each model's "ideal" label Y: its true excess-side
    # peak height for a real one, or a fixed low shelf position (spread across
    # decades, not competing for the same spot) for a negligible one.
    label_items = []
    negligible_rank = 0
    for rank, (model, n_cols, hist) in enumerate(entries):
        color = colors[rank]
        # Smaller models drawn last (frontmost) so a larger model's wider band can
        # never bury a smaller one wherever they overlap -- the opposite of drawing
        # in rank order, which let the largest, most prominent band sit on top.
        z = n - 1 - rank

        (y_sf, x_sf), (y_ex, x_ex) = curves[rank]
        ax.fill_betweenx(y_sf, 0, -x_sf, color=color, alpha=BAND_ALPHA, linewidth=0, zorder=z)
        ax.fill_betweenx(y_ex, 0, x_ex, color=color, alpha=BAND_ALPHA, linewidth=0, zorder=z)
        ax.plot(-x_sf, y_sf, color=color, linewidth=0.9, alpha=0.95, zorder=z + 0.5)
        ax.plot(x_ex, y_ex, color=color, linewidth=0.9, alpha=0.95, zorder=z + 0.5)

        if peaks[rank] >= negligible_cutoff:
            y_ideal = y_ex[int(np.argmax(x_ex))]
        else:
            # Geometric (not linear) spacing so shelf entries stay evenly spread in
            # *decades* regardless of how many there are.
            y_ideal = edges[0] * 10 ** (0.5 * (negligible_rank + 1))
            negligible_rank += 1
        label_items.append((rank, y_ideal))

    # Every label -- real peak or shelf alike -- renders in one straight, aligned
    # right-margin column: horizontal text at a single shared x (axes-fraction, just
    # outside the plotted data) with a small color swatch tying it to its band, Y
    # decluttered to a minimum on-screen gap. Simpler and more legible than rotating
    # text to follow each curve at a different x, and removes any risk of a label
    # sitting inside another band's fill.
    label_y = _declutter_y(ax, label_items)
    trans = mtransforms.blended_transform_factory(ax.transAxes, ax.transData)
    for rank, y_lab in label_y.items():
        model = entries[rank][0]
        ax.plot(1.012, y_lab, marker="s", markersize=5, color=colors[rank],
                 transform=trans, clip_on=False, zorder=100)
        ax.text(1.025, y_lab, model, transform=trans, ha="left", va="center",
                 color=INK, fontsize=8, fontweight="medium", clip_on=False, zorder=100)

    ax.set_ylabel("Violation magnitude (log scale)", color=MUTED, fontsize=10)
    ax.axvline(0, color=INK, linewidth=1.0, zorder=99)

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

    fig.text(0.27, 0.075, "Shortfall", ha="center", va="top", fontsize=11, color=MUTED)
    fig.text(0.73, 0.075, "Excess", ha="center", va="top", fontsize=11, color=MUTED)

    if journal:
        # Title, subtitle, and the non-recommendation caveat move to the manuscript's
        # own figure caption (main()'s companion .md file) instead of being drawn
        # into the image -- standard journal convention keeps descriptive/caption
        # text out of the figure itself.
        fig.subplots_adjust(top=0.92, bottom=0.16, left=0.10, right=0.80)
        # Lossless LZW: uncompressed TIFF at 350 dpi for this canvas is ~18 MB, well
        # past what most submission portals accept per figure; LZW is lossless (no
        # quality tradeoff) and typically gets this under 1 MB for a mostly-flat-fill
        # chart like this one.
        fig.savefig(out_path, dpi=JOURNAL_DPI, facecolor="white", format="tiff",
                     pil_kwargs={"compression": "tiff_lzw"})
    else:
        fig.text(0.06, 0.965, title, ha="left", va="top", fontsize=16, color=INK, weight="bold")
        fig.text(0.06, 0.925, subtitle, ha="left", va="top", fontsize=10.5, color=MUTED)
        fig.text(0.06, 0.025, NON_RECOMMENDATION_NOTICE, ha="left", va="bottom",
                  fontsize=7.5, color=MUTED, style="italic", wrap=True)
        fig.subplots_adjust(top=0.87, bottom=0.15, left=0.075, right=0.85)
        fig.savefig(out_path, dpi=300, facecolor="white")
    plt.close(fig)
    print("wrote", out_path)


def _write_captions(figures):
    """Journal figures carry no in-image title/caption (standard convention -- see
    `_pyramid_figure`'s journal=True docstring); this writes the equivalent caption
    text as a companion file so it isn't lost, ready to paste into the manuscript."""
    lines = ["# Figure captions (for manuscript text, not baked into the TIFFs)\n"]
    for label, title, subtitle in figures:
        lines.append(f"**{label}.** {title}. {subtitle} {NON_RECOMMENDATION_NOTICE}\n")
    CAPTIONS_OUT.write_text("\n".join(lines))
    print("wrote", CAPTIONS_OUT)


def main():
    FIGURES.mkdir(exist_ok=True)
    captions = []

    eq_entries = _load_entries("violation_histogram_equations")
    eq_title = "Mass-balance equation violations under per_constraint_residual=0"
    eq_subtitle = ("Distribution of violated stoichiometric rows by magnitude, one labeled "
                    "band per model, smallest to largest.")
    _pyramid_figure(eq_entries, EQUATIONS_OUT, eq_title, eq_subtitle)
    _pyramid_figure(eq_entries, EQUATIONS_JOURNAL_OUT, eq_title, eq_subtitle, journal=True)
    captions.append(("Figure 1", eq_title, eq_subtitle))

    con_entries = _load_entries("violation_histogram_constraints")
    if con_entries:
        con_title = "Coupling constraint violations under per_constraint_residual=0"
        con_subtitle = ("Distribution of violated coupling rows by magnitude, models with a "
                         "coupling block only, smallest to largest.")
        _pyramid_figure(con_entries, CONSTRAINTS_OUT, con_title, con_subtitle)
        _pyramid_figure(con_entries, CONSTRAINTS_JOURNAL_OUT, con_title, con_subtitle, journal=True)
        captions.append(("Figure 2", con_title, con_subtitle))
    else:
        print("no models with a coupling block found; skipping", CONSTRAINTS_OUT)

    _write_captions(captions)


if __name__ == "__main__":
    main()
