# Implementation Plan: S85 Multi-Objective cuOpt vs Gurobi Benchmark

**Branch**: `003-s85-multi-objective-benchmark` | **Date**: 2026-07-27 | **Spec**: ./spec.md

**Input**: Feature specification from `/specs/003-s85-multi-objective-benchmark/spec.md`

## Summary

Add a `benchmarks/s85_objectives/` sweep that re-solves the mWBM S85 model (874,634
variables) with both cuOpt (gpuGEM shipped defaults) and Gurobi standalone across ~20
distinct, biologically meaningful single-reaction objectives — organ/tissue biomass
maintenance, microbiome-taxon biomass, and the model's whole-body objective — instead of
just the one whole-body objective the existing cross-scale benchmark (`002-benchmark-
cuopt-gurobi`) used. Each (objective, solver) solve reuses the existing LP builder,
solver wrappers, and correctness gate from `benchmarks/`, prints start/elapsed/finish
progress (plus a periodic heartbeat during long blocking solves) so a multi-hour run is
observable, and is individually resumable/skippable like the existing `--all` runner.
Results land in per-objective JSON plus one aggregated CSV/summary that reports the
average and spread of each solver's runtime across the set and flags outliers — directly
answering whether S85's ~10x cuOpt/Gurobi gap on the biomass objective generalizes.

## Technical Context

**Language/Version**: Python 3.13 (host base conda env — same as `002`)

**Primary Dependencies**: cuopt-cu12 26.6.0, gurobipy 13.0.2, scipy, numpy — plus the
in-repo `gpugem` package (`loaders`, `solve`) and the existing `benchmarks` package
(`models.build_lp` pattern, `solve.solve_cuopt`/`solve_gurobi`, `residual.py`), all
imported and reused, not modified. No new third-party dependency.

**Storage**: flat files only — `benchmarks/results/s85_objectives/<objective_id>.json`
(one per objective, both solvers), `benchmarks/results/s85_objectives/summary.csv`
(aggregated), `benchmarks/results/s85_objectives/objectives.json` (the ObjectiveDefinition
registry, so the exact reaction list + rationale ships with the results).

**Testing**: `pytest` for the parts that don't require a GPU/Gurobi license (objective
registry validation: dedup, all reaction names resolve in the model's `rxns`, exactly one
nonzero per objective vector; outlier-detection and averaging math on synthetic
per-objective timing data). The actual solver runs are exercised on the GPU host per
`quickstart.md`, matching how `002`'s solver paths are validated (no CI GPU).

**Target Platform**: Linux GPU host with an NVIDIA GPU (cuOpt) and a Gurobi license —
same host used for the existing benchmark (`msp-precision`, RTX A4500).

**Project Type**: single project — extends the existing `benchmarks/` CLI tooling package
in this repository; no new service, frontend, or API surface.

**Performance Goals**: not a latency target — the goal is a *measurement*: an average
cuOpt and average Gurobi solve time across ~20 objectives on S85, comparable to the
existing single-objective S85 numbers (Gurobi ~52s, cuOpt ~509s median).

**Constraints**: per-solve `time_limit` defaults to 900s (same as `002`, FR unchanged);
total sweep wall time is expected to run multiple hours (~20 objectives x 2 solvers,
cuOpt alone was ~500s on the one previously-measured objective) — this drives the
progress-visibility (FR-005) and resumability (FR-009) requirements, not a hard SLA.

**Scale/Scope**: one model (S85: 874,634 cols / 1,993,029 total rows / 6,137,523 nnz),
~20 objectives, 2 solvers, 1 repeat per (objective, solver) by default (spec Assumptions).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Correctness-Validated Defaults**: PASS by construction — the sweep consumes
  `gpugem`'s shipped defaults via the existing `benchmarks.solve.solve_cuopt` wrapper
  unchanged; it never edits `gpugem/_defaults.py` and never tunes cuOpt settings per
  objective. Every reported time is paired with its feasibility residual (spec FR-004),
  so a fast-but-wrong solve cannot be averaged in as a win.
- **II. Honest Status/Feasibility Reporting**: PASS — reuses `benchmarks.residual`'s
  feasibility/objective-agreement checks verbatim; an (objective, solver) result that
  fails the correctness gate is recorded and shown, never coerced into the averaged
  comparison (spec FR-008, Edge Cases).
- **III. Test Coverage for Numerical Behavior**: N/A for solver-facing code — this
  feature adds no code to `gpugem/solver.py`, `scaling.py`, or `_defaults.py`. The new
  `benchmarks/` code (objective registry, aggregation/outlier math) gets `pytest`
  coverage per the Testing field above, consistent with the spirit of the principle.
- **IV. Minimal, COBRA-Compatible Surface**: PASS — no change to `gpugem`'s public API
  (`solve`, `solve_cobra`, `FBASolver`, `FBAResult`). This is benchmarking tooling only.
- **V. Documented Known Limitations**: N/A — no new solver bug or workaround is
  introduced; if the sweep surfaces one (e.g. an objective that cuOpt cannot solve
  within `time_limit`), it will be recorded as a per-objective result (edge case) and,
  if it reveals a genuine solver limitation, added to the README per this principle.

No violations. Complexity Tracking left empty.

**Post-Phase-1 re-check**: data-model.md, contracts/, and quickstart.md introduce no new
solver-facing code path, no new default, and no new public `gpugem` surface — they only add
benchmarking tooling (objective registry, sweep runner, aggregator) that calls the existing
`benchmarks.solve` / `benchmarks.residual` functions unchanged. Gate still PASSES.

## Project Structure

### Documentation (this feature)

```text
specs/003-s85-multi-objective-benchmark/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
benchmarks/
├── models.py                    # existing — reused: S85 registry entry, build_lp pattern
├── solve.py                     # existing — reused unchanged: solve_cuopt, solve_gurobi
├── residual.py                  # existing — reused unchanged: feasibility/agreement gate
├── run_benchmark.py             # existing cross-scale runner — untouched
├── s85_objectives.py            # NEW: ObjectiveDefinition registry (~20 entries) + a
│                                 #   build_lp_for_objective(name) helper that reuses
│                                 #   models.build_lp's S85 loader but swaps in each
│                                 #   objective's reaction index (mirrors the existing
│                                 #   Harvey single-objective pattern in models.py)
├── run_objective_sweep.py       # NEW CLI: --objective ID | --all, --force, --reps,
│                                 #   --time-limit; verbose progress + heartbeat; writes
│                                 #   per-objective JSON, resumable like run_benchmark.py
├── aggregate_sweep.py           # NEW: reads results/s85_objectives/*.json -> summary
│                                 #   (average/median/min/max per solver, ratio, outliers)
│                                 #   -> summary.csv + summary.json; also invoked by the
│                                 #   sweep CLI at the end of an --all run
├── results/
│   └── s85_objectives/
│       ├── objectives.json      # the ObjectiveDefinition registry, versioned with results
│       ├── <objective_id>.json  # one per objective (both solvers), same shape as existing
│       │                         #   per-model JSON in results/S85.json
│       └── summary.csv          # aggregated comparison + outlier flags
└── README.md                    # existing — append a short section for this sweep

tests/
└── test_s85_objectives.py       # NEW: objective-registry validation (dedup, reactions
                                   #   resolve, single nonzero) + aggregation/outlier math
                                   #   on synthetic timing data (no GPU/Gurobi required)
```

**Structure Decision**: Single project, extending the existing `benchmarks/` package
in place (same layout `002-benchmark-cuopt-gurobi` established). No new top-level
directory: the objective registry, sweep runner, and aggregator are new modules
alongside the existing `models.py`/`solve.py`/`residual.py`, which they import and
reuse rather than duplicate. Results are namespaced under
`results/s85_objectives/` so they don't collide with the existing per-model
`results/S85.json` from the cross-scale benchmark.

## Complexity Tracking

*No Constitution Check violations — this section is intentionally empty.*
