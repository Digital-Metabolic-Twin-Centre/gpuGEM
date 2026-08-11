# Implementation Plan: Colorblind-Friendly, Clearly-Layered Violation Distribution Figures

**Branch**: `009-distribution-figure-clarity` | **Date**: 2026-08-05 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/009-distribution-figure-clarity/spec.md`

## Summary

Replace the two violation-distribution figures' viridis-based, rank-sampled color assignment —
which was measurably failing this project's own ordinal-ramp accessibility check (not a single
hue, adjacent steps too close, lightest step below the contrast floor) — with a single-hue blue
ramp constructed directly in OKLCH space that passes all four checks for any model count. Reverse
the current z-order (largest model currently drawn frontmost) so smaller models draw on top of
larger ones, which removes the reason the fill opacity was kept low, and raise it for a more vivid
figure without any band becoming hidden. Purely a rendering change to
`make_violation_distribution_figures.py`; no data captured, computed, or persisted by any benchmark
script changes.

## Technical Context

**Language/Version**: Python 3.10+ (matches `pyproject.toml` floor)

**Primary Dependencies**: numpy, matplotlib (Agg) — already project dependencies. No new
dependency (the OKLCH conversion math is ~15 lines of standard, published constants, implemented
inline rather than adding a color-science library for this one use).

**Storage**: N/A — reads existing committed JSON, writes existing PNG paths; no schema change.

**Testing**: `pytest`. New tests for `_ordinal_ramp(n)` reimplement the relevant computable
property checks (monotone OKLCH lightness, adjacent ΔL >= 0.06, light-end contrast >= 2.0:1, single
hue) directly, rather than depending on the dataviz skill's external validator script at runtime
(that script lives outside this repository and was used only to *derive* and *spot-check* the
constants during planning — research R1/R2).

**Target Platform**: Anywhere — figure regeneration needs no GPU/solver, matching the existing
reproducibility convention for these figures.

**Project Type**: Single project — one file modified (`benchmarks/make_violation_distribution_figures.py`),
one test file extended. No `gpugem/` change.

**Performance Goals**: N/A (a few KB of extra pure-Python color math per figure regeneration,
negligible next to the existing PCHIP interpolation and label-placement search already in that
file).

**Constraints**: Every model's band must remain individually distinguishable (spec FR-004) after
both the z-order reversal and the opacity increase — verified visually, not just by the ramp's own
color-distance checks, since opacity/overlap interacts with perceived color in a way the ramp
validator alone doesn't model.

**Scale/Scope**: One new pure function (`_ordinal_ramp`), two call sites changed (`zorder=` and the
`CMAP(frac)` color lookup in `_pyramid_figure`), one constant (`BAND_ALPHA`) replacing a literal,
one new test function group, two regenerated PNGs.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Correctness-Validated Defaults**: PASS — not implicated; `gpugem/_defaults.py` untouched.
- **II. Honest Status/Feasibility Reporting**: PASS — not implicated; no change to what's computed
  or reported, only how already-correct, already-persisted data is drawn.
- **III. Test Coverage for Numerical Behavior**: PASS, directly addressed — `_ordinal_ramp`'s
  computed color properties get their own unit test (research R4), rather than relying on
  eyeballing or a script outside this repository, matching this principle's spirit even though the
  literal principle text is scoped to `gpugem/`.
- **IV. Minimal, COBRA-Compatible Surface**: PASS — no `gpugem` public API change; all changes
  under `benchmarks/`.
- **V. Documented Known Limitations**: PASS — no new limitation introduced; nothing to document.

No violations. Re-checked after Phase 1 design (research.md/data-model.md/contracts above) — still
PASS.

## Project Structure

### Documentation (this feature)

```text
specs/009-distribution-figure-clarity/
├── plan.md              # This file
├── research.md           # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/
│   └── ordinal-ramp-and-layering.md
└── tasks.md              # Phase 2 output (/speckit-tasks, not yet created)
```

### Source Code (repository root)

```text
benchmarks/
├── make_violation_distribution_figures.py   # MODIFIED: _ordinal_ramp() replaces CMAP/viridis;
│                                             #           zorder reversed; BAND_ALPHA raised
└── figures/
    ├── violation_distribution_equations.png    # regenerated
    └── violation_distribution_constraints.png  # regenerated

tests/
└── test_violation_histogram.py   # MODIFIED: new tests for _ordinal_ramp's color properties
```

**Structure Decision**: single project, one-file rendering change (matches every prior benchmark
feature's precedent of touching only `benchmarks/` — no `gpugem/` code involved). No new module;
`_ordinal_ramp` is added alongside the existing pure helper functions
(`_smooth_curve`/`_label_anchor`/`_label_angle`) already in `make_violation_distribution_figures.py`,
following that file's own established pattern rather than introducing a new one for a single small
function.

## Complexity Tracking

*No Constitution Check violations — this section is not needed.*
