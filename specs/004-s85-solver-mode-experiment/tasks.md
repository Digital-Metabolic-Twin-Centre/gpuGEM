---

description: "Task list for S85 Alternative Solver-Mode Experiment"

---

# Tasks: S85 Alternative Solver-Mode Experiment

**Input**: Design documents from `/specs/004-s85-solver-mode-experiment/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all present)

**Tests**: Included — plan.md's Technical Context commits to pytest coverage for (a) the additive
`FBAResult.solved_by` change (Constitution Principle III applies since this touches
`gpugem/solver.py`) and (b) the variant registry + speedup/best-candidate comparison math
(GPU/Gurobi-free), and quickstart.md step 2 runs both explicitly.

**Organization**: Tasks are grouped by user story (P1/P2/P3 from spec.md) so each can be
implemented and independently tested on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Single project — extends the existing `benchmarks/` package, plus one small additive change
inside `gpugem/` (see plan.md Project Structure).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare the output location for this feature's results, distinct from `002`'s
`results/S85.json` and `003`'s `results/s85_objectives/`.

- [X] T001 Create `benchmarks/results/s85_solver_modes/` directory with a `.gitkeep`

**Checkpoint**: Output location exists; no new dependencies required (plan.md confirms
cuopt-cu12/gurobipy/scipy/numpy already satisfy this feature).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The variant registry and the `solved_by` plumbing are needed by all three user
stories (every story solves "S85 under variant X and records which method answered" in some
form) — this MUST exist before any user story phase starts.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 In `gpugem/result.py`, add `solved_by: Optional[str] = None` field to `FBAResult`
  per `contracts/gpugem-api-addition.md` (docstring explaining it's from cuOpt's
  `sol.get_solved_by()`, most informative for `method=Concurrent`, `None` if unavailable)
- [X] T003 In `gpugem/solver.py`'s `solve()`, immediately after `sol = Solve(dm, settings)`,
  capture `sol.get_solved_by()` (its `SolverMethod` enum `.name`, e.g. `"PDLP"`) into a local
  variable using the same defensive `try/except` style already used for `get_lp_stats()`, and
  pass it through as `FBAResult(..., solved_by=...)` — no change to existing default-merging,
  settings application, or status/feasibility logic (depends on T002)
- [X] T004 [P] In `tests/test_solver.py`, add a test that solves the existing `tiny_lp` fixture
  and asserts `result.solved_by` is populated with a valid `SolverMethod` name (or is `None` if
  the installed cuOpt version doesn't support it — do not hard-fail on absence), per
  `contracts/gpugem-api-addition.md` (Constitution Principle III — depends on T003)
- [X] T005 In `benchmarks/solver_mode_variants.py`, create the `SOLVER_MODE_VARIANTS` list of 4
  `SolverModeVariant` entries per data-model.md: `baseline` (`cuopt_kwargs={}`, `is_baseline=True`),
  `methodical1` (`cuopt_kwargs={"pdlp_solver_mode": 2}`), `concurrent`
  (`cuopt_kwargs={"method": 0}`), `barrier_cold` (`cuopt_kwargs={"method": 3}`) — each with a
  `rationale` string drawn from the prior investigation notes in the spec's input — plus a
  `validate_variants()` function that checks every `cuopt_kwargs` key against cuOpt's live
  `get_solver_parameter_names()` registry and that exactly one entry has `is_baseline=True`
  (research R5, R8; validation rules in data-model.md)
- [X] T006 [P] Create `tests/test_solver_mode_variants.py` with registry validation tests (no
  GPU/Gurobi required): `id` values unique, exactly one `is_baseline=True`, every
  `cuopt_kwargs` key resolves against `get_solver_parameter_names()` (depends on T005)

**Checkpoint**: Foundation ready — `SOLVER_MODE_VARIANTS` and `FBAResult.solved_by` both exist
and are validated; user story implementation can now begin.

---

## Phase 3: User Story 1 - Run each candidate setting against S85 and see whether it helps (Priority: P1) 🎯 MVP

**Goal**: Solve S85 with cuOpt under the baseline settings and under each of the three candidate
variants, recording solve time, iteration count, and correctness for every one.

**Independent Test**: Run the experiment against S85 and confirm that a result (solve time,
iteration count, correctness) is recorded for the baseline and for each of the three candidates,
on the same objective and the same underlying LP.

### Implementation for User Story 1

- [X] T007 [US1] Create `benchmarks/_solver_mode_worker.py`: given a `variant_id` CLI argument,
  look it up in `SOLVER_MODE_VARIANTS` (T005), build S85's LP via
  `benchmarks.s85_objectives.build_lp_for_objective("whole_body")`, call
  `gpugem.solve(..., time_limit=<passed in>, check_feasibility=True, **variant.cuopt_kwargs)`,
  compute the feasibility residual via `benchmarks.residual.feasibility_residual`, and print one
  JSON object to stdout (`solve_s`, `status`, `solved_by`, `iters`, `objective`,
  `residual_inf`) — this is the subprocess entry point, never invoked directly by a user
  (research R1, R2; `contracts/cli-contract.md`)
- [X] T008 [US1] Create `benchmarks/run_solver_mode_experiment.py` orchestrator: solve Gurobi
  once via `benchmarks.solve.solve_gurobi` on the same LP (research R6) as the shared correctness
  reference; for each of the 4 variants in `SOLVER_MODE_VARIANTS` order, skip if
  `results/s85_solver_modes/<id>.json` already exists and `--force` wasn't given (print
  `[skip] <id>`), otherwise launch `python -m benchmarks._solver_mode_worker <id>` via
  `subprocess.run(capture_output=True, text=True, check=False)` (no timeout yet — added in
  US3/T015), parse the worker's stdout JSON, classify the outcome (`"Completed"` if returncode 0
  and valid JSON parsed; `"DidNotComplete"`/`"crashed"` otherwise, per research R4), compute
  `obj_rel_diff`/`verified_correct` against the shared Gurobi reference using
  `benchmarks.residual.objectives_agree`, and write `results/s85_solver_modes/<id>.json` per
  data-model.md's `VariantResult` schema and `contracts/result-json.schema.json`; add
  `--time-limit` (default 900.0) and `--force` CLI flags (depends on T007)
- [X] T009 [US1] On the GPU host, run
  `python -m benchmarks.run_solver_mode_experiment` for just the `baseline` variant (temporarily
  isolate it or let the full run reach it first) and confirm `results/s85_solver_modes/
  baseline.json`'s `solve_s` is consistent with the existing ~509-520s cuOpt figures from
  `002`/`003` and `solved_by="PDLP"` — this is the check that the new subprocess-based path
  reproduces the already-trusted result before trusting it for the untested candidates
  (quickstart.md step 3; depends on T008)
- [X] T010 [US1] On the GPU host, run the full experiment (`python -m
  benchmarks.run_solver_mode_experiment`) and confirm every one of the 4 variants produces a
  recorded `VariantResult` (`Completed` or `DidNotComplete`), none silently missing from
  `results/s85_solver_modes/` (depends on T008, T009)

**Checkpoint**: User Story 1 is fully functional and independently testable — raw per-variant
results exist for baseline and all three candidates, which is the minimum needed to know what
each setting does.

---

## Phase 4: User Story 2 - Compare all candidates against the baseline in one place (Priority: P2)

**Goal**: Produce a single, clear comparison showing each candidate's solve time and correctness
relative to the baseline, identifying the best verified-correct candidate if one exists.

**Independent Test**: After User Story 1's results exist, produce a report showing each
candidate's solve time and iteration count alongside the baseline's with a speedup/slowdown
figure, and confirm it correctly identifies the fastest verified-correct candidate (if any beats
the baseline).

### Implementation for User Story 2

- [X] T011 [P] [US2] Create `benchmarks/aggregate_solver_modes.py`: read the (up to 4)
  `results/s85_solver_modes/*.json` files, compute `speedup = baseline_solve_s /
  candidate_solve_s` per verified-correct candidate (research R7), identify `best_candidate_id`
  (verified-correct, `speedup > 1`, minimal `solve_s`) or `null` if none qualify, and write
  `results/s85_solver_modes/summary.json` + `summary.csv` per data-model.md's
  `VariantComparison` and `contracts/csv-columns.md` (exactly 4 CSV rows regardless of outcome)
  — runnable standalone with no solver import (depends on T008 for the result-file shape, not on
  T009/T010's actual GPU runs, so can proceed in parallel with those)
- [X] T012 [US2] In `benchmarks/run_solver_mode_experiment.py`, call
  `aggregate_solver_modes`'s summary regeneration at the end of a run, per
  `contracts/cli-contract.md` (depends on T008, T011)
- [X] T013 [P] [US2] In `tests/test_solver_mode_variants.py`, add comparison-math unit tests on
  synthetic `VariantResult`-shaped data: speedup computed correctly, best-candidate selection
  picks the fastest verified-correct candidate with `speedup > 1`, and the "no candidate beats
  baseline" case is reported explicitly (not omitted or defaulted to a misleading value) —
  matches spec User Story 2 Acceptance Scenario 3 (depends on T011)
- [X] T014 [US2] On the GPU host, run `python -m benchmarks.aggregate_solver_modes` (or let
  T012's wiring do it) against T010's results and confirm `summary.json`/`summary.csv` correctly
  reflect each variant's speedup and correctness, per quickstart.md step 6 (depends on T010, T012)

**Checkpoint**: User Stories 1 AND 2 both work — the full comparison report is available on top
of User Story 1's raw results.

---

## Phase 5: User Story 3 - Don't let an unproven setting hang the experiment (Priority: P3)

**Goal**: Guarantee that a candidate which doesn't finish within its time budget is recorded as
inconclusive and the remaining candidates still get attempted.

**Independent Test**: Cap a candidate's allotted solve time and confirm that if it doesn't finish
first, the experiment reports a clear "did not finish within the time budget" outcome for that
candidate and still proceeds to run the remaining candidates.

### Implementation for User Story 3

- [X] T015 [US3] In `benchmarks/run_solver_mode_experiment.py`, add `timeout=variant_time_limit +
  60` to the `subprocess.run` call (research R3) and catch `subprocess.TimeoutExpired`,
  classifying that outcome as `"DidNotComplete"` / `outcome_reason="timeout"` (distinct from
  T008's existing `"crashed"` classification for a clean nonzero exit) — the process is killed by
  `subprocess.run`'s own timeout handling, and the loop MUST continue to the next variant
  afterward (depends on T008)
- [X] T016 [US3] On the GPU host, force a timeout (e.g. temporarily pass a very small
  `--time-limit` while testing `barrier_cold` or `methodical1` specifically) and confirm: (a) it
  is recorded as `DidNotComplete`/`"timeout"`, not a false success or an unclassified crash; (b)
  the experiment proceeds to and completes the remaining variants; (c) the User Story 2 summary
  (T011/T014) marks the timed-out variant clearly rather than omitting it — matches spec User
  Story 3 Acceptance Scenarios 1-2 (depends on T015, T011)

**Checkpoint**: All three user stories are independently functional — the experiment produces
results, a comparison, and survives an unproven setting misbehaving.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, lint, and the final end-to-end run that answers the motivating
question.

- [X] T017 [P] Add a "S85 solver-mode experiment" section to `benchmarks/README.md` documenting
  `run_solver_mode_experiment.py` / `aggregate_solver_modes.py` usage, per plan.md's Project
  Structure note
- [X] T018 [P] Run `ruff check` on `gpugem/solver.py`, `gpugem/result.py`,
  `benchmarks/solver_mode_variants.py`, `benchmarks/_solver_mode_worker.py`,
  `benchmarks/run_solver_mode_experiment.py`, `benchmarks/aggregate_solver_modes.py`,
  `tests/test_solver_mode_variants.py` and fix any violations (Constitution Quality Standards:
  `line-length = 100`), consistent with `003`'s established convention of matching existing
  `benchmarks/` style rather than diverging
- [X] T019 Run quickstart.md end-to-end (steps 1-6) on the GPU host and record, in the
  experiment's own `summary.json`, whether any candidate variant beats the baseline while
  remaining `verified_correct` — the answer to spec SC-001. If any candidate surfaces a new
  solver limitation (e.g. `barrier_cold` OOMs, or `concurrent`'s winning method is inconsistent
  across repeat runs), add it to `README.md`'s "Known limitations" section per Constitution
  Principle V (depends on T010, T014, T016)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion — no dependency on US2/US3
- **User Story 2 (Phase 4)**: Depends on Foundational + US1's result-file shape (T008); its own
  code (`aggregate_solver_modes.py`, T011) is a new file and does not need US1's actual GPU runs
  to exist first, only the schema T008 defines
- **User Story 3 (Phase 5)**: Edits the same file US1/US2 built (`run_solver_mode_experiment.py`),
  so sequenced after both here, though its Independent Test doesn't require US2's comparison to
  exist
- **Polish (Phase 6)**: Depends on all three user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependency on US2/US3's behavior — raw results exist whether or not a
  comparison report or timeout handling exist yet
- **User Story 2 (P2)**: Independently testable once US1's result-file shape is fixed; its
  comparison logic doesn't care whether a variant completed via a happy path or (after US3 lands)
  via a classified timeout — `verified_correct=false` rows are handled either way
- **User Story 3 (P3)**: Independently testable (timeout behavior can be verified with a
  deliberately tiny time limit) — sequenced last here only because it edits the same
  orchestrator file US1 built

### Within Each User Story

- Worker (subprocess entry point) before orchestrator (US1)
- Orchestrator's result-file shape fixed before the comparison tool consumes it (US1 → US2)
- Manual/quickstart GPU validation task last in each phase

### Parallel Opportunities

- T004 (test file) can run in parallel with T005/T006 (different files) once T003 lands
- T006 (test file) can run in parallel with T007+ (different files) once T005 lands
- T011 (`aggregate_solver_modes.py`, new file) can proceed in parallel with T009/T010 (GPU
  validation of the orchestrator) — different files, only needs T008's schema
- T013 (test file) can run in parallel with T012/T014 (different files) once T011 lands
- T017 and T018 (Polish) can run in parallel — different files

---

## Parallel Example: Foundational Phase

```bash
# After T003 (solved_by capture) completes, run together:
Task: "Add solved_by test in tests/test_solver.py"                       # T004
Task: "Create SOLVER_MODE_VARIANTS registry in benchmarks/solver_mode_variants.py"  # T005
```

## Parallel Example: User Story 1 / User Story 2 overlap

```bash
# Once T008 (orchestrator + VariantResult schema) lands, run together:
Task: "GPU-validate baseline + full run"                                  # T009, T010
Task: "Implement aggregate_solver_modes.py against the fixed schema"      # T011
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: run the full experiment on the GPU host, inspect the 4 raw
   `VariantResult` JSON files by hand — this alone already tells you which settings even complete
   and roughly how fast, before any polish
5. Phases 4-5 turn that raw data into an actionable comparison and make the experiment safe to
   re-run unattended, but the core research answer is available after Phase 3 alone

### Incremental Delivery

1. Setup + Foundational → registry + `solved_by` plumbing ready
2. User Story 1 → raw per-variant results, testable end-to-end
3. User Story 2 → same experiment, now with a clear speedup comparison and best-candidate call
4. User Story 3 → same experiment, now resilient to an untested setting hanging
5. Polish → docs, lint, final recorded finding (and a Known Limitations update if warranted)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- US2 and US3 land after US1 primarily because of shared-file edits (`run_solver_mode_experiment.py`)
  or schema dependencies, not because of a deeper coupling — each still has its own Independent
  Test criterion
- This is the first feature in this repo to touch `gpugem/` itself (T002-T004); keep that change
  strictly additive per `contracts/gpugem-api-addition.md` — no existing behavior, defaults, or
  return values for current callers should change
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently
