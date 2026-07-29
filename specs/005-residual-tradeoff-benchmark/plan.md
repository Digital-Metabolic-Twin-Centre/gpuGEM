# Implementation Plan: Constraint-Residual Speed/Correctness Trade-off Benchmark

**Branch**: `005-residual-tradeoff-benchmark` | **Date**: 2026-07-29 | **Spec**: ./spec.md

**Input**: Feature specification from `/specs/005-residual-tradeoff-benchmark/spec.md`

## Summary

Add a `benchmarks/` tool that, for every model already in the `002` cross-scale benchmark
(e_coli_core, iML1515, Harvey, S84, S85), assembles a three-way comparison — cuOpt under
gpugem's shipped defaults (reused from `002`'s committed results, not re-solved), cuOpt with
`per_constraint_residual=0` (solved fresh, in-process, one new setting override), and Gurobi
(reused from `002`) — and produces two regenerable figures (constraint violation, solve time)
showing the trade-off discovered on S85 (~78x faster, worst-row violation ~8.9e-05 → ~156) across
every model, with an explicit, unmissable "diagnostic only, not a recommendation" framing baked
into the artifacts themselves. `gpugem/_defaults.py` is never touched.

## Technical Context

**Language/Version**: Python 3.13 (host base conda env — same as `002`/`003`/`004`)

**Primary Dependencies**: cuopt-cu12 26.6.0 (only for the new `per_constraint_residual=0` solves —
not needed to regenerate figures), matplotlib + pandas (figure generation, same as `002`'s
`make_figure.py`), the in-repo `gpugem`/`benchmarks` packages (`models.build_lp`,
`solve._solver_args`, `residual.feasibility_residual`), all reused unchanged.

**Storage**: `benchmarks/results/residual_tradeoff/<model>.json` (one per model, all three
configurations' stats), `benchmarks/results/residual_tradeoff/comparison.csv` (aggregated,
figure-source-of-truth, mirroring `002`'s `benchmark.csv` convention),
`benchmarks/figures/residual_tradeoff_violations.png` and
`benchmarks/figures/residual_tradeoff_solvetime.png`.

**Testing**: `pytest` for the comparison-table assembly logic (reading `002`'s existing results +
merging in a fresh per_constraint_residual=0 result, on synthetic data — no GPU/Gurobi needed)
and for the log-scale-with-zero-violation figure-data handling (research R5). Actual solves are
exercised on the GPU host per `quickstart.md`.

**Target Platform**: Linux GPU host with an NVIDIA GPU (cuOpt) — same host as `002`-`004`. Gurobi
is NOT needed to run this feature (its results are reused, never re-solved), only to regenerate
figures which need neither solver.

**Project Type**: single project — extends `benchmarks/` in place, no `gpugem/` changes at all
(unlike `004`, this uses only an existing, already-public `gpugem.solve(..., per_constraint_residual=0)`
override — no new field, no new API surface).

**Performance Goals**: not a latency target — the deliverable is the *comparison itself*: for each
of 5 models, the speed gained and violation-severity cost of `per_constraint_residual=0` relative
to the shipped default and to Gurobi.

**Constraints**: MUST NOT modify `gpugem/_defaults.py` (spec FR-009) under any outcome, including
if `per_constraint_residual=0` turns out to look favorable on some model — that's a separate,
out-of-scope decision requiring its own benchmark-backed justification per this project's
governance rules, not an automatic consequence of this feature. Each new solve reuses the same
per-model `time_limit` already recorded in `002`'s committed JSON, for a fair timing comparison.

**Scale/Scope**: 5 models (95 to 874,634 variables), 1 new solve per model (only the
`per_constraint_residual=0` configuration — the other two configurations per model are reused,
not solved), 2 output figures.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Correctness-Validated Defaults**: PASS — this feature never edits `_defaults.py`; it
  exists specifically to make an *already-known* correctness cost visible and quantified, not to
  hide or normalize it. `per_constraint_residual=0` results are never presented as validated or
  adopted (spec FR-008, User Story 3) — the opposite of what this principle guards against.
- **II. Honest Status/Feasibility Reporting**: PASS, and central to the feature's purpose — the
  whole point is refusing to let a faster solve's real constraint violation go unreported. The
  worst-row residual and (for the new configuration) rows-violated-count are computed with the
  same functions already used elsewhere in this project (`benchmarks.residual`, `gpugem`'s own
  `feasibility` dict), not a bespoke or looser calculation.
- **III. Test Coverage for Numerical Behavior**: N/A for `gpugem` — no `gpugem/solver.py`,
  `scaling.py`, or `_defaults.py` changes. The new `benchmarks/` comparison-assembly and
  figure-data logic gets `pytest` coverage per the Testing field above.
- **IV. Minimal, COBRA-Compatible Surface**: PASS — zero new `gpugem` public surface. The
  `per_constraint_residual=0` override uses `gpugem.solve`'s existing, already-documented
  `**cuopt_kwargs` passthrough (the same mechanism `004` used for its three variants) — nothing
  new to justify.
- **V. Documented Known Limitations**: APPLIES — this feature's entire output *is* a documented,
  quantified limitation/trade-off record. If the comparison surfaces anything not already in
  `README.md`'s "Known limitations" (e.g., a model where the effect is unexpectedly large or
  absent), it should be added there alongside the existing S85 finding.

No violations. Complexity Tracking left empty.

## Project Structure

### Documentation (this feature)

```text
specs/005-residual-tradeoff-benchmark/
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
├── models.py                          # existing — reused unchanged: build_lp(name) for
│                                       #   every one of the 5 already-covered models
├── solve.py                           # existing — reused unchanged: _solver_args(lp) helper
├── residual.py                        # existing — reused unchanged: feasibility_residual
├── run_residual_tradeoff.py           # NEW: orchestrator — for each of the 5 models, load
│                                       #   002's existing results (shipped-default cuOpt +
│                                       #   Gurobi, both reused/not re-solved), solve fresh with
│                                       #   gpugem.solve(..., per_constraint_residual=0),
│                                       #   compute its residual + rows-violated-count, write
│                                       #   results/residual_tradeoff/<model>.json
├── aggregate_residual_tradeoff.py     # NEW: reads results/residual_tradeoff/*.json ->
│                                       #   comparison.csv (one row per model x configuration)
├── make_residual_tradeoff_figures.py  # NEW: reads comparison.csv -> two PNGs (violations,
│                                       #   solve time), no solver import, matplotlib/Agg style
│                                       #   matching make_figure.py; explicit non-recommendation
│                                       #   caption baked into both figures (spec FR-008)
├── results/
│   └── residual_tradeoff/
│       ├── <model>.json               # one per model: all 3 configurations' stats
│       └── comparison.csv             # aggregated, figure source of truth
├── figures/
│   ├── residual_tradeoff_violations.png
│   └── residual_tradeoff_solvetime.png
└── README.md                          # existing — append a short section for this benchmark

tests/
└── test_residual_tradeoff.py          # NEW: comparison-assembly logic (merging reused +
                                        #   fresh results) and figure-data prep (log-scale /
                                        #   zero-violation handling) on synthetic data, no
                                        #   GPU/Gurobi required
```

**Structure Decision**: Single project, extending `benchmarks/` in place exactly like `002`-`004`.
Unlike `004`, no subprocess isolation is used for the new solve: `per_constraint_residual=0` is
cuOpt's own long-established default behavior (not an untested/crash-risk setting like `004`'s
Concurrent/cold-Barrier), already empirically confirmed fast (~6.5s on S85) and convergent, so a
plain in-process `gpugem.solve()` call is sufficient and simpler. Results are namespaced under
`results/residual_tradeoff/` so they don't collide with any prior feature's output.

## Complexity Tracking

*No Constitution Check violations — this section is intentionally empty.*

**Post-Phase-1 re-check**: data-model.md, contracts/, and quickstart.md confirm zero `gpugem/`
changes and zero new public surface — every new file lives in `benchmarks/` and calls existing,
unchanged `gpugem`/`benchmarks` functions. Gate still PASSES.
