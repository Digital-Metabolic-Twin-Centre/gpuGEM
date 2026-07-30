---

description: "Task list for Expand Cross-Scale Benchmark to Additional Microbiome Models"

---

# Tasks: Expand Cross-Scale Benchmark to Additional Microbiome Models

**Input**: Design documents from `/specs/006-expand-microbiome-benchmark/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all present)

**Tests**: None planned — plan.md's Technical Context explains why: this feature adds registry
data and a one-line sort-key change to already-tested code paths (`002`'s `run_benchmark.py`/
`make_figure.py` have no existing unit tests of their own to extend). Correctness comes from the
unchanged correctness gate itself, validated by the GPU-host quickstart run, consistent with how
`002` was originally validated.

**Organization**: Tasks are grouped by user story (P1/P2/P3 from spec.md) so each can be
implemented and independently tested on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Single project — extends `benchmarks/` in place. No `gpugem/` changes (see plan.md Project
Structure).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Eliminate the accidental-commit risk before anything else touches
`benchmarks/model_cache/` — the ~637MB of new `.mat` files are currently untracked but
unprotected by `.gitignore` (research R2).

- [X] T001 Add `benchmarks/model_cache/*.mat` to `.gitignore` per
  `contracts/gitignore-and-figure-ordering.md`; confirm `git status --short
  benchmarks/model_cache/` shows no output for the `.mat` files afterward (the existing tracked
  `e_coli_core.xml`/`iML1515.xml` BiGG caches are unaffected — pattern is `.mat`-scoped)

**Checkpoint**: New model files can no longer be accidentally committed; safe to proceed.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The registry entries are needed before any user story can run anything — US1 solves
through them, US2's figure reads dimensions derived from them, US3's gate check applies to
whatever they produce.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 In `benchmarks/models.py`, add the 4 new `REGISTRY` entries (`S9`, `S15`, `S23`,
  `S83`) exactly per `contracts/registry-entries.md` — `scale="microbiome"`, `kind="mat"`,
  `source=str(CACHE / "mWBM_<name>_male.mat")` (using the existing module-level `CACHE`
  constant, research R1), `model_key=None`, `objective=None` (research R3)
- [X] T003 Verify each new entry loads correctly: run `python -c "from benchmarks import models
  as M; [print(M.build_lp(n)[1]) for n in ('S9','S15','S23','S83')]"` and confirm the printed
  provenance for each matches the dimensions already established in research.md (S9:
  1,111,943 vars; S15: 1,084,341; S23: 1,007,742; S83: 1,179,186), `obj_nonzero=1`,
  `maximize=True` — CPU-only sanity check, no solver required (depends on T002)

**Checkpoint**: Foundation ready — all 4 new models load and build correctly; user story
implementation can now begin.

---

## Phase 3: User Story 1 - Get correctness-gated results for the four new models (Priority: P1) 🎯 MVP

**Goal**: Each of the 4 new models solved with both cuOpt and Gurobi through the existing
benchmark tooling, correctness-gated identically to the 5 existing models.

**Independent Test**: Run the existing benchmark tooling against each of the four new models and
confirm a result (solve time, objective, solver status, feasibility residual, pass/fail) is
produced for both cuOpt and Gurobi, in the same form already used for the five existing models.

### Implementation for User Story 1

- [X] T004 [US1] On the GPU host, run `python -m benchmarks.run_benchmark --model S9 --reps 3`
  and confirm `results/S9.json` is written with a `[OK]`/`[FAILED]` outcome per the existing
  correctness gate (depends on T003)
- [X] T005 [US1] On the GPU host, run `python -m benchmarks.run_benchmark --model S15 --reps 3`
  and confirm `results/S15.json` is written (depends on T003)
- [X] T006 [US1] On the GPU host, run `python -m benchmarks.run_benchmark --model S23 --reps 3`
  and confirm `results/S23.json` is written (depends on T003)
- [X] T007 [US1] On the GPU host, run `python -m benchmarks.run_benchmark --model S83 --reps 3`
  and confirm `results/S83.json` is written (depends on T003)
- [X] T008 [US1] Run `git diff --stat benchmarks/results/{e_coli_core,iML1515,Harvey,S84,S85}.json`
  and confirm no output — the 5 existing models' results are byte-for-byte unchanged after
  running the 4 new ones (spec FR-007/SC-003; quickstart.md steps 2 and 5; depends on T004-T007)

**Checkpoint**: User Story 1 is fully functional and independently testable — all 4 new models
have real, correctness-gated results.

---

## Phase 4: User Story 2 - See all nine models in one size-ordered comparison (Priority: P2)

**Goal**: The existing comparison figure regenerated to show all 9 models, ordered strictly by
size.

**Independent Test**: Regenerate the comparison figure from the committed results and confirm it
shows all nine models, positioned along the axis in strictly increasing order of model size, not
grouped by scale class first.

### Implementation for User Story 2

- [X] T009 [US2] In `benchmarks/make_figure.py`, replace `df.sort_values(["_sc",
  "n_cols"])` with `df.sort_values("n_cols")` and remove the now-unused `SCALE_ORDER` list and
  `_sc` column assignment, per `contracts/gitignore-and-figure-ordering.md` (research R5)
- [X] T010 [US2] On the GPU host (or reusing T004-T007's already-committed results), run `python
  -m benchmarks.run_benchmark --all` (regenerates `benchmark.csv` via the existing
  `aggregate_csv()`, skipping all 9 already-solved models) then `python -m benchmarks.make_figure`
  and confirm: `benchmark.csv` has 9 rows, `figures/benchmark_solvetime.png` shows 9 bars/model
  groups ordered strictly by `n_cols` ascending — quickstart.md step 6 (depends on T008, T009)

**Checkpoint**: User Stories 1 AND 2 both work — real results for all 9 models, visualized
together in size order.

---

## Phase 5: User Story 3 - Never let a failed new model masquerade as a success (Priority: P3)

**Goal**: Confirm the existing (unmodified) correctness-gate/reporting logic genuinely satisfies
this requirement for the newly-added models, not just by assumption.

**Independent Test**: Observe what happens when a model fails the correctness gate and confirm
the failure is recorded and visible, not omitted from the results or figure.

### Implementation for User Story 3

- [X] T011 [US3] Review `benchmarks/run_benchmark.py`'s existing `run_one()`/`aggregate_csv()`
  logic against T004-T007's actual outcomes: confirm every one of the 4 new models' results
  carries an explicit `both_feasible` value (not merely assumed true), that any `FAILED` outcome
  (if one occurred) is tagged `[FAILED]` in the console output and `both_feasible=False` in its
  JSON and CSV row, and that `make_figure.py`'s existing "gate fail" annotation (crossing out a
  bar) would trigger for such a row — if all 4 new models passed cleanly, this is a code-path
  confirmation (the existing FAILED-handling logic is real and applies uniformly, not
  demonstrated by a live failure) rather than a live failure observation (spec Edge Cases; depends
  on T004-T007)

**Checkpoint**: All three user stories are independently satisfied — real results, a size-ordered
comparison, and confirmed-not-just-assumed honest failure reporting.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, lint, and the final end-to-end confirmation that nothing outside this
feature's scope changed.

- [X] T012 [P] Update the model table near the top of `benchmarks/README.md` to include the 4 new
  models (S9, S15, S23, S83) alongside the existing 5, matching the existing table's columns
  (model, scale, source, loader)
- [X] T013 [P] Run `ruff check` on `benchmarks/models.py` and `benchmarks/make_figure.py` (the
  only two modified files) and fix any violations (Constitution Quality Standards:
  `line-length = 100`), consistent with prior features' established convention of matching
  existing `benchmarks/` style rather than diverging
- [X] T014 Run quickstart.md end-to-end (steps 1-7) on the GPU host, confirming: `.gitignore`
  protects the new files (step 1), the 5 existing models stay untouched throughout (steps 2, 5),
  all 4 new models produce results (steps 3-4), the regenerated figure is correctly size-ordered
  (step 6), and `git diff --stat gpugem/_defaults.py` produces no output (step 7, spec FR-008;
  depends on T008, T010, T011)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion — no dependency on US2/US3
- **User Story 2 (Phase 4)**: Depends on Foundational + US1's results existing (T004-T008) for
  its own validation task (T010), though its code change (T009) has no such dependency and could
  land earlier
- **User Story 3 (Phase 5)**: Depends on US1's actual run outcomes (T004-T007) to review against
  — a pure verification task, no code of its own
- **Polish (Phase 6)**: Depends on all three user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependency on US2/US3 — real results exist whether or not the figure
  or the failure-reporting review have happened yet
- **User Story 2 (P2)**: Its code change (T009) is independent of US1's GPU runs; its validation
  (T010) needs US1's results to have something to plot
- **User Story 3 (P3)**: Purely a review/confirmation of existing code against US1's real
  outcomes — no new code, so "implementing" it is verifying it

### Within Each User Story

- Registry entries (Foundational) before any solve (US1)
- All 4 models solved before checking the 5 existing ones are untouched (US1's own internal order)
- Comparison CSV/figure regeneration only after all 4 new results exist (US2)
- Manual/quickstart GPU validation task last in each phase

### Parallel Opportunities

- T004-T007 (the 4 new model solves) touch different files (`results/S9.json` etc.) and have no
  dependency on each other — can run in parallel if GPU/Gurobi-license capacity allows, though
  sequential is also fine given each is a full benchmark solve
- T009 (figure code change) can proceed in parallel with T004-T008 (GPU runs) — different files,
  T009 doesn't need any new model's results to exist, only T010's validation does
- T012 and T013 (Polish) can run in parallel — different files

---

## Parallel Example: Foundational → User Story 1 handoff

```bash
# Once T002/T003 (registry + sanity check) land, these have no dependency on each other:
Task: "Solve S9 through the existing benchmark tooling"   # T004
Task: "Solve S15 through the existing benchmark tooling"  # T005
Task: "Solve S23 through the existing benchmark tooling"  # T006
Task: "Solve S83 through the existing benchmark tooling"  # T007
```

## Parallel Example: User Story 1 / User Story 2 code change overlap

```bash
# T009 doesn't need any GPU run to exist -- can proceed alongside T004-T007:
Task: "Change make_figure.py's sort key to size-only"      # T009
Task: "Solve the 4 new models on the GPU host"              # T004-T007
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (protect the new files first)
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: 4 new correctness-gated results exist, 5 existing ones untouched — the
   core coverage-expansion goal is already met before any figure work happens
5. Phases 4-5 turn that into a legible comparison and confirm the honest-failure-reporting
   guarantee holds, but the underlying data already has standalone value after Phase 3

### Incremental Delivery

1. Setup + Foundational → new files protected, registry entries ready
2. User Story 1 → 4 new correctness-gated results, testable end-to-end
3. User Story 2 → same results, now visualized alongside the existing 5, size-ordered
4. User Story 3 → confirmed (not just assumed) that a failure would be honestly reported
5. Polish → docs, lint, final full-scope confirmation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- This feature's entire code change is 4 registry dict entries + 1 sort-key line + 1 `.gitignore`
  line — most tasks are GPU-host validation/observation, not new implementation, by design (see
  plan.md Summary)
- No `gpugem/` changes anywhere in this feature
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently
