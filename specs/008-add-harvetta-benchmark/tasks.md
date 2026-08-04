---

description: "Task list for Add Harvetta to the Benchmark Suite and Commit Model Files"

---

# Tasks: Add Harvetta to the Benchmark Suite and Commit Model Files

**Input**: Design documents from `/specs/008-add-harvetta-benchmark/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all present)

**Tests**: No new pure-function logic is introduced (one `REGISTRY` dict entry; every script
already generalizes over `ALL_MODELS`), so no new test tasks — consistent with feature 006's own
precedent for a model-onboarding-only change. The existing test suite is re-run as a regression
check in Polish.

**Organization**: Tasks are grouped by user story (P1/P1/P2 from spec.md) so each can be
implemented and independently tested on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Single project — extends the existing `benchmarks/` package plus one repository-configuration file
(`.gitignore`). No `gpugem/` changes (see plan.md Project Structure).

---

## Phase 1: Setup

**Purpose**: Confirm the prerequisite state this feature builds on before touching any code.

- [X] T001 Confirm `benchmarks/model_cache/Harvetta_1_03d.mat` is present (already placed by the
  user) and re-confirm, via `scipy.io.loadmat`, the structure findings research.md records:
  top-level key `"female"`, a genuine coupling block (`C`/`ctrs`/`d`/`dsense` present), and
  `"Whole_body_objective_rxn"` present verbatim in `rxns` — nothing to fix if this matches
  research R1, this is a pre-flight sanity check before registering the model

**Checkpoint**: Harvetta's file and structure are confirmed as expected; no surprises to plan
around before writing the `REGISTRY` entry.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The `REGISTRY` entry is the single piece every other task in this feature builds on —
both solve-based user stories need it to run a solve, and the git-tracking user story needs it to
know exactly which plain `.mat` file is now benchmark-suite-referenced.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 In `benchmarks/models.py`, add `REGISTRY["Harvetta"]` per `contracts/registry-entry.md`:
  `{"scale": "whole-body", "order": 9, "kind": "mat", "source": str(CACHE /
  "Harvetta_1_03d.mat"), "model_key": "female", "objective": "Whole_body_objective_rxn"}` (depends
  on T001)
- [X] T003 Confirm `benchmarks.models.ALL_MODELS` now includes `"Harvetta"` (ten entries total) by
  importing the module and checking `len(M.ALL_MODELS) == 10` and `"Harvetta" in M.ALL_MODELS` —
  no code change expected, this only verifies the dict-derived list picked up T002 (depends on T002)

**Checkpoint**: Foundation ready — every script that iterates `ALL_MODELS` or accepts `--model
Harvetta` now recognizes it; user story implementation can begin.

---

## Phase 3: User Story 1 - Get correctness-gated cuOpt vs Gurobi results for Harvetta (Priority: P1) 🎯 MVP

**Goal**: Harvetta has a correctness-gated cuOpt-vs-Gurobi result, and the existing cross-scale
comparison figure includes it.

**Independent Test**: Run the cross-scale benchmark tooling against Harvetta and confirm a result
(solve time, objective, solver status, feasibility residual, pass/fail) is produced for both
solvers, in the same form as every other model.

### Implementation for User Story 1

- [X] T004 [US1] On the GPU host, run `python -m benchmarks.run_benchmark --model Harvetta --reps
  3` and confirm `benchmarks/results/Harvetta.json` is written with both solvers' results,
  correctness-gated (status, residual, cross-solver objective agreement) exactly like every other
  model's result file — quickstart.md step 1 (depends on T002, T003)
- [X] T005 [US1] Confirm every other model's `benchmarks/results/<model>.json` is byte-for-byte
  unchanged after T004 (`git status`/`git diff --stat` on `benchmarks/results/` excluding the new
  `Harvetta.json`) — spec FR-006 (depends on T004)
- [X] T006 [US1] Run `python -m benchmarks.make_figure` and visually confirm
  `benchmarks/figures/benchmark_solvetime.png` shows all ten models, Harvetta correctly positioned
  by its solved variable count among the others, labels legible (no overlap regression) —
  quickstart.md step 3 (depends on T004)

**Checkpoint**: User Story 1 is fully functional and independently testable — Harvetta's baseline
cross-scale result exists and is visible in the existing comparison figure.

---

## Phase 4: User Story 2 - See Harvetta's per_constraint_residual=0 trade-off alongside every other model (Priority: P1)

**Goal**: Harvetta has a full three-configuration trade-off result with per-row violation
histograms (both S-block and, since Harvetta has a coupling block, C-block), and every trade-off
and violation-distribution figure includes it.

**Independent Test**: Run the trade-off benchmark tooling for Harvetta and confirm its result
includes all three configurations plus both violation histograms, and that regenerating the
figures includes Harvetta in all of them.

### Implementation for User Story 2

- [X] T007 [US2] On the GPU host, run `python -m benchmarks.run_residual_tradeoff --model
  Harvetta` and confirm `benchmarks/results/residual_tradeoff/Harvetta.json` is written with
  `shipped_default` reused from T004's result, `residual_0` solved fresh with both
  `violation_histogram_equations` and `violation_histogram_constraints` populated (Harvetta has a
  genuine coupling block per research R1), and `gurobi` reused — quickstart.md step 1 (depends on
  T004)
- [X] T008 [US2] Confirm every other model's `benchmarks/results/residual_tradeoff/<model>.json`
  is byte-for-byte unchanged after T007 — spec FR-006 (depends on T007)
- [X] T009 [US2] Run `python -m benchmarks.aggregate_residual_tradeoff` and confirm
  `benchmarks/results/residual_tradeoff/comparison.csv` now has 30 rows (10 models x 3
  configurations) (depends on T007)
- [X] T010 [US2] Run `python -m benchmarks.make_residual_tradeoff_figures` and visually confirm
  `residual_tradeoff_solvetime.png` / `residual_tradeoff_violations.png` show all ten models with
  legible, non-overlapping labels — quickstart.md step 3 (depends on T009)
- [X] T011 [US2] Run `python -m benchmarks.make_violation_distribution_figures` and visually
  confirm `violation_distribution_equations.png` shows all ten models and
  `violation_distribution_constraints.png` shows Harvetta alongside every other model with a
  coupling block, each individually legible (reusing the label-collision-avoidance fixes from
  feature 007 — a tenth/eighth model should not reintroduce the overlap bugs already fixed there)
  — quickstart.md step 3 (depends on T009)

**Checkpoint**: User Stories 1 AND 2 both work — Harvetta's full trade-off picture, including its
violation distributions, is visible everywhere every other model already is.

---

## Phase 5: User Story 3 - Reproduce every benchmarked model directly from the repository (Priority: P2)

**Goal**: Every `.mat`/`.xml` file the benchmark suite's `REGISTRY` references — Harvetta's and the
four models added in feature 006 — is tracked and committed; the size-heavy, unreferenced
`_lifted` variants stay untracked via a narrowed `.gitignore` pattern.

**Independent Test**: Confirm the five plain `.mat` files are no longer ignored and are staged for
commit, while the four `_lifted` variants remain ignored.

### Implementation for User Story 3

- [X] T012 [US3] Edit `.gitignore` per `contracts/gitignore-and-tracking.md`: replace
  `benchmarks/model_cache/*.mat` with `benchmarks/model_cache/*_lifted.mat`
- [X] T013 [US3] Run `git check-ignore benchmarks/model_cache/mWBM_S9_male_lifted.mat` (expect exit
  0, still ignored) and `git check-ignore benchmarks/model_cache/mWBM_S9_male.mat` (expect exit 1,
  no longer ignored) to confirm T012 took effect before staging anything (depends on T012)
- [X] T014 [US3] Stage the five plain `.mat` files `REGISTRY` references —
  `benchmarks/model_cache/Harvetta_1_03d.mat`,
  `benchmarks/model_cache/mWBM_{S9,S15,S23,S83}_male.mat` — plus `.gitignore`, per
  `contracts/gitignore-and-tracking.md`; confirm via `git status` that the four `_lifted` variants
  do **not** appear as staged or trackable (depends on T013)
- [X] T015 [US3] Confirm `git ls-files benchmarks/model_cache/` lists exactly 7 files (the 2
  already-tracked BiGG XMLs + the 5 newly-staged plain `.mat` files) once T014's staged files are
  committed — spec SC-004 (depends on T014)

**Checkpoint**: User Story 3 is independently functional and testable — the repository's model
cache now contains everything the benchmark suite's registry references, and only that.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, regression check, and the final end-to-end confirmation that nothing
was changed that shouldn't have been.

- [X] T016 [P] Update `benchmarks/README.md`'s model table to add Harvetta (scale, source,
  loader), and add a short note documenting the `.gitignore` policy change from T012 — every file
  `REGISTRY` references is now committed; `_lifted` variants remain excluded and unused — per
  plan.md's Constitution Check (Principle V)
- [X] T017 [P] Run the full `pytest` suite (`python -m pytest tests/ -q`) and confirm no
  regressions — the one new `REGISTRY` entry should not affect any existing test, since none are
  Harvetta-specific
- [X] T018 Run quickstart.md end-to-end (validation items 1-6) on the GPU host, and confirm `git
  diff --stat gpugem/` produces no output — the project's shipped defaults are unchanged regardless
  of how Harvetta performs (spec SC-005; depends on T006, T011, T015, T017)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS User Stories 1 and 2 (both need
  the `REGISTRY` entry to solve anything); does not block User Story 3's `.gitignore` edit itself,
  though T014's file list is only fully correct once T002 has landed
- **User Story 1 (Phase 3)**: Depends on Foundational completion
- **User Story 2 (Phase 4)**: Depends on Foundational completion AND User Story 1's result file
  (T004) — `_load_002_result` reads `results/Harvetta.json`, the file US1 produces
- **User Story 3 (Phase 5)**: Depends on Foundational completion (needs T002 to know the
  authoritative file list) — independent of US1/US2's GPU solves, can proceed in parallel with them
- **Polish (Phase 6)**: Depends on all three user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependency on US2/US3 — Harvetta's baseline result and figure exist
  whether or not the trade-off comparison or git-tracking change have happened yet
- **User Story 2 (P1)**: Depends on US1's result file existing (not on US1's figure or validation
  tasks) — the trade-off benchmark reuses US1's shipped-default/Gurobi numbers rather than
  re-solving them
- **User Story 3 (P2)**: Independently testable (ignore-rule and staged-file state can be verified
  on their own), no dependency on either solve-based story completing

### Within Each User Story

- Solve (T004/T007) before its own no-regression check (T005/T008) before its own figure
  regeneration (T006/T009-T011) — US1, US2
- `.gitignore` edit (T012) before verifying it took effect (T013) before staging files (T014)
  before the final tracked-file-count check (T015) — US3

### Parallel Opportunities

- User Story 3 (T012-T015) can proceed in parallel with User Story 1/2's GPU solves (T004-T011) —
  different files, only needs T002
- T016 and T017 (Polish) can run in parallel — different files

---

## Parallel Example: Foundational -> User Stories 1/3 overlap

```bash
# After T002/T003 (REGISTRY entry) land, run together:
Task: "GPU-solve Harvetta under the cross-scale benchmark"     # T004-T006 (US1)
Task: "Narrow .gitignore and stage the five plain .mat files"  # T012-T015 (US3)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks US1/US2)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: inspect `results/Harvetta.json` and the regenerated
   `benchmark_solvetime.png` by hand — Harvetta's baseline correctness-gated numbers already exist
5. Phase 4 turns that into the full speed/correctness trade-off picture; Phase 5 makes the whole
   suite reproducible from the repository alone — both are independently valuable on top of Phase 3

### Incremental Delivery

1. Setup + Foundational → Harvetta registered, ready to solve
2. User Story 1 → baseline cross-scale result, visible in the existing comparison figure
3. User Story 2 → full trade-off + violation-distribution picture, visible everywhere every other
   model already is
4. User Story 3 → the benchmark suite's model files are reproducible from the repository alone
5. Polish → docs, regression check, final confirmation that no shipped default changed

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- No `gpugem/` changes anywhere in this feature — every task touches only `benchmarks/`,
  `.gitignore`, or committed model files
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently
- T014/T015 involve staging/committing ≈ 299 MB of binary model data — a hard-to-reverse action
  (cleanly undoing it later requires a git history rewrite, not a plain revert); confirm with the
  user before running the actual `git add`/commit if this hasn't already been explicitly confirmed
