# Phase 1 Data Model: Colorblind-Friendly, Clearly-Layered Violation Distribution Figures

## ModelBandStyle (new — rendering-only, not persisted)

Computed per model, per figure, from that model's size rank (`0` = smallest) within that figure's
own set of `n` models (data-model.md's existing `ModelBandStyle` concept from the spec, now given a
concrete formula):

| Field | Formula | Notes |
|---|---|---|
| `color` | `_ordinal_ramp(n)[rank]` | Single-hue OKLCH-constructed ramp (research R2); light = smallest, dark = largest, monotone, validated ΔL ≥ 0.06 for whatever `n` the figure has. |
| `zorder` | `n - 1 - rank` | Reversed from the current `rank` (research R3) — smallest model highest zorder (frontmost), largest lowest (backmost). |
| `alpha` | fixed, figure-wide (~0.7, tuned per research R3) | No longer needs to be low enough to let a hidden band "show through," since the draw order now prevents any band from being fully covered. |

Both existing figures (`violation_distribution_equations.png`,
`violation_distribution_constraints.png`) already have all the other inputs this needs (model list
sorted by `n_cols`, per spec Assumptions each figure computes its own `n` and ranks independently)
— no new data is read or persisted; this is purely how `_pyramid_figure` styles each model's
already-existing fill/line calls.

## Invariant

For any `n >= 2`: the `n`-element ramp `_ordinal_ramp(n)` has strictly monotone decreasing OKLCH
lightness, every adjacent pair's `|ΔL| >= 0.06`, the lightest element clears 2.0:1 WCAG contrast
against the figure's white background, and every element shares the same hue family (OKLab hue
spread across all elements <= 40°). This is exactly what research R2's construction guarantees by
formula, and what the new unit test (research R4) checks directly.
