---

description: "Task list for MATLAB vs Python Lifted-Model Runtime & Fidelity Comparison"

---

# Tasks: MATLAB vs Python Lifted-Model Runtime & Fidelity Comparison

**Input**: Design documents from `/specs/015-matlab-python-lifting-comparison/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all present)

**Tests**: Included — plan.md's Technical Context commits to pytest coverage for the new
lift+Gurobi glue and the comparison/gating logic, matching this project's established
`benchmarks/` testing convention (Constitution Principle III's literal file list is not touched by
this feature, per research.md R4, but the project's actual practice on every sibling benchmark
feature is still honored).

**Organization**: Tasks are grouped by user story (P1/P1/P2 from spec.md) so each can be
implemented and independently tested on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Single project — new `benchmarks/` tooling reusing `gpugem.lifting` and `benchmarks.solve`
unchanged (plan.md Project Structure); no `gpugem/`-internal change. One input side
(`matlab/<model>.json`) is produced by a temporary script that lives entirely outside both repos'
tracked trees (research.md R8) — it is never itself a file in this task list's file paths.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare the output location for this feature's per-model results, distinct from every
prior feature's `results/` subdirectory.

- [X] T001 Create `benchmarks/results/matlab_python_lifting/` and
  `benchmarks/results/matlab_python_lifting/matlab/` directories, each with a `.gitkeep`

**Checkpoint**: Output locations exist; no new dependency required (plan.md confirms
numpy/scipy/pandas/matplotlib/gpugem/gurobipy already satisfy the Python side).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The worker, orchestrator, and figure script are needed, unchanged, by every user
story — US1 needs them to produce the runtime data and figure, US2 needs the orchestrator's
comparison logic to prove agreement is actually checked (not assumed), US3 needs the figure
script to exist before it can be validated against Constitution Principle VI.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 Create `benchmarks/_matlab_python_lifting_worker.py` per contracts/cli-contract.md:
  `--model NAME --lift-big FLOAT --time-limit SECONDS`; resolves the model via
  `benchmarks.models.build_lp`, lifts with `gpugem.lift_mass_balance`/`gpugem.lift_coupling`
  (research.md R4 — no new `gpugem` surface), solves the lifted system with
  `benchmarks.solve.solve_gurobi(method=2)` (research.md R3), maps the solution back with
  `gpugem.map_back`, and prints one `PipelineRun`-shaped (`pipeline="python"`) JSON object
  (data-model.md) to stdout as the last line — subprocess entry point, never invoked directly
- [X] T003 [P] Create `tests/test_matlab_python_lifting_comparison.py` with tests for the
  worker's pure pieces — `flux_summary` computation (e.g. L2 norm / max-abs of a mapped-back flux
  vector) and the `PipelineRun` JSON shape — on synthetic small LPs, no live Gurobi required
  (depends on T002)
- [X] T004 Create `benchmarks/run_matlab_python_lifting_comparison.py` per
  contracts/cli-contract.md: for each requested model (default: all six in-scope models), run or
  reuse `_matlab_python_lifting_worker` to produce `python_<model>.json`; read the corresponding
  `matlab_<model>.json` from `--matlab-results` (default `benchmarks/results/
  matlab_python_lifting/matlab/`), erroring clearly (spec FR-009) if that model's MATLAB-side
  result is missing — this script never runs MATLAB itself; build that model's
  `CrossLanguageComparisonRow` (data-model.md: `status_agrees`, `objective_agrees` within
  `OBJ_TOL`, `flux_agrees`, `aux_vars_match` as informational-only, `verified_correct`); write
  `benchmarks/results/matlab_python_lifting/comparison.csv` (depends on T002)
- [X] T005 [P] In `tests/test_matlab_python_lifting_comparison.py`, add tests for
  `CrossLanguageComparisonRow` construction on synthetic `PipelineRun`-shaped pairs: matching
  status/objective/flux → `verified_correct=True`; a status or objective or flux mismatch →
  `verified_correct=False` with the specific disagreement identifiable, never averaged away
  (spec FR-004/FR-005); an `n_aux_vars` mismatch alone → `aux_vars_match=False` but does not by
  itself force `verified_correct=False` (edge case); an `excluded=True` side → the row still
  appears with `excluded_models` populated, never silently dropped (spec FR-009/SC-004) (depends
  on T004)
- [X] T006 [P] Create `benchmarks/make_matlab_python_lifting_figure.py` per
  contracts/cli-contract.md: read `comparison.csv`, plot one MATLAB bar and one Python bar per
  in-scope model (log-scale y-axis spanning the small-to-whole-body range, annotated solve times),
  reusing the CVD-validated palette verbatim from
  `benchmarks/make_residual_tradeoff_figures.py::CONFIG_COLOR` (research.md R7) and this project's
  "FAILED correctness gate" annotation convention (`make_gurobi_default_figure.py`) for any row
  with `verified_correct=False`; write `benchmarks/figures/matlab_python_lifting_comparison.png`
  (300+ dpi) and `.pdf` (vector copy, Constitution Principle VI — PDF, not EPS); no baked-in title
  or caption inside the image (depends on T004)

**Checkpoint**: Foundation ready — worker, orchestrator, and figure scripts exist and their logic
is validated on synthetic data; user story implementation can now begin.

---

## Phase 3: User Story 1 - See MATLAB-lifted and Python-lifted Gurobi runtimes side by side (Priority: P1) 🎯 MVP

**Goal**: For each of the six in-scope models, both pipelines' lift-and-solve runtimes are
measured on this machine and shown together.

**Independent Test**: For every in-scope model, `comparison.csv` has both `matlab_solve_s` and
`python_solve_s` populated, and the figure shows both bars side by side.

### Implementation for User Story 1

- [X] T007 [US1] Write the temporary MATLAB comparison script at a scratch location outside both
  `gpuGEM/` and `cobratoolbox-f-develop/`'s tracked trees (research.md R8 — e.g. this session's
  scratchpad; never committed to either repo). For each in-scope model: load
  `benchmarks/model_cache/<model>.{xml,mat}` COBRA-natively (research.md R1 — identical file to
  the Python side, zero conversion), stack the mass-balance (`S`/`b`, all `'E'`) and coupling
  (`C`/`d`/`dsense`) blocks into one `LPproblem.A`/`.b`/`.csense` (research.md R2, mirroring
  `benchmarks/solve.py::solve_gurobi`'s own eq/upper/lower row grouping), call
  `reformulate(LPproblem, 1000, 1)`, solve via `changeCobraSolver('gurobi','LP')` +
  `solveCobraLP(LPproblem, 'method', 2)` (research.md R3 — barrier, matching the Python side), and
  write one `matlab_<model>.json` matching the `PipelineRun` schema (data-model.md), including
  `n_aux_vars`/`n_mass_balance_rows_lifted`/`n_coupling_rows_lifted` from `reformulate`'s own
  reported transform counts
- [X] T008 [US1] Run the T007 script for all six in-scope models on this machine; copy the six
  resulting `matlab_<model>.json` files into `benchmarks/results/matlab_python_lifting/matlab/`
  and commit them — the only MATLAB-side artifact that becomes part of the repo (spec FR-007;
  depends on T007)
- [X] T009 [US1] Run `python -m benchmarks.run_matlab_python_lifting_comparison` for all six
  in-scope models on this machine; confirm `benchmarks/results/matlab_python_lifting/
  comparison.csv` has `matlab_solve_s` and `python_solve_s` populated (not `NaN`) for every model
  (depends on T004, T008)
- [X] T010 [US1] Run `python -m benchmarks.make_matlab_python_lifting_figure` and visually confirm
  `benchmarks/figures/matlab_python_lifting_comparison.png` shows a MATLAB bar and a Python bar,
  both annotated with their actual solve time, for each of the six in-scope models (depends on
  T006, T009)

**Checkpoint**: User Story 1 is fully functional and independently testable — the side-by-side
runtime comparison exists for all six in-scope models.

---

## Phase 4: User Story 2 - Trust that the Python lifting port matches MATLAB's reformulate.m (Priority: P1)

**Goal**: Every model's cross-language agreement (status, objective, mapped-back flux) is actually
checked and honestly reported — never silently assumed or averaged away.

**Independent Test**: `comparison.csv` shows, for every in-scope model, whether the two pipelines'
status/objective/flux agreed, with any disagreement clearly identifiable rather than hidden inside
`verified_correct` alone.

### Implementation for User Story 2

- [X] T011 [US2] Inspect `comparison.csv` (from T009) and confirm, for every in-scope model,
  `status_agrees`, `objective_agrees`, and `flux_agrees` are all populated; for any model where one
  is `False`, confirm the figure (T010) visibly flags it via the gate-fail annotation rather than
  rendering it as a pass (quickstart.md step 4; depends on T009, T010)
- [X] T012 [US2] If T011 finds a disagreement: determine whether it is a genuine translation gap
  between `gpugem.lifting` and `reformulate.m` (in which case, fix in `gpugem/lifting.py` and
  re-run spec 013's own existing tests in `tests/test_lifting.py`/`tests/
  test_model_lifting_validation.py` to confirm no regression) or a legitimate,
  non-bug MATLAB/Gurobi-specific difference (in which case, document it — never silently patch
  over it). Conditional: only makes a change if T011 actually finds a disagreement (depends on
  T011)
- [X] T013 [P] [US2] In `tests/test_matlab_python_lifting_comparison.py`, add a regression test
  confirming the comparison logic never reports `verified_correct=True` when any of
  status/objective/flux actually disagree — synthetic mismatched `PipelineRun` pair, asserting the
  resulting row is `verified_correct=False` with the specific disagreement flagged (depends on
  T005)

**Checkpoint**: User Stories 1 AND 2 both work — the comparison is both complete and honest about
what did and didn't agree between the two implementations.

---

## Phase 5: User Story 3 - A publication-quality figure documenting how well lifting is working in both pipelines (Priority: P2)

**Goal**: The comparison figure meets this project's existing publication-figure standard, and the
comparison is documented in this project's established style.

**Independent Test**: The figure passes Constitution Principle VI's checks, and
`benchmarks/README.md` states plainly, per model, which pipeline was faster and whether they
agreed.

### Implementation for User Story 3

- [X] T014 [US3] Validate `benchmarks/figures/matlab_python_lifting_comparison.png`/`.pdf` against
  Constitution Principle VI: confirm the reused palette's CVD-safe validation still holds for this
  figure's specific color assignment (research.md R7 — confirm, not re-derive, since the palette
  is reused verbatim), confirm resolution/sizing/vector export matches this project's
  already-established target journal convention, confirm labels stay legible at final print size,
  and confirm no baked-in title/caption is rendered into the image itself (depends on T010)
- [X] T015 [US3] Append a "MATLAB vs Python lifted-model comparison" section to
  `benchmarks/README.md` documenting the new scripts (usage per quickstart.md), the comparison
  methodology (research.md R1-R6), and — using T009's real results — a plain-language summary per
  model of which pipeline was faster and whether the two agreed (spec SC-005), explicitly calling
  out any disagreement found in T011/T012 rather than only reporting speed (depends on T009, T011)
- [X] T016 [US3] If T012 found and documented a genuine, non-bug MATLAB/Gurobi-specific limitation,
  add it to `README.md`'s "Known limitations" section per Constitution Principle V. Conditional:
  only makes a change if such a limitation was actually found (depends on T012)

**Checkpoint**: All three user stories are independently functional — the comparison exists, is
correct and honestly reported, meets this project's publication standard, and is documented.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Lint, full regression check, and final end-to-end confirmation.

- [X] T017 [P] Run `ruff check` on `benchmarks/_matlab_python_lifting_worker.py`,
  `benchmarks/run_matlab_python_lifting_comparison.py`,
  `benchmarks/make_matlab_python_lifting_figure.py`,
  `tests/test_matlab_python_lifting_comparison.py` and fix any violations
  (Constitution Quality Standards: `line-length = 100`)
- [X] T018 [P] Run the full repo-wide test suite (`pytest tests/`) and confirm no regressions —
  in particular that `tests/test_lifting.py` and `tests/test_model_lifting_validation.py` still
  pass unchanged, since this feature touches no `gpugem/` file
- [X] T019 Run quickstart.md end-to-end (steps 1-4), confirm via `git diff`/`git status` that
  `gpugem/solver.py`, `gpugem/scaling.py`, `gpugem/lifting.py`, `gpugem/_defaults.py`,
  `benchmarks/solve.py`, and `benchmarks/models.py` are all untouched (plan.md Constraints), and
  confirm no MATLAB script file was accidentally committed to either `gpuGEM/` or
  `cobratoolbox-f-develop/` (spec FR-007 spot-check — `git status` in both repos shows nothing
  MATLAB-related staged or untracked-but-intended)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion — no dependency on US2/US3
- **User Story 2 (Phase 4)**: Depends on Foundational + US1's actual host runs (T009, T010) having
  produced the CSV/figure to inspect — genuinely sequenced after US1, not just file-shared (same
  pattern as spec 014's US1/US2 relationship)
- **User Story 3 (Phase 5)**: Depends on Foundational + US1's results (T009, T010) and, for T015,
  US2's inspection (T011)
- **Polish (Phase 6)**: Depends on all three user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependency on US2/US3 — the figure exists and shows both runtimes
  regardless of whether agreement has been separately inspected or documented yet
- **User Story 2 (P1)**: Genuinely depends on US1's host runs existing to inspect — equal spec
  priority to US1, but implementation-sequenced after it
- **User Story 3 (P2)**: Depends on US1's real results (for the figure to validate) and US2's
  findings (to document honestly, including any disagreement)

### Within Each User Story

- Worker before orchestrator (Foundational)
- Orchestrator before the figure script (Foundational)
- MATLAB-side script written and run (T007, T008) before the orchestrator can produce a real
  (non-erroring) comparison (T009)
- Orchestrator's real output before the figure can show real data (T009 → T010)

### Parallel Opportunities

- T003 and T005 (different test functions, same file) can be drafted in parallel once T002/T004
  land respectively
- T006 (figure script) can be built in parallel with T007 (writing the MATLAB script) — different
  files, no shared state, both only need `contracts/cli-contract.md`/data-model.md
- T017 and T018 (Polish, different concerns) can run in parallel

---

## Parallel Example: Foundational Phase

```bash
# Once T002 lands:
Task: "Worker pure-piece tests"                                 # T003

# Once T004 lands:
Task: "CrossLanguageComparisonRow construction tests"            # T005

# Independent of both, once contracts/data-model exist:
Task: "Figure script"                                            # T006
```

## Parallel Example: Foundational -> User Story 1 handoff

```bash
# Independent files, both gated only on design docs, not on each other:
Task: "Figure script (T006)"
Task: "Temporary MATLAB comparison script (T007)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: the figure exists and shows both pipelines' runtimes for all six
   in-scope models — this alone already answers the motivating "how do both codes perform in
   comparison to each other" question, before any dedicated agreement inspection or documentation
   pass
5. Phases 4-5 turn that into a verified-honest, publication-ready, documented result

### Incremental Delivery

1. Setup + Foundational → worker/orchestrator/figure scripts ready, validated on synthetic data
2. User Story 1 → the side-by-side runtime comparison exists, testable end-to-end on this machine
3. User Story 2 → confirmed honest about cross-language agreement (or any disagreement)
4. User Story 3 → figure meets Constitution VI, comparison documented
5. Polish → lint, full regression check, final confirmation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- This feature touches no `gpugem/` file at all — `gpugem.lift_mass_balance`, `lift_coupling`, and
  `map_back` are reused exactly as spec 013 already exposed them
- The temporary MATLAB script (T007) is deliberately never given a path inside either repo — do
  not "helpfully" commit it anywhere; only its per-model JSON output (T008) is a tracked artifact
  (research.md R8, spec FR-007)
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently
