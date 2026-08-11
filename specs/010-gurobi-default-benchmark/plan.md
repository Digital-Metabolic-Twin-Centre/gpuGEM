# Implementation Plan: Gurobi Default-Settings Benchmark Across All Models

**Branch**: `010-gurobi-default-benchmark` | **Date**: 2026-08-11 | **Spec**: ./spec.md

**Input**: Feature specification from `/specs/010-gurobi-default-benchmark/spec.md`

## Summary

Add a `benchmarks/` tool that, for every model already in the main cross-scale cuOpt-vs-Gurobi
comparison, solves fresh with Gurobi's `Method` parameter left at its own untouched factory
default (`-1`, automatic algorithm selection) — reusing, never re-solving, each model's already-
recorded cuOpt result and deliberately-configured-Gurobi (`method=2`, barrier) result — and
produces a three-way `comparison.csv` and one regenerable solve-time figure showing cuOpt, Gurobi
barrier, and Gurobi default side by side per model. `gpugem/_defaults.py` and this project's
shipped Gurobi wrapper defaults are never touched; only a different argument value is passed
through the existing `solve_gurobi` function.

## Technical Context

**Language/Version**: Python 3.13 (host base conda env — same as every prior benchmark feature)

**Primary Dependencies**: gurobipy (only for the new default-settings solves — not needed to
regenerate the CSV or figure), matplotlib + pandas (figure generation, same as
`make_residual_tradeoff_figures.py`), the in-repo `benchmarks` package (`models.build_lp`,
`solve.solve_gurobi`, `residual.feasibility_residual`), all reused unchanged except for the
additive `bar_iters`/`simplex_iters` extension to `solve_gurobi`'s return dict (research R2).

**Storage**: `benchmarks/results/gurobi_default/<model>.json` (one per model, the new
default-settings solve's stats), `benchmarks/results/gurobi_default/comparison.csv` (aggregated,
figure-source-of-truth, mirroring feature 005's `comparison.csv` convention),
`benchmarks/figures/gurobi_default_comparison.png`.

**Testing**: `pytest` for the `solve_gurobi` return-dict extension (`bar_iters`/`simplex_iters`
present and additive — existing callers unaffected), the comparison-table assembly logic (reading
an existing model's `results/<model>.json` + merging in a fresh default-settings result, on
synthetic data — no GPU/Gurobi needed), and the correctness-gate-failure path (spec FR-003: a
failed gate is recorded and marked, never silently dropped from the CSV). Actual solves are
exercised on a host with Gurobi licensed, per `quickstart.md`.

**Target Platform**: Linux host with Gurobi licensed for producing fresh results — same
requirement as every prior Gurobi-touching benchmark feature. Regenerating `comparison.csv` or the
figure needs neither Gurobi nor cuOpt installed (spec FR-007).

**Project Type**: single project — extends `benchmarks/` in place, no `gpugem/` changes at all;
the one `benchmarks/solve.py` edit is additive (two new dict keys), not a behavior change to any
existing call site.

**Performance Goals**: not a latency target — the deliverable is the *comparison itself*: for
each model, Gurobi's out-of-the-box runtime next to the project's existing cuOpt and
deliberately-configured-Gurobi numbers (spec User Story 1).

**Constraints**: MUST NOT modify `gpugem/_defaults.py` or this project's shipped Gurobi wrapper
default (`solve_gurobi`'s `method=2` default argument) under any outcome, including if default
settings turn out faster on some model (spec FR-008/SC-004) — publishing that data point is the
entire point of this feature, adopting it is a separate, out-of-scope decision. Each new solve
reuses the same per-model `time_limit` already recorded in the model's existing JSON, for a fair
timing comparison (spec Assumptions).

**Scale/Scope**: every model in the main benchmark suite, 1 new solve per model (only the
default-settings configuration — the other two configurations per model are reused, not solved),
1 output figure. Explicitly excludes the separate, narrower Harvey two-demand two-method
comparison (spec Edge Cases, Assumptions).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Correctness-Validated Defaults**: PASS — this feature never edits `_defaults.py` or the
  shipped `solve_gurobi` default; it adds one more, equally-valid, equally-supported data point
  (Gurobi's own factory default) without proposing it as a replacement (spec FR-008, Assumptions).
- **II. Honest Status/Feasibility Reporting**: PASS, and central to the feature's purpose — a
  default-settings solve that fails the correctness gate is recorded and clearly marked, never
  silently included in the comparison as if it had passed (spec FR-003). Uses the same
  `benchmarks.residual.feasibility_residual` and status vocabulary already used everywhere else in
  this project, not a bespoke or looser calculation.
- **III. Test Coverage for Numerical Behavior**: N/A for `gpugem` — no `gpugem/solver.py`,
  `scaling.py`, or `_defaults.py` changes. The `solve_gurobi` extension and the new
  `benchmarks/` comparison-assembly logic get `pytest` coverage per the Testing field above.
- **IV. Minimal, COBRA-Compatible Surface**: PASS — zero new `gpugem` public surface; the one
  `benchmarks/solve.py` change is additive dict keys on an already-internal helper, not a public
  API change.
- **V. Documented Known Limitations**: N/A — no new solver limitation discovered; this feature
  documents a performance comparison, not a correctness caveat requiring a `README.md` update.
- **VI. Publication-Ready Figure Standards** (v1.2.0): the low-cost, unambiguous parts (a
  CVD-validated palette reused from the already-validated `CONFIG_COLOR` triple — research R5;
  professional axis/legend phrasing; no internal-setting jargon baked into labels) are applied
  directly to `gurobi_default_comparison.png`. This feature does **not** additionally build the
  full browsing-PNG + journal-PDF + companion-caption treatment established for the
  violation-distribution figures (features 007/009) — that is a presentation-format decision
  spanning every figure this project already has, not something to bundle silently into a
  data-content feature; it stays a separate, explicit follow-up unless requested.

No violations. Complexity Tracking left empty.

## Project Structure

### Documentation (this feature)

```text
specs/010-gurobi-default-benchmark/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
benchmarks/
├── models.py                          # existing — reused unchanged: build_lp(name) for every
│                                       #   model in the main suite
├── solve.py                           # EXTENDED: solve_gurobi's return dict gains bar_iters/
│                                       #   simplex_iters (already-computed values it currently
│                                       #   discards after collapsing into `iters`) — additive,
│                                       #   every existing caller unaffected (research R2)
├── residual.py                        # existing — reused unchanged: feasibility_residual
├── run_gurobi_default_benchmark.py    # NEW: orchestrator — for each model, load the existing
│                                       #   results/<model>.json (cuOpt + deliberately-configured
│                                       #   Gurobi, both reused/not re-solved), solve fresh with
│                                       #   solve_gurobi(lp, time_limit=..., method=-1), apply the
│                                       #   correctness gate, write
│                                       #   results/gurobi_default/<model>.json
├── aggregate_gurobi_default.py        # NEW: reads results/gurobi_default/*.json + each model's
│                                       #   existing results/<model>.json -> comparison.csv
│                                       #   (one row per model, three configurations)
├── make_gurobi_default_figure.py      # NEW: reads comparison.csv -> one PNG (solve time), no
│                                       #   solver import, matplotlib/Agg style matching
│                                       #   make_figure.py / make_residual_tradeoff_figures.py
├── results/
│   └── gurobi_default/
│       ├── <model>.json               # one per model: the new default-settings solve's stats
│       └── comparison.csv             # aggregated, figure source of truth
├── figures/
│   └── gurobi_default_comparison.png
└── README.md                          # existing — append a short section for this benchmark

tests/
└── test_gurobi_default_benchmark.py   # NEW: solve_gurobi's bar_iters/simplex_iters extension,
                                        #   comparison-assembly logic (merging reused + fresh
                                        #   results), and the correctness-gate-failure path, all
                                        #   on synthetic data, no GPU/Gurobi required
```

**Structure Decision**: Single project, extending `benchmarks/` in place exactly like features
002-005. Mirrors feature 005's already-established "reuse two configs, add one new, never touch
the reused ones" pattern precisely (research R3), including the dedicated `results/gurobi_default/`
subdirectory so results don't collide with any prior feature's output. No subprocess isolation
needed for the new solve: `method=-1` is Gurobi's own long-established, fully-supported default
behavior, not an untested/crash-risk setting — a plain call through the existing `solve_gurobi`
function is sufficient.

## Complexity Tracking

*No Constitution Check violations — this section is intentionally empty.*

**Post-Phase-1 re-check**: data-model.md, contracts/, and quickstart.md confirm zero `gpugem/`
changes, one small additive `benchmarks/solve.py` extension, and zero new public surface — every
new file lives in `benchmarks/` and calls existing, unchanged `benchmarks` functions plus the one
additive `solve_gurobi` extension. Gate still PASSES.
