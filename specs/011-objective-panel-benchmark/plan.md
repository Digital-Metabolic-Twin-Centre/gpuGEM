# Implementation Plan: Cross-Model Objective-Panel Credibility Benchmark

**Branch**: `011-objective-panel-benchmark` | **Date**: 2026-08-14 | **Spec**: ./spec.md

**Input**: Feature specification from `/specs/011-objective-panel-benchmark/spec.md`

## Summary

Add a `benchmarks/` tool that, for every model in the main suite, solves every objective reaction listed in
that model's already-curated `benchmarks/objective_candidates/<model>.csv` panel (10-50 objectives per
model, ~385 total) with both solvers exactly as already published for that model (gpugem's shipped cuOpt
settings, Gurobi's deliberately-configured barrier setting) -- never a different setting. Each (model,
objective, solver) combination is solved `reps=3` times (matching every other recorded result in this
project), with runtime, objective value, and constraint-violation residual all reported as the median across
those repeats, gated by the same correctness check used everywhere else in this project. Results are saved
as two additive CSVs (a lean objective-value/runtime view, and a fuller correctness/benchmark-detail view)
plus one figure per model, so a reader can judge whether every model's already-published single-objective
number is representative of that model's broader objective panel. `gpugem/_defaults.py` and every previously
-published result are never touched.

## Technical Context

**Language/Version**: Python 3.13 (host base conda env -- same as every prior benchmark feature)

**Primary Dependencies**: gurobipy + cuopt-cu12 (only for producing fresh results -- not needed to
regenerate the CSVs or figures), matplotlib + pandas (figure generation, same style as `make_gurobi_default_
figure.py`), the in-repo `benchmarks` package (`models.build_lp`, `models._mat_rxns`, `solve.solve_gurobi`/
`solve_cuopt`, `residual.feasibility_residual`/`objectives_agree`), all reused unchanged; one new small
reaction-lookup helper generalizing two already-proven per-model-kind lookup mechanisms (research R2).

**Storage**: `benchmarks/results/objective_panel/<model>/<objective_id>.json` (one per (model, objective)
pair, both solvers' full repeat data), `benchmarks/results/objective_panel/objective_runtime.csv` and
`benchmark_details.csv` (the two additive aggregate views, figure-source-of-truth),
`benchmarks/figures/objective_panel_<model>.png` (one per model).

**Testing**: `pytest` for the reaction-lookup helper (both cobra-kind and mat-kind resolution, on synthetic/
small models -- no GPU/Gurobi needed), the median-vs-single-run and median-vs-gate distinction (research R7:
a combination with one failing repeat must still gate to `both_feasible=False` even if its median residual
looks fine), and the two-CSV aggregation logic (reading fixture JSONs, no solver import). Actual solves are
exercised on a host with both solvers available, per `quickstart.md` -- expected to run over an extended
period given the realistic multi-day total runtime (research R4).

**Target Platform**: Linux host with both Gurobi licensed and cuOpt's GPU available, for producing fresh
results. Regenerating the CSVs or figures needs neither solver installed (spec FR-007/SC-001).

**Project Type**: single project -- extends `benchmarks/` in place, no `gpugem/` changes at all; the
reaction-lookup helper is additive, generalizing existing lookup code rather than replacing it.

**Performance Goals**: not a latency target -- the deliverable is the comparison itself: for every model,
whether its one already-published objective's runtime is typical or an outlier across a much larger,
biologically diverse panel of objectives on the same model.

**Constraints**: MUST NOT modify `gpugem/_defaults.py`, `benchmarks/solve.py`'s existing default arguments,
or any already-published `results/*.json`/`results/gurobi_default/*.json` file under any outcome (spec
FR-009/FR-010/SC-003/SC-005) -- this feature is a read-mostly credibility check on existing settings, not a
tuning exercise. Every (model, objective, solver) combination MUST remain individually resumable given the
realistic multi-day total runtime (spec FR-011/SC-004; research R4).

**Scale/Scope**: 10 models, ~385 total objectives (10 for e_coli_core, 25 each for iML1515/Harvey/Harvetta,
50 each for the six microbiome models), x 2 solvers x 3 repeats = ~2,310 individual solves. Realistically
multi-day wall-clock time overall, dominated by the six large microbiome models (research R4).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Correctness-Validated Defaults**: PASS -- this feature never edits `_defaults.py`; it exists
  specifically to check whether already-shipped, already-validated settings hold up across a wider objective
  panel, using those settings completely unchanged (spec FR-002/FR-010).
- **II. Honest Status/Feasibility Reporting**: PASS, and central to this feature's purpose -- a combination
  that fails the correctness gate is recorded and clearly marked, never silently included as if it had
  passed (spec FR-006), and the gate itself is never loosened by the median-reporting requirement (research
  R7 -- gate reads every repeat, only the *displayed* residual is a median).
- **III. Test Coverage for Numerical Behavior**: the new reaction-lookup helper and the median/gate
  aggregation logic get `pytest` coverage per the Testing field above; no `gpugem/solver.py`/`scaling.py`/
  `_defaults.py` changes to cover.
- **IV. Minimal, COBRA-Compatible Surface**: PASS -- zero new `gpugem` public surface; every new file lives
  in `benchmarks/`.
- **V. Documented Known Limitations**: N/A -- no new solver limitation discovered; this feature validates
  existing published numbers rather than surfacing a new trade-off.
- **VI. Publication-Ready Figure Standards** (v1.2.0): the already CVD-validated `CONFIG_COLOR` solver-color
  pair is reused directly (research R8) for the new per-model figures, with professional axis/legend
  phrasing and no internal-setting jargon. Consistent with features 005/010's own re-check, this feature does
  **not** additionally build the full journal-PDF/TIFF/caption treatment -- that stays a separate, explicit
  follow-up, not silently bundled into this data-content feature.

No violations. Complexity Tracking left empty.

## Project Structure

### Documentation (this feature)

```text
specs/011-objective-panel-benchmark/
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
├── models.py                        # existing — reused unchanged: build_lp(name), _mat_rxns,
│                                     #   REGISTRY/ALL_MODELS for every model this feature covers
├── solve.py                         # existing — reused unchanged: solve_gurobi, solve_cuopt
├── residual.py                      # existing — reused unchanged: feasibility_residual,
│                                     #   objectives_agree
├── objective_candidates/            # existing — the 10 curated per-model objective-panel CSVs
│                                     #   this feature reads (prior work, not modified here)
├── objective_panel.py               # NEW: shared helpers — _build_lp_with_objective(model,
│                                     #   reaction_id) generalizing the cobra-kind and mat-kind
│                                     #   reaction lookups already used by models.build_lp's
│                                     #   meta["objective"] branch and s85_objectives.py (research
│                                     #   R2); _load_panel(model) reads that model's
│                                     #   objective_candidates/<model>.csv; _load_settings(model)
│                                     #   reads reps/time_limit/res_tol/obj_tol from its existing
│                                     #   results/<model>.json (research R1)
├── run_objective_panel.py           # NEW: orchestrator — for each requested model, for each
│                                     #   objective in its panel, solve with both solvers reps
│                                     #   times, apply the correctness gate per-repeat (research
│                                     #   R7), write
│                                     #   results/objective_panel/<model>/<objective_id>.json;
│                                     #   heartbeat prints during each solve (research R4); skip
│                                     #   -if-exists resumability (spec FR-011)
├── aggregate_objective_panel.py     # NEW: reads results/objective_panel/<model>/*.json ->
│                                     #   objective_runtime.csv + benchmark_details.csv (spec
│                                     #   FR-007) — no solver import
├── make_objective_panel_figures.py  # NEW: reads both CSVs -> one PNG per model (spec FR-008) —
│                                     #   no solver import; failed-gate objectives visually marked,
│                                     #   each model's already-published baseline objective
│                                     #   visually distinguished (contracts/figure-contract.md)
├── results/
│   └── objective_panel/
│       ├── <model>/
│       │   └── <objective_id>.json  # one per (model, objective) pair
│       ├── objective_runtime.csv
│       └── benchmark_details.csv
├── figures/
│   └── objective_panel_<model>.png  # one per model
└── README.md                        # existing — append a short section for this benchmark

tests/
└── test_objective_panel.py          # NEW: reaction-lookup helper (both model kinds), the
                                      #   median-display-vs-all-repeats-gate distinction (research
                                      #   R7), and the two-CSV aggregation logic — all on synthetic
                                      #   data, no GPU/Gurobi required
```

**Structure Decision**: Single project, extending `benchmarks/` in place exactly like every prior feature.
Mirrors the established `run_*` / `aggregate_*` / `make_*_figure(s)` three-script pattern (features 005,
010) precisely, with results namespaced under `results/objective_panel/` so they don't collide with any
prior feature's output, and figures namespaced `objective_panel_<model>.png` for the same reason. No
subprocess isolation needed: every (model, objective) solve uses this project's already-established,
already-proven settings for that model — nothing untested or crash-risk about the configuration itself, only
about the sheer number of combinations, which resumability (not isolation) addresses.

## Complexity Tracking

*No Constitution Check violations — this section is intentionally empty.*

**Post-Phase-1 re-check**: data-model.md, contracts/, and quickstart.md confirm zero `gpugem/` changes and
zero new public surface — every new file lives in `benchmarks/` and calls existing, unchanged
`benchmarks`/`gpugem` functions plus one additive reaction-lookup helper generalizing already-proven logic.
Gate still PASSES.
