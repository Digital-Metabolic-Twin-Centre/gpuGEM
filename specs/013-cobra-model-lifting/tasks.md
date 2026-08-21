---

description: "Task list for Opt-In Model Lifting for Badly-Scaled LPs"

---

# Tasks: Opt-In Model Lifting for Badly-Scaled LPs

**Input**: Design documents from `/specs/013-cobra-model-lifting/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all present)

**Tests**: Included — plan.md's Technical Context commits to pytest coverage per Constitution
Principle III (this feature touches `gpugem/solver.py` and adds `gpugem/lifting.py`), and
quickstart.md step 1 runs them explicitly.

**Organization**: Tasks are grouped by user story (P1/P1/P2 from spec.md) so each can be
implemented and independently tested on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Single project — this is the second feature (after `specs/004-s85-solver-mode-experiment/`) to
add a new module inside `gpugem/` itself, plus a `benchmarks/` validation script (plan.md Project
Structure).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare the output location for this feature's validation results, distinct from
every prior feature's `results/` subdirectory.

- [X] T001 Create `benchmarks/results/model_lifting/` directory with a `.gitkeep`

**Checkpoint**: Output location exists; no new dependency required (plan.md confirms
numpy/scipy already satisfy this feature — no new third-party dependency).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The core `reformulate.m` translation (`gpugem/lifting.py`) is needed, unchanged, by
all three user stories — solving-with-lifting (US1), correctness comparison (US2), and scale/
traceability verification (US3) all depend on the same transform functions existing and being
individually correct first.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 Create `gpugem/lifting.py` with the `LiftingMapping` dataclass per data-model.md
  (`n_original_vars`, `n_original_stoich_rows`, `n_original_coupling_rows`, `big`,
  `mass_balance_lifted_rows`, `coupling_lifted_rows`, `n_aux_vars`, `n_aux_rows`) — module
  docstring states this is a faithful port of
  `cobratoolbox/src/base/solvers/rescale/reformulate.m` and explicitly notes it is a separate,
  different algorithm from `gpugem/scaling.py` (research.md R3), which this feature does not
  modify
- [X] T003 In `gpugem/lifting.py`, implement `lift_mass_balance(S, b, big=1000.0) ->
  (S_lifted, b_lifted, LiftingMapping)` per research.md R1: for each homogeneous equality row
  (all of `S`/`b`, since gpuGEM's `S` block is always the mass-balance equalities) with at least
  one entry `|value| > big`, compute one **shared** auxiliary chain for that row —
  `dum_i = max(floor(log(|value_i|)/log(big)), 1)` per large entry, `stp = min(|value_i| **
  (1/(dum_i+1)) for i in row)` (the correct translation of MATLAB's `mode()` on all-distinct
  floats — research.md R1 point 3, do **not** use `statistics.mode()`), build the bidiagonal
  chain (`aux_k - stp*aux_{k+1} = 0`) of length `max(dum_i)`, connect the original row via a
  single `-stp` entry to the first chain link, and connect each entry's own `dum_i` level back to
  its *original* column with coefficient `original_value / stp**dum_i`; zero the original large
  entries. Add inline comments referencing the specific `reformulate.m` line ranges each part
  translates (spec FR-008/SC-004 traceability)
- [X] T004 In `gpugem/lifting.py`, implement `lift_coupling(C, d_lb, d_ub, big, mapping) ->
  (C_lifted, d_lb_lifted, d_ub_lifted, LiftingMapping)` per research.md R2: identify rows with
  exactly two nonzero, opposite-sign entries and a homogeneous bound (`d_lb==0` or `d_ub==0`);
  for each, `dum = max(floor(log(qty)/log(big)), 1)` (`qty` = the row's one large entry),
  `stp = qty ** (1/(dum+1))` (plain root, no sharing needed — one large value per row), append a
  `dum`-length sign-consistent chain, zero the original entry; rows not matching the pattern pass
  through unchanged. Same traceability comment convention as T003 (depends on T002)
- [X] T005 In `gpugem/lifting.py`, implement `map_back(fluxes_lifted, mapping) -> np.ndarray` per
  research.md R5: a literal `fluxes_lifted[:mapping.n_original_vars]` prefix slice — no inverse
  arithmetic (depends on T002)
- [X] T006 [P] In `gpugem/__init__.py`, export `lift_mass_balance`, `lift_coupling`, `map_back`,
  `LiftingMapping` from `gpugem.lifting`, mirroring the existing `scale_model`/`remap_fluxes`/
  `CoefficientScalingMapping` export pattern (contracts/gpugem-api-addition.md — depends on T002)
- [X] T007 [P] Create `tests/test_lifting.py` with a hand-constructed small example (mirroring
  `tests/test_scaling.py`'s existing precedent for this class of transform, research.md R7 layer
  2): assert `S_lifted @ x_lifted` reproduces `S @ x_original` on original rows and exactly zero
  on new auxiliary rows, for an `x_lifted` built by hand from the mapping's recorded chain
  metadata; include a case with **multiple** large entries sharing one row (to actually exercise
  the shared-chain/`stp`-sharing logic, not just a single-entry case) (depends on T003)
- [X] T008 [P] In `tests/test_lifting.py`, add the equivalent hand-verifiable test for
  `lift_coupling` (two-nonzero-opposite-sign row, confirm the chain reproduces the original
  coupling relationship and a non-matching row passes through unchanged) (depends on T004)
- [X] T009 [P] In `tests/test_lifting.py`, add `map_back` tests: correct prefix slice, and a
  clear error (not silent truncation) if `fluxes_lifted` is shorter than
  `mapping.n_original_vars` (depends on T005)

**Checkpoint**: Foundation ready — `gpugem.lifting`'s transform functions exist, are individually
verified correct on hand-constructed examples, and are exported; user story implementation can now
begin.

---

## Phase 3: User Story 1 - Solve with lifting on, get back an unlifted-model-shaped, correct answer (Priority: P1) 🎯 MVP

**Goal**: `gpugem.solve(..., lift=True)` (and, for free, `solve_cobra`/`FBASolver`) transforms the
model, solves it, and returns a result expressed purely in the original model's variable space.

**Independent Test**: Solve the same model once with `lift` left at its default and once with
`lift=True`; confirm identical behavior in the first case and an original-variable-shaped result
in the second.

### Implementation for User Story 1

- [X] T010 [US1] In `gpugem/solver.py`'s `solve()`, add `lift: bool = False, lift_big: float =
  1000.0` as keyword-only parameters, consumed and removed **before** `params.update(cuopt_kwargs)`
  so they are never mistaken for a cuOpt solver parameter (contracts/gpugem-api-addition.md).
  When `lift=False`, behavior MUST be byte-for-byte identical to today (spec FR-001) — no
  existing code path may execute differently
- [X] T011 [US1] In the same function, when `lift=True`: call `gpugem.lifting.lift_mass_balance`
  on `S`/`b` and, if `C` is not `None`, `gpugem.lifting.lift_coupling` on `C`/`d_lb`/`d_ub`,
  using `lift_big`; build the `DataModel` from the **lifted** arrays instead of the originals
  (depends on T010, T003, T004)
- [X] T012 [US1] After `Solve()` returns, when `lift=True`: truncate the raw solution via
  `gpugem.lifting.map_back` **before** constructing `FBAResult` (so `fluxes` is always in the
  original variable space regardless of whether lifting was used internally — spec FR-005;
  depends on T011, T005)
- [X] T013 [US1] Recompute `FBAResult.feasibility` against the **original**, unlifted `S`/`b`/
  `C`/`d_lb`/`d_ub` using the mapped-back fluxes when `lift=True` — never the lifted system's own
  internal residual (research.md R6; depends on T012)
- [X] T014 [P] [US1] In `tests/test_lifting.py`, add an integration test: solve `e_coli_core`
  (via `gpugem.solve_cobra`) with `lift=False` and `lift=True` and assert the two results have
  matching `objective` and `fluxes` (within this project's existing tolerance) — this model has
  no coefficients exceeding the default `lift_big`, so it also exercises the "lifting is a safe
  no-op" edge case (spec Edge Cases) in the same test (depends on T010-T013)
- [X] T015 [P] [US1] In `tests/test_lifting.py`, add a regression test proving the "free"
  integration claim (research.md R4): `gpugem.solve_cobra(model, lift=True)` and
  `gpugem.FBASolver(S, b, lb, ub, c, lift=True).solve()` both succeed and produce results
  matching a direct `gpugem.solve(..., lift=True)` call — with **zero** changes made to
  `solve_cobra.py` or the `FBASolver` class as part of this feature (depends on T010-T013)
- [X] T016 [US1] On the host, run quickstart.md step 2 (`e_coli_core`, `lift=True` vs.
  `lift=False`) and confirm matching objectives and zero auxiliary variables introduced (depends
  on T010-T013)

**Checkpoint**: User Story 1 is fully functional and independently testable — the opt-in
solve-lift-map-back round trip works and every existing caller's default behavior is unchanged.

---

## Phase 4: User Story 2 - Trust that lifting doesn't change the answer (Priority: P1)

**Goal**: Prove, across models of different scale, that a lifted-and-mapped-back solve matches
the unlifted solve — the correctness bar this entire feature exists to meet.

**Independent Test**: Solve `e_coli_core` and `S85` both lifted and unlifted; confirm both report
verified-correct parity (matching objective, residual within this project's existing tolerance).

### Implementation for User Story 2

- [X] T017 [US2] Create `benchmarks/run_model_lifting_validation.py`: for a given model (via
  `benchmarks.models.build_lp`), solve unlifted (`gpugem.solve`) and lifted
  (`gpugem.solve(..., lift=True)`), build a `LiftedSolveComparison` per data-model.md
  (`unlifted_objective`, `lifted_objective`, `objective_agrees` via
  `benchmarks.residual.objectives_agree`, `unlifted_residual_inf`/`lifted_residual_inf` against
  the **original** `S`/`b` — reusing `benchmarks.residual.feasibility_residual`,
  `verified_correct`, `unlifted_solve_s`/`lifted_solve_s` recorded for context only per spec
  FR-009), write `results/model_lifting/<model>.json`; `--model NAME` CLI flag (depends on
  T010-T013)
- [X] T018 [P] [US2] In a new `tests/test_model_lifting_validation.py`, add unit tests for the
  comparison/`verified_correct` math on synthetic (non-GPU) `LiftedSolveComparison`-shaped data:
  matching results are verified-correct, a residual over tolerance or an objective mismatch is
  correctly flagged `verified_correct=False`, never silently passed (depends on T017)
- [X] T019 [US2] On the GPU host, run `python -m benchmarks.run_model_lifting_validation --model
  e_coli_core` and confirm `[OK]` verified-correct with zero auxiliary rows/vars introduced
  (quickstart.md step 3; depends on T017)
- [X] T020 [US2] On the GPU host, run `python -m benchmarks.run_model_lifting_validation --model
  S85` and confirm `[OK]` verified-correct, and that **both** the mass-balance and coupling
  lifting paths were actually exercised (nonzero rows lifted in each block) — matching
  research.md R8's empirical prediction (mass-balance block spans `[1e-6, 2e5]`; ~68,259 coupling
  rows expected to be lifted at the default threshold); if either block lifts zero rows, that is
  a research-invalidating result requiring investigation before proceeding, not a silent pass
  (quickstart.md step 3; depends on T017)

  **Actual outcome**: both paths exercised exactly as predicted (242 mass-balance rows, 68,259
  coupling rows — matching research.md R8's number precisely). Result is `[FAILED]`, not `[OK]`:
  objective matches exactly but the mapped-back residual (1.32e-3) exceeds this project's 1e-4
  tolerance, despite `lifted_status=Optimal`. Investigated (not silently accepted, per spec FR-006
  Acceptance Scenario 3): the transform itself is independently verified exact; the gap is
  cuOpt's own solver tolerance on the auxiliary chain being amplified (by the chain's step size,
  up to ~999) when read back into the original row. A tighter-tolerance follow-up narrowed but did
  not close the gap and did not converge in the same time budget. Documented in
  `benchmarks/README.md` and `README.md`'s Known Limitations — a genuine, honestly-reported
  negative result, not a silent pass and not a bug in the transform.

**Checkpoint**: User Stories 1 AND 2 both work — lifting is usable and proven correct on both a
small no-op case and a large model that genuinely exercises both transforms.

---

## Phase 5: User Story 3 - Confirm the lifted model's scale is actually fixed, and the translation is faithful (Priority: P2)

**Goal**: Independently verifiable evidence that lifting corrects coefficient magnitudes (not
just restructures them) and that the implementation is traceable to `reformulate.m` without
needing a MATLAB/Octave installation.

**Independent Test**: Inspect a badly-scaled model's coefficient ranges before/after lifting;
confirm the mass-balance and coupling transforms in `gpugem/lifting.py` can each be traced to
`reformulate.m`'s corresponding section.

### Implementation for User Story 3

- [X] T021 [US3] In `benchmarks/run_model_lifting_validation.py`, compute a `ScaleReport` per
  data-model.md alongside the `LiftedSolveComparison`: for every row `LiftingMapping` recorded as
  lifted, the largest `|coefficient|` among its descendants **before** vs. **after** lifting, for
  both the mass-balance and (if present) coupling blocks; include `n_mass_balance_rows_lifted`,
  `n_coupling_rows_lifted`, `n_aux_vars_added`; write it into the same
  `results/model_lifting/<model>.json` (depends on T017)
- [X] T022 [US3] In the same script, assert (and report a clear `[FAILED]`, non-zero exit — not
  a silent warning) that every `*_max_abs_after` value is `<= lift_big` for every validated
  model — spec FR-007's "verify and report," not merely assume the algorithm worked (depends on
  T021)
- [X] T023 [P] [US3] Review `gpugem/lifting.py`'s `lift_mass_balance`/`lift_coupling` (from T003/
  T004) and confirm every non-trivial step (row selection, shared-chain construction, the
  `mode()`-is-`min()` translation, the coupling pattern match) carries a comment citing the exact
  `reformulate.m` line range it corresponds to (spec FR-008/SC-004) — add any missing references
  found during review; this is a review/documentation task, not new transform logic (depends on
  T003, T004)
- [X] T024 [US3] On the GPU host, inspect `results/model_lifting/S85.json`'s `scale_report` and
  confirm the before/after coefficient-range comparison is present and shows correction (e.g.
  mass-balance max `|coef|` well above `lift_big` before, `<= lift_big` after) — quickstart.md
  step 4 (depends on T020, T022)

**Checkpoint**: All three user stories are independently functional — lifting works, is proven
correct, and is independently verifiable as both scale-correcting and faithful to its reference
algorithm.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, lint, and the final end-to-end confirmation.

- [X] T025 [P] Add a "Opt-in model lifting" section to `benchmarks/README.md` documenting
  `run_model_lifting_validation.py` usage, the `lift`/`lift_big` parameters on `gpugem.solve()`,
  and the explicit note that runtime/performance comparison is deferred future work (spec FR-009)
- [X] T026 [P] Run `ruff check` on `gpugem/lifting.py`, `gpugem/solver.py`, `gpugem/__init__.py`,
  `benchmarks/run_model_lifting_validation.py`, `tests/test_lifting.py`,
  `tests/test_model_lifting_validation.py` and fix any violations (Constitution Quality
  Standards: `line-length = 100`), matching the established project style
- [X] T027 Run quickstart.md end-to-end (steps 1-4) on the GPU host and record, in this feature's
  README section, the final confirmation that lifting is verified-correct on both validated
  models and that scale correction is demonstrated. If lifting surfaces any new limitation (e.g.
  an S85 coupling-row shape this research didn't anticipate, or a numerical edge case), add it to
  `README.md`'s "Known limitations" section per Constitution Principle V (depends on T016, T019,
  T020, T024)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion — no dependency on US2/US3
- **User Story 2 (Phase 4)**: Depends on Foundational + US1 (T010-T013 — needs `lift=True` to
  actually work before it can be validated); its own new file (`run_model_lifting_validation.py`)
  does not need US3's scale-report addition to exist first
- **User Story 3 (Phase 5)**: Depends on Foundational + US2's script existing (T017 — extends the
  same file rather than creating a new one) — sequenced last among the three stories, matching
  its P2 priority
- **Polish (Phase 6)**: Depends on all three user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependency on US2/US3 — the round trip works whether or not it has
  been validated across models yet or has a scale report
- **User Story 2 (P1)**: Genuinely depends on US1 (can't validate `lift=True` correctness before
  `lift=True` exists) — equal spec priority to US1, but implementation-sequenced after it
- **User Story 3 (P2)**: Extends US2's script rather than being fully independent of it — but its
  own Independent Test (inspecting coefficient ranges, reviewing traceability) is conceptually
  separable from US2's correctness question

### Within Each User Story

- Mass-balance transform, coupling transform, and map-back (Foundational) before any solve()
  integration (US1)
- `solve()` integration (US1) before the validation script can meaningfully call `lift=True`
  (US2)
- Correctness comparison (US2) before scale-report/traceability review makes sense to add (US3)
- Manual/quickstart GPU validation task last in each phase

### Parallel Opportunities

- T006 (`__init__.py` exports) can run in parallel with T007-T009 (test files) once T002-T005 land
- T007, T008, T009 (different test functions, same file — coordinate on file but logically
  independent) can be drafted in parallel once their respective implementation (T003/T004/T005)
  lands
- T014 and T015 (different test functions) can run in parallel once T010-T013 land
- T023 (review/documentation task, no code change) can run in parallel with T021-T022 (script
  changes) — different files
- T025 and T026 (Polish, different files) can run in parallel

---

## Parallel Example: Foundational Phase

```bash
# After T002 (LiftingMapping) lands, T003 and T004 can proceed in parallel (different functions,
# same file -- coordinate on file but logically independent):
Task: "Implement lift_mass_balance in gpugem/lifting.py"   # T003
Task: "Implement lift_coupling in gpugem/lifting.py"        # T004

# Once T003/T004/T005 land, run together:
Task: "Export lifting.py's public names in gpugem/__init__.py"  # T006
Task: "Hand-verifiable mass-balance test in tests/test_lifting.py"  # T007
Task: "Hand-verifiable coupling test in tests/test_lifting.py"      # T008
Task: "map_back tests in tests/test_lifting.py"                     # T009
```

## Parallel Example: User Story 1

```bash
# Once T010-T013 (solve() integration) land, run together:
Task: "e_coli_core round-trip integration test"                     # T014
Task: "solve_cobra/FBASolver free-inheritance regression test"      # T015
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories; this is also where most of the
   actual `reformulate.m` translation complexity lives)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: `gpugem.solve(model, lift=True)` works end-to-end on `e_coli_core`,
   with `lift=False` behavior completely unchanged — this alone proves the API shape and the
   round trip before spending GPU time on the large-model correctness proof
5. Phases 4-5 turn that working round trip into a *proven*, *independently verifiable* one

### Incremental Delivery

1. Setup + Foundational → `gpugem.lifting`'s transform functions exist and are individually
   correct
2. User Story 1 → the opt-in round trip works on `gpugem.solve()` (and, for free, every other
   entry point), testable end-to-end
3. User Story 2 → proven correct on both a no-op small model and a genuinely badly-scaled large
   one
4. User Story 3 → independently verifiable scale-correction evidence and reference-algorithm
   traceability
5. Polish → docs, lint, final recorded confirmation

---

## Notes

- [P] tasks = different files, no dependencies (or independent functions within a shared file,
  called out explicitly where that's the case)
- [Story] label maps task to specific user story for traceability
- This is the second feature in this repo to touch `gpugem/` itself (after
  `specs/004-s85-solver-mode-experiment/`'s `FBAResult.solved_by` addition) — keep the change
  strictly additive per `contracts/gpugem-api-addition.md`: no existing behavior, defaults, or
  return values for current callers should change when `lift` is left at its default
- `gpugem/scaling.py` is explicitly out of scope for modification (research.md R3) — do not
  "helpfully" merge or extend it while implementing this feature
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently
