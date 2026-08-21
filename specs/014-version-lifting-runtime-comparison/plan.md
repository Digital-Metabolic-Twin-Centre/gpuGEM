# Implementation Plan: Version x Lifting Runtime Comparison

**Branch**: `014-version-lifting-runtime-comparison` | **Date**: 2026-08-21 | **Spec**: ./spec.md

**Input**: Feature specification from `/specs/014-version-lifting-runtime-comparison/spec.md`

## Summary

Extend `benchmarks/figures/benchmark_solvetime.png` from 2 bars per model (Gurobi,
current-version-unlifted cuOpt) to 5, for exactly six models (e_coli_core, iML1515, Harvey,
Harvetta, S84, S85), by adding cuOpt (newer version, unlifted), cuOpt (current version, lifted),
and cuOpt (newer version, lifted). Of the 24 total (model x configuration) data points, 8 already
exist (research.md R3: 6 from `specs/002-benchmark-cuopt-gurobi/`'s `benchmark.csv`, 2 from
`specs/013-cobra-model-lifting/`'s lifted-model validation — including S85's already-known
correctness-gate failure, carried through honestly rather than re-litigated) and are reused
verbatim; the remaining 16 are freshly solved by one new, model-agnostic subprocess worker
(research.md R5), launched under either the shared environment (current version) or the isolated
venv already provisioned in `specs/012-cuopt-native-tuning/` (newer version, re-provisioned
automatically if the venv no longer exists). A new, derived CSV and figure script — never
mutating `benchmark.csv`/`make_figure.py` in place — produce the extended figure, following this
project's existing "derived comparison figure" precedent (`specs/010-.../
gurobi_default_comparison.png`).

## Technical Context

**Language/Version**: Python 3.13, matching every other `benchmarks`/`gpugem` module.

**Primary Dependencies**: `gpugem` (unmodified — `lift`/`lift_big` from `specs/013-.../` used
as-is), `cuopt-cu12` (26.6.0 shared env + 26.8.0 isolated venv, both already established),
`gurobipy` (read-only — Gurobi's existing numbers are reused, never re-solved), `pandas`,
`matplotlib`, `numpy`, `scipy`. No new third-party dependency.

**Storage**: `benchmarks/results/version_lifting/<model>.json` (new, one per in-scope model, only
the freshly-solved configurations), `benchmarks/results/version_lifting_comparison.csv` (new,
derived), `benchmarks/figures/benchmark_solvetime.png` (existing path, superseded content for the
six in-scope models — research.md R6).

**Testing**: `pytest` for the aggregation/CSV-row-building logic (synthetic inputs, no GPU) and
the correctness-gate reuse (confirming the same gate function from `specs/013-.../` is actually
called, not reimplemented) — Constitution Principle III does not strictly require this (no
`gpugem/` file is touched by this feature), but this project's established `benchmarks/` testing
convention applies regardless. Actual solves are exercised on the GPU host per `quickstart.md`.

**Target Platform**: Linux GPU host with cuOpt (both versions) and Gurobi — same host as every
prior benchmark feature.

**Project Type**: single project — entirely new `benchmarks/` tooling; no `gpugem/`-internal
change at all (contrast with `specs/013-.../`, which added `gpugem/lifting.py` — this feature only
*consumes* that already-shipped capability).

**Performance Goals**: N/A — this feature measures runtime, it does not target one; correctness
(spec FR-004) takes priority over any number reported.

**Constraints**: `benchmarks/results/benchmark.csv`, `benchmarks/make_figure.py`, and
`gpugem/scaling.py`/`gpugem/lifting.py` MUST NOT be modified (research.md R6; consistency with
`specs/013-.../`'s own constraint on `scaling.py`). Already-existing results (6 old-unlifted, 2
old-lifted) MUST be reused, never re-solved (spec FR-007/FR-008).

**Scale/Scope**: 6 models x up to 3 new configurations each = at most 16 fresh solves (research.md
R3's exact accounting), of which only the 3 S85-involving ones are expected to take non-trivial
wall-clock time (research.md R2's table shows every other in-scope model resolves in
single-digit-to-tens of seconds under the already-published old-version baseline).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Correctness-Validated Defaults**: PASS — this feature changes no shipped default; it only
  measures runtime under settings (`lift`, cuOpt version) already established and validated
  elsewhere. No new default is proposed.
- **II. Honest Status/Feasibility Reporting**: PASS — every new number is gated by the exact same
  correctness check used throughout this project (research.md R7), and a known failure (S85,
  old-lifted) is carried through and visibly shown, never hidden (spec FR-004/User Story 2).
- **III. Test Coverage for Numerical Behavior**: N/A strictly (no `gpugem/` file touched), but the
  new aggregation/gating logic still gets dedicated unit tests matching this project's established
  `benchmarks/` convention.
- **IV. Minimal, COBRA-Compatible Surface**: PASS — no `gpugem` public surface change at all.
- **V. Documented Known Limitations**: APPLIES CONDITIONALLY — if any of the 16 fresh solves
  surfaces a new correctness failure beyond the already-known S85 one, it MUST be recorded in
  `README.md`'s Known Limitations, matching every prior feature's precedent.
- **VI. Publication-Ready Figure Standards**: APPLIES — the extended `benchmark_solvetime.png`
  MUST continue to meet this project's figure standards (CVD-safe color assignment for the now-up-
  to-5-way categorical comparison per model, PDF vector copy, no baked-in captions belonging in a
  manuscript instead). Five colors across a fixed category (Gurobi + 4 cuOpt configurations) is a
  larger categorical set than the original figure's 2 — assigned in a fixed, documented order,
  never re-cycled per model.

No unjustified violations. No Complexity Tracking entries needed (no new `gpugem` surface, no
default changes).

## Project Structure

### Documentation (this feature)

```text
specs/014-version-lifting-runtime-comparison/
├── plan.md              # This file (/speckit-plan command output)
├── research.md           # Phase 0 output (/speckit-plan command) — R1-R7
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md         # Phase 1 output (/speckit-plan command)
├── contracts/            # Phase 1 output (/speckit-plan command)
└── tasks.md              # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
benchmarks/
├── models.py                              # existing — reused unchanged: build_lp(name)
├── residual.py                            # existing — reused unchanged: correctness gate
├── run_benchmark.py                       # existing — UNCHANGED (research.md R6); its
│                                            #   benchmark.csv is read, never written, by this
│                                            #   feature
├── make_figure.py                         # existing — UNCHANGED; remains independently
│                                            #   runnable, regenerates today's narrower 2-bar view
├── run_model_lifting_validation.py        # existing (specs/013) — its build_comparison /
│                                            #   scale_report functions reused as library calls,
│                                            #   not reimplemented (research.md R5/R7)
├── run_cuopt_tuning.py                    # existing (specs/012) — its isolated-venv
│                                            #   provisioning command reused verbatim
│                                            #   (research.md R4), not its S85-specific worker
├── _version_lifting_worker.py             # NEW: model-agnostic subprocess entry point --
│                                            #   --model NAME --lift/--no-lift, prints one
│                                            #   RuntimeConfiguration JSON to stdout
├── run_version_lifting_comparison.py      # NEW: orchestrator -- determines which of the 16
│                                            #   combinations are missing (research.md R3),
│                                            #   provisions/reuses the isolated venv, launches
│                                            #   _version_lifting_worker per missing combination,
│                                            #   writes results/version_lifting/<model>.json
├── aggregate_version_lifting_comparison.py # NEW: reads benchmark.csv + results/version_lifting/
│                                            #   *.json + specs/013's model_lifting/*.json ->
│                                            #   results/version_lifting_comparison.csv
├── make_extended_solvetime_figure.py      # NEW: reads version_lifting_comparison.csv ->
│                                            #   figures/benchmark_solvetime.png (up to 5 bars/
│                                            #   model, graceful 2-bar fallback per row)
├── results/
│   └── version_lifting/
│       └── <model>.json                    # one per in-scope model, only the freshly-solved
│                                             #   configurations
│   └── version_lifting_comparison.csv       # derived, all 10 models, 5-way where in-scope
└── README.md                               # existing -- append a section for this comparison

tests/
└── test_version_lifting_comparison.py     # NEW: aggregation/row-building and gate-reuse tests
                                             #   on synthetic data (no GPU/Gurobi required)
```

**Structure Decision**: Single project, entirely new `benchmarks/` tooling reusing three prior
features' already-established building blocks (`specs/002`'s `benchmark.csv`, `specs/012`'s
isolated-venv approach, `specs/013`'s `lift=True` and its comparison/gating functions) rather than
re-deriving any of them. No `gpugem/`-internal change — the smallest footprint of any feature so
far that builds on the cuOpt-tuning/lifting work.

## Complexity Tracking

*No entries — no `gpugem` public surface change, no default changes, no Constitution Check
violations requiring justification.*
