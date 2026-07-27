# Implementation Plan: S85 Alternative Solver-Mode Experiment

**Branch**: `004-s85-solver-mode-experiment` | **Date**: 2026-07-27 | **Spec**: ./spec.md

**Input**: Feature specification from `/specs/004-s85-solver-mode-experiment/spec.md`

## Summary

Add a `benchmarks/` experiment that re-solves S85's whole-body-objective LP (the same LP the
`002` cross-scale benchmark and `003` sweep's `whole_body` entry use) with cuOpt under the
current baseline settings and under three untested variants —
`pdlp_solver_mode=Methodical1`, `method=Concurrent`, and `method=Barrier` (cold, no warm start) —
each expressed purely as `**cuopt_kwargs` overrides through `gpugem.solve`'s existing
per-call override mechanism, so `gpugem/_defaults.py` is never touched. Every variant is gated
by the same feasibility-residual + Gurobi-objective-agreement correctness check already used in
`002`/`003`, runs with its own time budget, and — because two of the three variants have never
been run on this model family and cuOpt's own behavior under them is unknown (Barrier's cold
factorization on an ~874K-variable problem in particular) — each variant runs in an **isolated
subprocess** so a hang, crash, or OOM in one variant cannot lose the others' results or corrupt
the run. Results land in one JSON per variant plus a comparison summary that reports each
candidate's speedup/slowdown factor against the baseline and flags the best verified-correct
candidate, if any.

## Technical Context

**Language/Version**: Python 3.13 (host base conda env — same as `002`/`003`)

**Primary Dependencies**: cuopt-cu12 26.6.0, gurobipy 13.0.2, scipy, numpy — the in-repo
`gpugem` package (`solve`, extended per Phase 1 below) and `benchmarks` package
(`s85_objectives.build_lp_for_objective`, `solve.solve_gurobi`, `residual.py`), all reused. No
new third-party dependency.

**Storage**: flat files — `benchmarks/results/s85_solver_modes/<variant_id>.json` (one per
variant), `benchmarks/results/s85_solver_modes/summary.json`/`.csv` (comparison), mirroring the
`003` sweep's output convention.

**Testing**: `pytest` for (a) the one small additive change inside `gpugem` (see Phase 1 —
`solved_by` surfaced on `FBAResult`), covering both that it's populated when cuOpt reports it and
`None` when it doesn't (Constitution Principle III applies here since this touches
`gpugem/solver.py`), and (b) the comparison/speedup-factor math in `benchmarks`, on synthetic
variant results (no GPU/Gurobi required) — same pattern as `003`'s `aggregate_sweep` tests.
Actual solver-mode runs are exercised on the GPU host per `quickstart.md`.

**Target Platform**: Linux GPU host with an NVIDIA GPU (cuOpt) and a Gurobi license — same host
as `002`/`003` (`msp-precision`, RTX A4500).

**Project Type**: single project — extends the existing `benchmarks/` CLI tooling package, plus
one small additive (non-breaking) field on `gpugem`'s public `FBAResult`. No new service,
frontend, or API surface.

**Performance Goals**: not a latency target — the goal is a *measurement*: does any candidate
variant reduce cuOpt's wall time on S85 below its current ~509s (`002`/`003` baseline), and if so
by how much, while remaining verified-correct.

**Constraints**: each variant gets its own time budget (default reused from `002`/`003`: 900s);
a variant that does not finish in that budget is recorded as inconclusive, not as a failure or a
crash (spec FR-005). Each variant MUST run in a separate OS process from the experiment's
orchestrator and from each other, so a crash (e.g. Barrier's cuDSS factorization exhausting GPU
or host memory on a problem this large, which is plausible and explicitly untested) cannot take
down the whole experiment or leave a stale CUDA context for the next variant.

**Scale/Scope**: one model (S85, same dimensions as `002`/`003`: 874,634 cols / 1,993,029 total
rows / 6,137,523 nnz), one fixed objective (whole-body, for direct comparability to the existing
baseline numbers), 4 variants (baseline + 3 candidates), 1 solve each (no repeats, per spec
Assumptions).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Correctness-Validated Defaults**: PASS — this experiment never edits
  `gpugem/_defaults.py` (spec FR-007); every variant is expressed as a per-call
  `**cuopt_kwargs` override through `gpugem.solve`'s existing mechanism ("Any cuOpt parameter can
  be overridden via keyword arguments" — already part of `gpugem.solve`'s documented contract, not
  new surface). Even if a candidate wins, promoting it to a default is explicitly out of scope
  here and would need its own benchmark-backed justification later (spec Assumptions).
- **II. Honest Status/Feasibility Reporting**: PASS — reuses `benchmarks.residual`'s
  feasibility/objective-agreement checks verbatim, and a variant that times out is recorded as
  "did not complete," never silently coerced into "Optimal" or dropped (spec FR-005, Edge Cases).
- **III. Test Coverage for Numerical Behavior**: APPLIES — this is the one feature so far that
  touches `gpugem/solver.py` (surfacing `solved_by`, Phase 1 below). The change is additive
  (a new optional field, no change to existing solve behavior or defaults) but still gets a
  dedicated unit test per this principle, not just an integration check.
- **IV. Minimal, COBRA-Compatible Surface**: APPLIES, justified — adding `solved_by: Optional[str]`
  to `FBAResult` is new public surface. It's justified by this feature's own concrete need (spec
  FR-004: recording which method actually answered a Concurrent solve) — the same bar the
  constitution sets ("justified by an actual modelling use case"). It's a single additive field,
  not a redesign of the result schema, and every existing caller is unaffected (default `None`).
- **V. Documented Known Limitations**: APPLIES conditionally — if any candidate variant surfaces a
  new solver limitation (e.g. Barrier OOMs, or Concurrent's chosen method is nondeterministic
  across runs), that MUST be recorded in the README's "Known limitations" section as part of this
  feature's results, not silently worked around.

No unjustified violations. One entry in Complexity Tracking for the `FBAResult` addition (see
below), justified rather than avoided.

## Project Structure

### Documentation (this feature)

```text
specs/004-s85-solver-mode-experiment/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
gpugem/
├── solver.py                    # MODIFIED (additive only): capture sol.get_solved_by() and
│                                 #   pass it through to FBAResult; no change to existing
│                                 #   default-merging or solve behavior
└── result.py                    # MODIFIED (additive only): new `solved_by: Optional[str] = None`
                                   #   field on FBAResult

benchmarks/
├── s85_objectives.py             # existing (003) — reused unchanged: build_lp_for_objective
│                                 #   ("whole_body") supplies the fixed LP for every variant
├── solve.py                      # existing — reused unchanged: solve_gurobi (baseline reference)
├── residual.py                   # existing — reused unchanged: correctness gate
├── solver_mode_variants.py       # NEW: SolverModeVariant registry (baseline, methodical1,
│                                 #   concurrent, barrier_cold) — id, cuopt_kwargs override dict,
│                                 #   rationale (mirrors s85_objectives.py's OBJECTIVES pattern)
├── run_solver_mode_experiment.py # NEW: orchestrator CLI — for each variant, launches a
│                                 #   subprocess (see research.md R1) that solves S85 under that
│                                 #   variant's cuopt_kwargs, waits with the variant's time
│                                 #   budget, records the result (or "inconclusive" on
│                                 #   timeout/crash), writes results/s85_solver_modes/<id>.json
├── _solver_mode_worker.py        # NEW: the actual subprocess entry point — solves one variant,
│                                 #   prints its JSON result to stdout for the parent to capture
├── aggregate_solver_modes.py     # NEW: reads results/s85_solver_modes/*.json -> speedup/
│                                 #   slowdown factors vs baseline, best-candidate identification
│                                 #   -> summary.json + summary.csv
├── results/
│   └── s85_solver_modes/
│       ├── <variant_id>.json     # one per variant (baseline, methodical1, concurrent,
│       │                         #   barrier_cold)
│       └── summary.csv           # aggregated comparison
└── README.md                     # existing — append a short section for this experiment

tests/
├── test_solver.py                # existing — add one test: solved_by is populated/None
│                                 #   appropriately (Constitution III, small addition)
└── test_solver_mode_variants.py  # NEW: variant-registry validation + speedup-factor /
                                   #   best-candidate math on synthetic results (no GPU/Gurobi)
```

**Structure Decision**: Single project, extending `benchmarks/` in place exactly like `003`, plus
one small additive change inside `gpugem/` itself (the only feature so far that needs one, because
`solved_by` genuinely doesn't exist anywhere yet and only `gpugem.solve` has access to the raw
cuOpt solution object). Results are namespaced under `results/s85_solver_modes/` so they don't
collide with `002`'s `results/S85.json` or `003`'s `results/s85_objectives/`.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|---------------------------------------|
| New public field `FBAResult.solved_by` | Spec FR-004 requires recording which underlying method (PDLP/DualSimplex/Barrier) answered a `method=Concurrent` solve; only `gpugem.solve` has access to cuOpt's `sol.get_solved_by()` | Duplicating `gpugem/solver.py`'s ~80 lines of DataModel/SolverSettings/Solve wiring inside `benchmarks/` just to read one extra field would violate the project's own reuse precedent (`002`/`003` both reuse `gpugem.solve`/`benchmarks.solve` unchanged) and create two divergent solve paths to keep in sync |

**Post-Phase-1 re-check**: data-model.md, contracts/, and quickstart.md confirm the only
`gpugem/`-internal change is the additive `solved_by` field (contracts/gpugem-api-addition.md) —
no default value changes, no new required parameters, fully backward compatible. Everything else
is new `benchmarks/` tooling calling `gpugem.solve`/`benchmarks.solve`/`benchmarks.residual`
unchanged. Gate still PASSES.
