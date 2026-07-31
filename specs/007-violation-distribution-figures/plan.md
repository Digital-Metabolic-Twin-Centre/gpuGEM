# Implementation Plan: Violation Distribution Figures for per_constraint_residual=0

**Branch**: `007-violation-distribution-figures` | **Date**: 2026-07-31 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/007-violation-distribution-figures/spec.md`

## Summary

Extend feature 005's `per_constraint_residual=0` trade-off benchmark to cover all nine models now
in the suite (not just the original five), and add two new figures — population-pyramid-style
mirrored histograms — showing the full distribution of mass-balance-equation and coupling-constraint
violations under that setting, not just the single worst-row number already captured. Requires: (1)
running the existing `run_residual_tradeoff.py --all` against the now-nine-model registry (no
orchestration code change, per research R1), (2) capturing full signed per-row violation data as
binned histograms at solve time (new, small `benchmarks/violation_histogram.py` module), (3) a
one-time backfill of the histogram fields for the original five models' already-committed results,
and (4) two new figure-generation entry points plus a width fix for the existing runtime comparison
figure at nine models.

## Technical Context

**Language/Version**: Python 3.10+ (matches `pyproject.toml` floor)

**Primary Dependencies**: numpy, scipy (sparse), matplotlib (Agg backend), pandas — all already
project dependencies; no new dependency introduced.

**Storage**: Committed JSON result files (`benchmarks/results/residual_tradeoff/<model>.json`) and
a committed CSV (`comparison.csv`) — same convention as every prior benchmark feature.

**Testing**: `pytest`, extending `tests/test_residual_tradeoff.py`'s pattern with a new
`tests/test_violation_histogram.py` for the pure signed-violation and binning functions.

**Target Platform**: Linux + NVIDIA GPU for the solve step (`run_residual_tradeoff.py`); figure
regeneration (`make_violation_distribution_figures.py`) runs anywhere with no GPU.

**Project Type**: Single project — benchmarking/analysis scripts under `benchmarks/`, no change to
the `gpugem` library itself.

**Performance Goals**: N/A (benchmark tooling, not a service); the solve step's own runtime is the
subject being measured, not a target for this feature's code.

**Constraints**: Result files must stay small even for S85-scale models (~734K S-block rows, ~1.26M
C-block rows) — addressed by histogram binning, never raw per-row persistence (research R2). Both
new figures must regenerate from committed data alone, no solver installed (FR-010).

**Scale/Scope**: 9 models x 1 fresh-or-backfilled `per_constraint_residual=0` solve each (4 fresh,
5 backfilled) x 2 row populations (S-block always, C-block for 7 of 9 models) x 24 histogram bins
each. Two new figures, one extended figure, one new small module, one new test file.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Correctness-Validated Defaults**: PASS. `gpugem/_defaults.py` untouched;
  `per_constraint_residual=0` remains explicitly non-default and non-recommended, restated in every
  new figure's caption (FR-011).
- **II. Honest Status/Feasibility Reporting**: PASS. This feature strictly increases the honesty and
  granularity of what's reported about `per_constraint_residual=0`'s correctness cost — no
  regression risk.
- **III. Test Coverage for Numerical Behavior**: PASS. New pure functions (signed row violation,
  histogram binning) get synthetic-input unit tests in `tests/test_violation_histogram.py`; no
  change to `gpugem/solver.py`, `scaling.py`, or `_defaults.py`, so this feature doesn't itself
  trigger that principle's mandate on the library, but follows its spirit for the new benchmark code.
- **IV. Minimal, COBRA-Compatible Surface**: PASS. No `gpugem` public API change; all new code is
  under `benchmarks/`.
- **V. Documented Known Limitations**: PASS. No new solver limitation discovered; extends existing
  README documentation of the `per_constraint_residual` trade-off (005/006 precedent).

No violations. Re-checked after Phase 1 design (research.md/data-model.md/contracts above) — still
PASS, no new considerations introduced by the design.

## Project Structure

### Documentation (this feature)

```text
specs/007-violation-distribution-figures/
├── plan.md              # This file
├── research.md           # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/
│   ├── result-json-extension.md
│   └── figure-contract.md
└── tasks.md              # Phase 2 output (/speckit-tasks, not yet created)
```

### Source Code (repository root)

```text
benchmarks/
├── violation_histogram.py            # NEW: signed_row_violations(), histogram(), MAGNITUDE_BIN_EDGES
├── run_residual_tradeoff.py          # MODIFIED: _solve_residual_0 computes+stores both histograms;
│                                      #           run_model() backfills old-format files (research R4)
├── make_violation_distribution_figures.py   # NEW: the two population-pyramid figures
├── make_residual_tradeoff_figures.py # MODIFIED: figsize width fix for 9 models (research R7)
├── results/residual_tradeoff/
│   ├── e_coli_core.json ... S83.json # 5 backfilled in place, 4 newly created
│   └── comparison.csv                # regenerated, 27 rows
├── figures/
│   ├── residual_tradeoff_solvetime.png      # regenerated, 9 models
│   ├── residual_tradeoff_violations.png     # regenerated, 9 models
│   ├── violation_distribution_equations.png # NEW
│   └── violation_distribution_constraints.png # NEW
└── README.md                          # MODIFIED: document the two new figures + backfill behavior

tests/
└── test_violation_histogram.py       # NEW: pure-function tests (signed violation, binning, zero/edge handling)
```

**Structure Decision**: single project, benchmarks-only change (matches 004/005/006's precedent —
no `gpugem/` library code touched). One new module (`violation_histogram.py`) rather than growing
`residual.py`, since it's a distinct concern (full-vector binning vs. scalar worst-case) with its
own shared constant (`MAGNITUDE_BIN_EDGES`) that both the solve step and the figure step must import
identically.

## Complexity Tracking

*No Constitution Check violations — this section is not needed.*
