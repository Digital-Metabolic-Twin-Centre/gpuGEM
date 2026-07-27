---

description: "Task list for S85 Multi-Objective cuOpt vs Gurobi Benchmark"

---

# Tasks: S85 Multi-Objective cuOpt vs Gurobi Benchmark

**Input**: Design documents from `/specs/003-s85-multi-objective-benchmark/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all present)

**Tests**: Included — plan.md's Technical Context and Project Structure commit to `tests/test_s85_objectives.py` covering the objective registry and aggregation/outlier math (GPU/Gurobi-free), and quickstart.md step 2 runs it explicitly.

**Organization**: Tasks are grouped by user story (P1/P2/P3 from spec.md) so each can be implemented and independently tested on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Single project — extends the existing `benchmarks/` package in place (see plan.md Project Structure). No new top-level directory.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare the output location for this feature's results, distinct from the existing `results/S85.json` cross-scale-benchmark artifact.

- [ ] T001 Create `benchmarks/results/s85_objectives/` directory with a `.gitkeep` so committed sweep results (per-objective JSON, `objectives.json`, `summary.json`/`.csv`) have a stable, version-controlled home before any code runs

**Checkpoint**: Output location exists; no new dependencies required (plan.md confirms cuopt-cu12/gurobipy/scipy/numpy already satisfy this feature).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The objective registry and the LP-objective-override helper are needed by all three user stories (every story solves "S85 with objective X" in some way) — this MUST exist before any user story phase starts.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T002 In `benchmarks/s85_objectives.py`, create the `OBJECTIVES` list of `ObjectiveDefinition` entries (`id`, `reaction`, `category`, `rationale`, `is_baseline`) per research.md R1's selection approach: 1 whole-body baseline (`Whole_body_objective_rxn`, `is_baseline=True`), ~10 organ/tissue biomass-maintenance reactions, ~5 immune/blood-cell biomass reactions, ~4 microbiome-associated objectives (via the model's `Microbiota` mask) — resolve exact reaction names by loading `mWBM_S85_male.mat` (`benchmarks.models.MODELS_DIR`) and filtering `rxns` for `*biomass*`/`*maintenance*` plus the `Microbiota` mask, per data-model.md's `ObjectiveDefinition` schema and validation rules (unique `reaction` values, exactly one `is_baseline=True`, `len(OBJECTIVES) >= 20` unless fewer valid candidates exist, in which case document the actual count in a module docstring)
- [ ] T003 [P] In `benchmarks/s85_objectives.py`, add a `write_objectives_json()` function that serializes `OBJECTIVES` to `benchmarks/results/s85_objectives/objectives.json` per data-model.md's `ObjectiveDefinition` schema (depends on T002)
- [ ] T004 In `benchmarks/s85_objectives.py`, add `build_lp_for_objective(objective_id)` that reuses `benchmarks.models`'s S85 `.mat` loader (`gpugem.loaders.from_mat`) and the existing single-objective-override pattern already used for Harvey in `benchmarks/models.py` (`build_lp`, lines ~90-105), but resolves the reaction index from the requested `OBJECTIVES` entry instead of a hardcoded reaction name; returns `(lp, prov)` shaped like `benchmarks.models.build_lp`'s return value (depends on T002)
- [ ] T005 [P] Create `tests/test_s85_objectives.py` with registry validation tests (no GPU/Gurobi required): every `reaction` in `OBJECTIVES` is unique, every `reaction` resolves to exactly one index in the S85 model's `rxns` array, exactly one entry has `is_baseline=True`, and `len(OBJECTIVES) >= 20` or the shortfall is documented (depends on T002)

**Checkpoint**: Foundation ready — `OBJECTIVES`, `build_lp_for_objective`, and `objectives.json` all exist and are validated; user story implementation can now begin.

---

## Phase 3: User Story 1 - Compare solvers across many objectives on S85 (Priority: P1) 🎯 MVP

**Goal**: Solve S85 with both cuOpt and Gurobi across all ~20 objectives and produce a per-objective + averaged runtime comparison report.

**Independent Test**: Run the sweep against the S85 model and confirm a report is produced containing, for every configured objective, cuOpt's and Gurobi's solve time, objective value, and feasibility status, plus an overall average runtime per solver across the objective set.

### Implementation for User Story 1

- [ ] T006 [US1] In `benchmarks/run_objective_sweep.py`, implement `solve_objective(objective_id, reps, time_limit, res_tol, obj_tol, versions)`: build the LP via `build_lp_for_objective` (T004), run `benchmarks.solve.solve_gurobi` then `benchmarks.solve.solve_cuopt` for `reps` repeats each, gate correctness via `benchmarks.residual.feasibility_residual`/`objectives_agree` (same pattern as `benchmarks/run_benchmark.py`'s `_run_solver`/`run_one`), and write `benchmarks/results/s85_objectives/<objective_id>.json` matching data-model.md's `ObjectiveSweepResult` schema and `contracts/result-json.schema.json` (no progress output or skip-existing logic yet — those are added in US2/US3)
- [ ] T007 [US1] In `benchmarks/run_objective_sweep.py`, implement the `main()` CLI entrypoint: `--objective ID` (mutually exclusive with `--all`), `--all`, `--reps` (default 1), `--time-limit` (default 900.0), `--res-tol` (default 1e-4), `--obj-tol` (default 1e-6) — iterating `OBJECTIVES` in file order and calling `solve_objective` (T006) for each requested objective, per `contracts/cli-contract.md` (depends on T006, T003)
- [ ] T008 [P] [US1] Create `benchmarks/aggregate_sweep.py`: read every `benchmarks/results/s85_objectives/*.json` (excluding `objectives.json`/`summary.json`), compute the `SweepSummary` (per-solver mean/median/min/max solve time over `both_feasible=True` rows, `runtime_ratio_median`, `baseline_ratio` from the `is_baseline` objective, `outliers` per research.md R4's `[median/2, median*2]` rule), and write `benchmarks/results/s85_objectives/summary.json` and `summary.csv` per `contracts/csv-columns.md` (one row per objective, gated and non-gated) — runnable standalone with no solver import, matching `benchmarks/make_figure.py`'s existing "regenerable from committed results" property
- [ ] T009 [US1] In `benchmarks/run_objective_sweep.py`, call `aggregate_sweep`'s summary-regeneration at the end of an `--all` invocation, per `contracts/cli-contract.md` (depends on T007, T008)
- [ ] T010 [P] [US1] In `tests/test_s85_objectives.py`, add aggregation/outlier unit tests against synthetic per-objective timing data: mean/median/min/max computed only over `both_feasible=True` rows, `runtime_ratio_median` and outlier flagging match research.md R4's rule, non-gated rows are present in `summary.csv` output but excluded from the stats (depends on T008)
- [ ] T011 [US1] Run quickstart.md step 3 (`python benchmarks/run_objective_sweep.py --objective whole_body`) on the GPU host and confirm `results/s85_objectives/whole_body.json`'s gurobi/cuopt medians are consistent with the existing `results/S85.json` numbers (~52s / ~509s) — this is the check that the new code path reproduces the already-trusted `002` result before trusting it for the other objectives (depends on T009)

**Checkpoint**: User Story 1 is fully functional and independently testable — running `--all` (even without progress output or resumability) produces a complete per-objective + aggregated report.

---

## Phase 4: User Story 2 - Monitor a multi-hour run in progress (Priority: P2)

**Goal**: Make a running sweep observable — which objective/solver is active, and elapsed time — so a multi-hour unattended run can be trusted rather than treated as a black box.

**Independent Test**: Start the sweep and, while it is running, observe progress output that identifies the current objective (name and position out of the total count), which solver is active, and elapsed time for that step and for the run overall.

### Implementation for User Story 2

- [ ] T012 [US2] In `benchmarks/run_objective_sweep.py`, add start/finish progress print lines around each solver call in `solve_objective`/the `--all` loop: `[n/total] <id> (<reaction>) -- <solver> solving...` on start and `[n/total] <id> -- <solver> done in <Xs>  status=<status>` on finish, per `contracts/cli-contract.md`'s illustrated output (depends on T007)
- [ ] T013 [US2] In `benchmarks/run_objective_sweep.py`, add a `--heartbeat-s` CLI flag (default 30) and a background daemon thread (start/stop via `threading.Event`) around each blocking `solve_gurobi`/`solve_cuopt` call that prints `"...still solving, <Ns> elapsed"` every `--heartbeat-s` seconds, per research.md R2 (depends on T012)
- [ ] T014 [US2] Run quickstart.md step 3/4 pattern on the GPU host for an objective expected to exceed 30s (e.g. `whole_body`) and confirm heartbeat lines appear at the expected cadence during the cuOpt solve, distinguishing "still solving" from a hang (depends on T013)

**Checkpoint**: User Stories 1 AND 2 both work — a full sweep now shows live progress without changing what gets recorded in the results.

---

## Phase 5: User Story 3 - Resume an interrupted sweep (Priority: P3)

**Goal**: An interrupted multi-hour `--all` run can be restarted without losing or re-solving already-completed objectives.

**Independent Test**: Interrupt a sweep partway through, restart it, and confirm that already-completed objectives are skipped (not re-solved) while remaining objectives are solved and added to the results; confirm `--force` re-solves a specific objective on request.

### Implementation for User Story 3

- [ ] T015 [US3] In `benchmarks/run_objective_sweep.py`, add a skip-if-exists check before calling `solve_objective` for each objective in the `--all`/`--objective` loop (print `[skip] <id> (exists; --force to rerun)`), plus a `--force` flag that bypasses the skip and overwrites the existing result — mirroring `benchmarks/run_benchmark.py`'s existing `--force` semantics (depends on T013)
- [ ] T016 [US3] In `benchmarks/run_objective_sweep.py`, scope the non-zero exit-code (`any_failed`) check to only objectives *attempted in this invocation*, so a resumed run isn't failed by a pre-existing skipped result, per `contracts/cli-contract.md` (depends on T015)
- [ ] T017 [US3] On the GPU host, start `--all`, interrupt it (Ctrl-C) after at least one objective completes, restart with `--all`, and confirm completed objectives print `[skip]` while remaining ones solve; then confirm `--objective <id> --force` re-solves and overwrites a specific completed objective (quickstart.md step 5) (depends on T016)

**Checkpoint**: All three user stories are independently functional — the sweep can be run to completion, monitored live, and safely resumed after interruption.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, lint, and full end-to-end validation across all three stories together.

- [ ] T018 [P] Add a "S85 multi-objective sweep" section to `benchmarks/README.md` documenting `run_objective_sweep.py` / `aggregate_sweep.py` usage, per plan.md's Project Structure note
- [ ] T019 [P] Run `ruff check benchmarks/s85_objectives.py benchmarks/run_objective_sweep.py benchmarks/aggregate_sweep.py tests/test_s85_objectives.py` and fix any violations (Constitution Quality Standards: `line-length = 100`)
- [ ] T020 Run quickstart.md end-to-end (steps 1-6) on the GPU host and record whether `summary.json`'s `baseline_ratio` sits near `runtime_ratio_median` or appears in `outliers` — this is the answer to the motivating question (spec SC-001) and should be captured in the sweep's `summary.json`/`summary.csv` as the durable record (depends on T011, T014, T017)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion — no dependency on US2/US3
- **User Story 2 (Phase 4)**: Depends on Foundational completion; edits the same file US1 created (`run_objective_sweep.py`), so proceeds after US1 in this plan even though it adds no new *data* dependency on US1's tasks beyond that file existing
- **User Story 3 (Phase 5)**: Same reasoning as US2 — edits `run_objective_sweep.py` after US2's edits land
- **Polish (Phase 6)**: Depends on all three user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependency on US2/US3's behavior — a report is produced whether or not progress lines or resumability exist yet
- **User Story 2 (P2)**: Independently testable (progress output can be verified without interrupting anything), but its tasks land in the same file US1 built, so it is sequenced after US1 here
- **User Story 3 (P3)**: Independently testable (skip/`--force` behavior can be verified on its own), sequenced after US2 for the same shared-file reason

### Within Each User Story

- Foundational entities (`OBJECTIVES`, `build_lp_for_objective`) before any solving logic
- Core solve-and-record loop (US1) before progress instrumentation (US2) before resume logic (US3) — each layers onto the same CLI file
- Manual/quickstart validation task last in each phase

### Parallel Opportunities

- T003 and T005 (different files, both depend only on T002) can run in parallel
- T008 (new file `aggregate_sweep.py`) can run in parallel with T006/T007 (`run_objective_sweep.py`) — different files
- T010 (test file) can run in parallel with T007/T009 (different files) once T008 lands
- T018 and T019 (Polish) can run in parallel — different files

---

## Parallel Example: Foundational Phase

```bash
# After T002 (OBJECTIVES list) completes, run together:
Task: "Add write_objectives_json() in benchmarks/s85_objectives.py"       # T003
Task: "Registry validation tests in tests/test_s85_objectives.py"          # T005
```

## Parallel Example: User Story 1

```bash
# T006/T007 (run_objective_sweep.py) and T008 (aggregate_sweep.py) touch different files:
Task: "Implement solve_objective() + main() CLI in benchmarks/run_objective_sweep.py"  # T006, T007
Task: "Implement aggregate_sweep.py summary computation"                                # T008
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: run `--all` on the GPU host, confirm `summary.json` answers whether S85's ~10x cuOpt/Gurobi gap generalizes across objectives
5. This alone answers the motivating research question from spec.md — Phases 4-5 improve operability of long runs but aren't required for the core answer

### Incremental Delivery

1. Setup + Foundational → registry + LP builder ready
2. User Story 1 → full report generation, testable end-to-end (MVP — answers the research question)
3. User Story 2 → same sweep, now observable during multi-hour runs
4. User Story 3 → same sweep, now safely resumable after interruption
5. Polish → docs, lint, full validation run

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- US2 and US3 tasks are sequenced after US1 because they all edit `benchmarks/run_objective_sweep.py`, not because they depend on US1's results — each remains independently testable per its own Independent Test criterion
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently
- No tests exist for solver correctness itself (that's covered by reusing `benchmarks.residual`/`benchmarks.solve` unchanged, per plan.md's Constitution Check) — the new tests here only cover the registry and aggregation math that this feature actually adds
