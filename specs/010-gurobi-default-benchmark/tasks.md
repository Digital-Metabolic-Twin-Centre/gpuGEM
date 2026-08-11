---

description: "Task list for Gurobi Default-Settings Benchmark Across All Models"

---

# Tasks: Gurobi Default-Settings Benchmark Across All Models

**Input**: Design documents from `/specs/010-gurobi-default-benchmark/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all present)

**Tests**: Included — plan.md's Technical Context commits to pytest coverage for the
`solve_gurobi` return-dict extension, the comparison-assembly logic (reusing an existing model's
`results/<model>.json` + merging in a fresh default-settings result), and the
correctness-gate-failure path (spec FR-003), all GPU/Gurobi-free.

**Organization**: Tasks are grouped by user story (P1/P2 from spec.md) so each can be implemented
and independently tested on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Include exact file paths in descriptions

## Path Conventions

Single project — extends the existing `benchmarks/` package. No `gpugem/` changes (see plan.md
Project Structure).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare the output location for this feature's results, distinct from the existing
`results/<model>.json` (which this feature reads but never writes to) and every other feature's
own results subdirectory (`results/residual_tradeoff/`, `results/s85_objectives/`, etc.).

- [X] T001 Create `benchmarks/results/gurobi_default/` directory with a `.gitkeep`

**Checkpoint**: Output location exists; no new dependencies required (plan.md confirms gurobipy is
already used elsewhere in this project; cuOpt is not needed at all for this feature).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The `solve_gurobi` introspection extension and the pure, GPU-free logic for reading
an existing model's result are needed by every user story — US1 writes results using both, US2's
comparison/figure consume what US1 produces.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 In `benchmarks/solve.py::solve_gurobi`, add `bar_iters` (`int(m.BarIterCount)`) and
  `simplex_iters` (`int(m.IterCount)`) to the returned dict — both already computed internally
  today and currently discarded after collapsing into the existing `iters` field; purely additive,
  every existing caller/key unaffected (research R2, data-model.md)
- [X] T003 In `benchmarks/run_gurobi_default_benchmark.py`, implement `_load_existing_result(model)`:
  read `benchmarks/results/<model>.json`, error out clearly if missing (this feature has nothing
  to compare against without it, per `contracts/cli-contract.md`), and return the reused
  `cuopt_*`/`gurobi_barrier_*` values plus `time_limit` needed for `data-model.md`'s
  `ThreeWayComparison` — never modifying the source file
- [X] T004 [P] Create `tests/test_gurobi_default_benchmark.py` with tests for: `solve_gurobi`'s
  `bar_iters`/`simplex_iters` keys are present and additive (existing keys like `iters`/`method`
  unaffected — synthetic/mocked model, no live Gurobi license required if the test environment
  lacks one, otherwise a small real LP), and `_load_existing_result` (using a fixture JSON matching
  the real `results/<model>.json` schema — confirms the reused values come back unmodified, and
  confirms the clear-error-on-missing-file behavior) — depends on T002, T003

**Checkpoint**: Foundation ready — an existing model's result can be loaded and Gurobi's
automatic-mode algorithm choice can be introspected; user story implementation can now begin.

---

## Phase 3: User Story 1 - See Gurobi's out-of-the-box runtime, not only the project's own tuned choice, for every model (Priority: P1) 🎯 MVP

**Goal**: For every model already in the main suite, produce a `GurobiDefaultResult` — a real
solve time, objective, status, and feasibility residual from Gurobi with `Method` left at its own
factory default (`-1`), gated by the same correctness checks used everywhere else in this project.

**Independent Test**: Run the benchmark tooling with Gurobi's algorithm setting left untouched
against every model in the suite and confirm a result (solve time, objective, status, feasibility
residual) is produced for each, without altering any model's already-recorded cuOpt or
deliberately-configured-Gurobi result.

### Implementation for User Story 1

- [X] T005 [US1] In `benchmarks/run_gurobi_default_benchmark.py`, implement `_solve_default(model)`:
  build the LP via `benchmarks.models.build_lp(model)`, call `benchmarks.solve.solve_gurobi(lp,
  time_limit=<from _load_existing_result's time_limit>, method=-1)` (research R1), compute
  `residual_inf` via `benchmarks.residual.feasibility_residual`, derive `solved_by` from
  `bar_iters`/`simplex_iters` (`"barrier"` if `bar_iters > 0` else `"simplex"`), and apply the
  correctness gate (`feasible = status == "Optimal" and residual_inf <= res_tol`,
  `obj_agree_with_cuopt` checked against the model's existing cuOpt objective from
  `_load_existing_result`) to produce a `GurobiDefaultResult` dict per `data-model.md` (spec
  FR-001/FR-002; depends on T002, T003)
- [X] T006 [US1] Implement the `main()` CLI in `benchmarks/run_gurobi_default_benchmark.py`:
  `--model NAME` / `--all` (mutually exclusive), `--force`; for each requested model, skip
  (`[skip] <model>`) if `results/gurobi_default/<model>.json` already exists and `--force` wasn't
  given, otherwise call `_load_existing_result` (T003) + `_solve_default` (T005) and write
  `results/gurobi_default/<model>.json`; a failed correctness gate is still written to disk with
  `feasible: false`/`obj_agree_with_cuopt: false`, never dropped (spec FR-003); call
  `aggregate_gurobi_default.main()` at the end of an `--all` run (depends on T003, T005)
- [X] T007 [US1] In `tests/test_gurobi_default_benchmark.py`, add a test for the
  correctness-gate-failure path: a synthetic case with a non-optimal status or an
  out-of-tolerance residual still returns a complete `GurobiDefaultResult` dict with
  `feasible=False` (or `obj_agree_with_cuopt=False`) rather than raising or being silently dropped
  — no GPU/Gurobi required (depends on T005)
- [X] T008 [US1] On a host with Gurobi licensed, run `python -m
  benchmarks.run_gurobi_default_benchmark --model e_coli_core` and confirm the written JSON's
  reused `cuopt_*`/`gurobi_barrier_*` values match `results/e_coli_core.json` exactly, and the new
  `gurobi_default` result has `feasible: true` — quickstart.md "single model" step (depends on
  T006)
- [X] T009 [US1] On the same host, run `--all` and confirm every model in the suite has a
  `results/gurobi_default/<model>.json` (spec FR-001 acceptance scenario 3), and confirm via `git
  diff --stat benchmarks/results/*.json` that no existing per-model result file changed (spec
  FR-004/SC-002; quickstart.md "no side effect" step; depends on T006, T008)

**Checkpoint**: User Story 1 is fully functional and independently testable — real, per-model
default-settings results exist for every model in the suite, with the correctness gate enforced.

---

## Phase 4: User Story 2 - See all three numbers side by side, per model, in one place (Priority: P2)

**Goal**: Turn the collected default-settings results into a single comparison view (CSV + figure)
showing cuOpt, Gurobi (deliberately-configured), and Gurobi (default) side by side per model.

**Independent Test**: Generate the comparison from already-collected results and confirm it shows,
for every model, the solve time for cuOpt, deliberately-configured Gurobi, and default-settings
Gurobi — regenerable from committed result data without either solver installed.

### Implementation for User Story 2

- [X] T010 [P] [US2] Create `benchmarks/aggregate_gurobi_default.py`: read whichever
  `results/gurobi_default/*.json` files exist, join each against its model's existing
  `results/<model>.json` for the reused `cuopt_*`/`gurobi_barrier_*` columns, compute
  `gurobi_default_speedup_vs_barrier`, and write `results/gurobi_default/comparison.csv` per
  `contracts/csv-columns.md` — standalone, no solver import (spec FR-007; depends on T003's
  schema)
- [X] T011 [US2] Create `benchmarks/make_gurobi_default_figure.py`: read `comparison.csv`, produce
  `benchmarks/figures/gurobi_default_comparison.png` (log-scale y-axis on `solve_s`, three bars
  per model in the existing scale/`n_cols` ordering, reusing the already CVD-validated
  `CONFIG_COLOR` triple from `make_residual_tradeoff_figures.py` — research R5 — with a model
  whose `gurobi_default_feasible`/`gurobi_default_obj_agree_with_cuopt` is false visually marked as
  failed rather than plotted as a normal bar, per `contracts/figure-contract.md` and spec FR-003)
  — matplotlib `Agg` backend, 300 dpi, `bbox_inches="tight"`, no solver import (depends on T010)
- [X] T012 [P] [US2] In `tests/test_gurobi_default_benchmark.py`, add tests for
  `aggregate_gurobi_default`'s join logic (reused `cuopt_*`/`gurobi_barrier_*` columns come through
  unmodified from the fixture JSON) and for `comparison.csv`'s required columns being present per
  `contracts/csv-columns.md` — no GPU/Gurobi required (depends on T010)
- [X] T013 [US2] On the host (or with T009's already-committed results), run `python -m
  benchmarks.aggregate_gurobi_default && python -m benchmarks.make_gurobi_default_figure` and
  visually confirm the figure shows every model with three correctly-colored, correctly-annotated
  bars — quickstart.md "regenerate" steps (depends on T009, T011)

**Checkpoint**: Both user stories work — the raw default-settings data (US1) is now visible
alongside cuOpt and deliberately-configured Gurobi in one comparison view (US2).

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, lint, and the final end-to-end confirmation that nothing was changed
that shouldn't have been.

- [X] T014 [P] Add a "Gurobi default-settings benchmark" section to `benchmarks/README.md`
  documenting `run_gurobi_default_benchmark.py` / `aggregate_gurobi_default.py` /
  `make_gurobi_default_figure.py` usage, per plan.md's Project Structure note
- [X] T015 [P] Run `ruff check` on `benchmarks/solve.py`, `benchmarks/run_gurobi_default_benchmark.py`,
  `benchmarks/aggregate_gurobi_default.py`, `benchmarks/make_gurobi_default_figure.py`,
  `tests/test_gurobi_default_benchmark.py` and fix any violations (Constitution Quality Standards:
  `line-length = 100`), consistent with this project's established convention of matching existing
  `benchmarks/` style rather than diverging
- [X] T016 Run quickstart.md end-to-end and confirm `git diff gpugem/_defaults.py` produces no
  output — this project's shipped solver defaults are unchanged regardless of what the comparison
  shows (spec FR-008/SC-004; depends on T009, T013)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion — no dependency on US2
- **User Story 2 (Phase 4)**: Depends on Foundational + US1's result-file shape (T006); its own new
  file (`aggregate_gurobi_default.py`, T010) only needs T003's schema, not US1's actual host runs,
  so it can be built in parallel with T008/T009
- **Polish (Phase 5)**: Depends on both user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependency on US2 — raw default-settings data exists whether or not
  the comparison view exists yet
- **User Story 2 (P2)**: Independently testable once US1's result-file shape is fixed (T006);
  comparison/figure generation doesn't require US1's own host-validation tasks to have run first

### Within Each User Story

- Loading the existing result (`_load_existing_result`) before the fresh solve (`_solve_default`)
  before the CLI that wires them together (US1)
- Comparison CSV before the figure (US2)
- Host validation task last in each phase

### Parallel Opportunities

- T004 (test file) can run in parallel with continued work on
  `run_gurobi_default_benchmark.py` once T002/T003 land
- T010 (`aggregate_gurobi_default.py`, new file) can proceed in parallel with T008/T009 (host
  validation of `run_gurobi_default_benchmark.py`) — different files, only needs T003's schema
- T012 (test file) can run in parallel with T013 (host/visual validation) once T010/T011 land
- T014 and T015 (Polish) can run in parallel — different files

---

## Parallel Example: Foundational Phase

```bash
# After T002/T003 (introspection extension + load logic) land, run together:
Task: "solve_gurobi + _load_existing_result tests in tests/test_gurobi_default_benchmark.py"  # T004
Task: "Continue User Story 1 implementation in run_gurobi_default_benchmark.py"               # T005+
```

## Parallel Example: User Story 1 / User Story 2 overlap

```bash
# Once T003 (existing-result schema) is fixed, run together:
Task: "Host-validate the single-model and --all run"                       # T008, T009
Task: "Implement aggregate_gurobi_default.py against the fixed schema"     # T010
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: run `--all` on a host with Gurobi licensed, inspect the
   `results/gurobi_default/<model>.json` files by hand — the raw out-of-the-box runtime numbers
   already exist, even before the comparison view is generated
5. Phase 4 turns that raw data into a single side-by-side view, but the core research answer
   (per-model default-settings runtime) is available after Phase 3 alone

### Incremental Delivery

1. Setup + Foundational → existing-result loading and introspection logic ready
2. User Story 1 → real default-settings results for every model, testable end-to-end
3. User Story 2 → same data, now visualized alongside cuOpt and deliberately-configured Gurobi
4. Polish → docs, lint, final confirmation that no shipped default changed

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- US2 lands after US1 primarily because of the result-file schema dependency, not deeper coupling
  — it still has its own Independent Test criterion
- No `gpugem/` changes anywhere in this feature — every task touches only `benchmarks/` or `tests/`
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently
