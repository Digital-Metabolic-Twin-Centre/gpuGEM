# Contract: `_ordinal_ramp(n)` and band draw order

## `_ordinal_ramp(n) -> list[str]`

Pure function, `benchmarks/make_violation_distribution_figures.py`. Given a model count `n >= 2`,
returns `n` hex colors, index `0` = lightest (smallest model), index `n-1` = darkest (largest
model), satisfying data-model.md's invariant (monotone OKLCH L, adjacent ΔL >= 0.06, light-end
contrast >= 2.0:1, single hue).

Construction (research R2):
```python
LIGHT_HEX = "#86b6ef"   # dataviz skill's reference blue, step 250 — passes 2.06:1 light-end contrast
DARK_HEX  = "#0d366b"   # dataviz skill's reference blue, step 700 — hue/chroma trajectory reference
MIN_DL    = 0.063       # > the 0.06 ordinal floor, small safety margin

def _ordinal_ramp(n):
    L0, a0, b0 = _hex_to_oklab(LIGHT_HEX)
    L1, a1, b1 = _hex_to_oklab(DARK_HEX)
    dark_L = L0 - (n - 1) * MIN_DL
    return [_oklab_to_hex(L0 + t*(dark_L-L0), a0 + t*(a1-a0), b0 + t*(b1-b0))
            for t in (i/(n-1) for i in range(n))]
```

Verified (research R2) for the two concrete cases this project needs today:
- `_ordinal_ramp(10)` == `["#86b6ef","#73a2da","#618ec6","#4e7bb2","#3d689f","#2b568b","#1a4478","#073266","#002154","#000f42"]`
- `_ordinal_ramp(8)` == `["#86b6ef","#73a2db","#618ec6","#4f7bb3","#3d689f","#2c568c","#1b4379","#083266"]`

(Exact hex values may shift by a tiny rounding amount depending on floating-point path; the test
this contract implies checks the *properties* — monotone, ΔL >= 0.06, contrast, hue spread — not
byte-exact hex strings, so it isn't brittle to insignificant rounding differences.)

## Band draw order and opacity

In `_pyramid_figure`, for `entries` sorted ascending by `n_cols` (existing convention, `rank` = index):

```python
n = len(entries)
colors = _ordinal_ramp(n)
for rank, (model, n_cols, hist) in enumerate(entries):
    color = colors[rank]
    z = n - 1 - rank          # smallest model (rank 0) drawn last -> frontmost
    ax.fill_betweenx(..., color=color, alpha=BAND_ALPHA, zorder=z)
```

`BAND_ALPHA` replaces the current `0.42` literal; starting point ~0.7 per research R3, confirmed by
rendering both figures and visually checking every model's band (including the now-backmost
largest model) remains individually identifiable — no fixed number is contractually mandated
beyond spec FR-004's "no band becomes fully hidden."

## Unchanged

`_smooth_curve`, `_label_anchor`, `_label_angle`, `_load_entries`, the negligible-model shelf logic,
axis/title/caption styling, and both `main()` entry points are untouched — this feature only
changes how `color`/`zorder`/`alpha` are computed and assigned per model.
