---

description: "Task list for Constraint-Residual Speed/Correctness Trade-off Benchmark"

---

# Tasks: Constraint-Residual Speed/Correctness Trade-off Benchmark

**Input**: Design documents from `/specs/005-residual-tradeoff-benchmark/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all present)

**Tests**: Included — plan.md's Technical Context commits to pytest coverage for the
comparison-assembly logic (merging reused `002` data with a fresh solve) and the figure
zero-violation/log-scale data prep, both GPU/Gurobi-free, and quickstart.md step 2 runs them
explicitly.

**Organization**: Tasks are grouped by user story (P1/P2/P3 from spec.md) so each can be
implemented and independently tested on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Single project — extends the existing `benchmarks/` package. No `gpugem/` changes (see plan.md
Project Structure).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare the output location for this feature's results, distinct from `002`'s
`results/<model>.json` (which this feature reads but never writes to) and prior features'
`results/s85_objectives/` / `results/s85_solver_modes/`.

- [X] T001 Create `benchmarks/results/residual_tradeoff/` directory with a `.gitkeep`

**Checkpoint**: Output location exists; no new dependencies required (plan.md confirms
cuopt-cu12/matplotlib/pandas already satisfy this feature; Gurobi is not needed at all since its
results are reused).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The pure, GPU-free data-assembly logic (reading `002`'s existing results into the
shared schema, computing derived comparison fields) is needed by every user story — US1 writes
it, US2's figures consume it, US3's framing decorates what it produces.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 In `benchmarks/run_residual_tradeoff.py`, implement `_load_002_result(model)`: read
  `benchmarks/results/<model>.json` (error clearly if missing — this feature has nothing to
  compare against without it, per `contracts/cli-contract.md`), and return `(shipped_default,
  gurobi)` as two dicts matching data-model.md's `ResidualModeResult` schema (`source="reused"`,
  `rows_violated=null` for both, `residual_inf` taken from the existing JSON's
  `gurobi.repeats[0].residual_inf`/`cuopt.repeats[0].residual_inf`, `time_limit` from the existing
  JSON's own `time_limit` field per research R6)
- [X] T003 In `benchmarks/run_residual_tradeoff.py`, implement `build_model_comparison(model,
  scale, n_cols, shipped_default, residual_0, gurobi)`: a pure function returning a
  `ModelComparison` dict per data-model.md, computing `speedup_residual_0_vs_shipped =
  shipped_default["solve_s"] / residual_0["solve_s"]` and
  `violation_ratio_residual_0_vs_shipped = residual_0["residual_inf"] /
  shipped_default["residual_inf"]` (depends on T002 for the input shape)
- [X] T004 [P] Create `tests/test_residual_tradeoff.py` with tests for `_load_002_result` (using a
  temporary/fixture JSON matching `002`'s real schema — confirms `rows_violated` comes back
  `null` and `source="reused"`) and `build_model_comparison` (confirms `speedup`/`violation_ratio`
  arithmetic on synthetic input, no GPU/Gurobi required) — depends on T002, T003

**Checkpoint**: Foundation ready — `002` results can be loaded and assembled into the comparison
schema; user story implementation can now begin.

---

## Phase 3: User Story 1 - See exactly what per_constraint_residual trades away, per model (Priority: P1) 🎯 MVP

**Goal**: For every model already in `002`, produce a `ModelComparison` with real numbers for all
three configurations — two reused, one freshly solved with `per_constraint_residual=0`.

**Independent Test**: Run the benchmark and confirm that, for every model already covered by the
cross-scale benchmark, a result exists for cuOpt under shipped defaults, cuOpt with
`per_constraint_residual=0`, and Gurobi — each with solve time, iteration count, and
constraint-violation statistics.

### Implementation for User Story 1

- [X] T005 [US1] In `benchmarks/run_residual_tradeoff.py`, implement `_solve_residual_0(model)`:
  build the LP via `benchmarks.models.build_lp(model)`, call `gpugem.solve(...,
  **benchmarks.solve._solver_args(lp), time_limit=<from _load_002_result's shipped_default
  time_limit>, per_constraint_residual=0, check_feasibility=True)`, compute `residual_inf` via
  `benchmarks.residual.feasibility_residual`, and read `rows_violated` from
  `res.feasibility["stoich_rows_violated_1e6"]`; return a `ResidualModeResult` dict
  (`source="fresh"`) per data-model.md (research R2 — no subprocess isolation needed; depends on
  T002)
- [X] T006 [US1] Implement the `main()` CLI in `benchmarks/run_residual_tradeoff.py`: `--model
  NAME` / `--all` (mutually exclusive), `--force`; for each requested model, skip
  (`[skip] <model>`) if `results/residual_tradeoff/<model>.json` already exists and `--force`
  wasn't given, otherwise call `_load_002_result` (T002) + `_solve_residual_0` (T005) +
  `build_model_comparison` (T003) and write `results/residual_tradeoff/<model>.json` per
  `contracts/result-json.schema.json`; call `aggregate_residual_tradeoff.main()` at the end of an
  `--all` run (depends on T002, T003, T005)
- [X] T007 [US1] On the GPU host, run `python -m benchmarks.run_residual_tradeoff --model S85`
  and confirm: `shipped_default`/`gurobi` in the written JSON match `002`'s existing S85 numbers
  (`~511s`/`~55s`, `residual_inf` `~8.9e-05` for shipped_default), and `residual_0` reproduces the
  original investigation's finding (`~6.5s`, `residual_inf` in the hundreds) — quickstart.md step
  1 (depends on T006)
- [X] T008 [US1] On the GPU host, run `python -m benchmarks.run_residual_tradeoff --all` and
  confirm all 5 models (e_coli_core, iML1515, Harvey, S84, S85) produce a `ModelComparison`, none
  silently missing — quickstart.md step 3 (depends on T006, T007)

**Checkpoint**: User Story 1 is fully functional and independently testable — real, per-model
three-way comparison data exists for every covered model.

---

## Phase 4: User Story 2 - See the trade-off at a glance, not by reading raw numbers (Priority: P2)

**Goal**: Turn the collected comparison data into two regenerable figures (violations, solve
time) showing all three configurations per model.

**Independent Test**: Generate the figures from already-collected results and confirm they show,
per model, the constraint-violation level and solve time for all three configurations,
regenerable from committed result data without a solver installed.

### Implementation for User Story 2

- [X] T009 [P] [US2] Create `benchmarks/aggregate_residual_tradeoff.py`: read whichever
  `results/residual_tradeoff/*.json` files exist, write `results/residual_tradeoff/comparison.csv`
  per `contracts/csv-columns.md` (15 rows at full coverage: 5 models x 3 configurations; `rows_violated`
  left empty, not zero, for `configuration in {shipped_default, gurobi}`) — standalone, no solver
  import (depends on T003's `ModelComparison` shape)
- [X] T010 [US2] Create `benchmarks/make_residual_tradeoff_figures.py`: read `comparison.csv`,
  produce `benchmarks/figures/residual_tradeoff_violations.png` (log-scale y-axis on
  `residual_inf`, three bars per model in `002`'s existing scale/`n_cols` ordering, per-bar value
  annotations, zero-violation values floored to a small epsilon for plotting only per research R5)
  and `benchmarks/figures/residual_tradeoff_solvetime.png` (log-scale y-axis on `solve_s`, same
  model ordering and bar grouping) — matplotlib `Agg` backend, 300 dpi, `bbox_inches="tight"`,
  matching `benchmarks/make_figure.py`'s existing style; no solver import (depends on T009)
- [X] T011 [P] [US2] In `tests/test_residual_tradeoff.py`, add tests for the figure data-prep
  logic in `make_residual_tradeoff_figures.py`: a zero `residual_inf` value doesn't crash the
  log-scale plot and the true value is preserved in the annotation/CSV (not silently altered) —
  no GPU/Gurobi required (depends on T010)
- [X] T012 [US2] On the GPU host (or with T008's already-committed results), run
  `python -m benchmarks.aggregate_residual_tradeoff && python -m
  benchmarks.make_residual_tradeoff_figures` and visually confirm both PNGs show all 5 models with
  three configurations each, log-scaled, values annotated — quickstart.md step 4 (depends on T008,
  T010)

**Checkpoint**: User Stories 1 AND 2 both work — the full trade-off is visible in two regenerable
figures on top of User Story 1's raw data.

---

## Phase 5: User Story 3 - Never mistake "faster" for "recommended" (Priority: P3)

**Goal**: Make it structurally impossible to misread either figure as endorsing
`per_constraint_residual=0`.

**Independent Test**: Review the benchmark's output artifacts and confirm they explicitly state
that `per_constraint_residual=0` results are not validated for correctness and are not a
suggested replacement for the shipped default.

### Implementation for User Story 3

- [X] T013 [US3] In `benchmarks/make_residual_tradeoff_figures.py`, add to both figures: a
  distinct hatch pattern on the `residual_0` bars (visually separating them from
  `shipped_default`/`gurobi`) and a fixed caption reproduced verbatim on the figure itself —
  *"per_constraint_residual=0 results are shown for comparison only; they are not validated for
  correctness and are not a recommended configuration."* — per `contracts/figure-contract.md` and
  spec FR-008 (depends on T010)
- [X] T014 [US3] Open both regenerated figures and confirm: the caption is present and legible on
  each figure independently (a reader seeing only one figure still gets the warning), and the
  `residual_0` bars are visually distinguishable from the other two at a glance — quickstart.md
  step 4(b)-(c) (depends on T013)

**Checkpoint**: All three user stories are independently functional — the benchmark produces
data, a visual comparison, and an unmissable non-recommendation framing baked into the artifacts
themselves.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, lint, and the final end-to-end confirmation that nothing was changed
that shouldn't have been.

- [X] T015 [P] Add a "Constraint-residual speed/correctness trade-off" section to
  `benchmarks/README.md` documenting `run_residual_tradeoff.py` /
  `aggregate_residual_tradeoff.py` / `make_residual_tradeoff_figures.py` usage, per plan.md's
  Project Structure note
- [X] T016 [P] Run `ruff check` on `benchmarks/run_residual_tradeoff.py`,
  `benchmarks/aggregate_residual_tradeoff.py`, `benchmarks/make_residual_tradeoff_figures.py`,
  `tests/test_residual_tradeoff.py` and fix any violations (Constitution Quality Standards:
  `line-length = 100`), consistent with prior features' established convention of matching
  existing `benchmarks/` style rather than diverging
- [X] T017 Run quickstart.md end-to-end (steps 1-5) on the GPU host, and confirm step 5's `git
  diff --stat gpugem/_defaults.py` produces no output — the project's shipped defaults are
  unchanged regardless of what the comparison shows (spec SC-002; depends on T008, T012, T014)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion — no dependency on US2/US3
- **User Story 2 (Phase 4)**: Depends on Foundational + US1's result-file shape (T006); its own
  new file (`aggregate_residual_tradeoff.py`, T009) only needs T003's schema, not US1's actual GPU
  runs, so it can be built in parallel with T007/T008
- **User Story 3 (Phase 5)**: Edits the same file US2 built (`make_residual_tradeoff_figures.py`),
  so sequenced after it here, though its Independent Test doesn't require US2's own validation
  task to have run first
- **Polish (Phase 6)**: Depends on all three user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependency on US2/US3 — raw three-way comparison data exists whether
  or not figures or framing exist yet
- **User Story 2 (P2)**: Independently testable once US1's result-file shape is fixed (T006);
  figure generation doesn't care whether US3's hatch/caption layer has been added
- **User Story 3 (P3)**: Independently testable (caption/hatch presence can be verified on its
  own), sequenced last here only because it edits the same file US2 built

### Within Each User Story

- Data loading (`_load_002_result`) before the fresh solve (`_solve_residual_0`) before assembly
  (`build_model_comparison`) before the CLI that wires them together (US1)
- Comparison CSV before figures before figure framing (US2 → US3)
- Manual/quickstart GPU validation task last in each phase

### Parallel Opportunities

- T004 (test file) can run in parallel with continued work on `run_residual_tradeoff.py` once
  T002/T003 land
- T009 (`aggregate_residual_tradeoff.py`, new file) can proceed in parallel with T007/T008 (GPU
  validation of `run_residual_tradeoff.py`) — different files, only needs T003's schema
- T011 (test file) can run in parallel with T012 (GPU/visual validation) once T010 lands
- T015 and T016 (Polish) can run in parallel — different files

---

## Parallel Example: Foundational Phase

```bash
# After T002/T003 (load + assembly logic) land, run together:
Task: "Comparison-assembly tests in tests/test_residual_tradeoff.py"       # T004
Task: "Continue User Story 1 implementation in run_residual_tradeoff.py"   # T005+
```

## Parallel Example: User Story 1 / User Story 2 overlap

```bash
# Once T003 (ModelComparison schema) is fixed, run together:
Task: "GPU-validate the S85 and full --all run"                # T007, T008
Task: "Implement aggregate_residual_tradeoff.py against the fixed schema"  # T009
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: run `--all` on the GPU host, inspect the 5 `results/residual_tradeoff/
   <model>.json` files by hand — the full three-way trade-off numbers already exist, even before
   any figure is generated
5. Phases 4-5 turn that raw data into a legible, honestly-framed visual comparison, but the core
   research answer (per-model speed/violation trade-off) is available after Phase 3 alone

### Incremental Delivery

1. Setup + Foundational → `002`-result loading and comparison-assembly logic ready
2. User Story 1 → real three-way comparison data for all 5 models, testable end-to-end
3. User Story 2 → same data, now visualized in two regenerable figures
4. User Story 3 → same figures, now structurally unmistakable as diagnostic-only
5. Polish → docs, lint, final confirmation that no shipped default changed

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- US2 and US3 land after US1 primarily because of schema/shared-file dependencies, not because of
  deeper coupling — each still has its own Independent Test criterion
- No `gpugem/` changes anywhere in this feature — every task touches only `benchmarks/` or `tests/`
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently
