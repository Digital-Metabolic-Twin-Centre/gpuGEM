---

description: "Task list for Cross-Model Objective-Panel Credibility Benchmark"

---

# Tasks: Cross-Model Objective-Panel Credibility Benchmark

**Input**: Design documents from `/specs/011-objective-panel-benchmark/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all present)

**Tests**: Included — plan.md's Technical Context commits to pytest coverage for the reaction-lookup
helper (both model kinds), the median-display-vs-all-repeats-gate distinction (research R7), and the
two-CSV aggregation logic, all GPU/Gurobi-free.

**Organization**: Tasks are grouped by user story (P1/P2/P2 from spec.md) so each can be implemented
and independently tested on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Single project — extends the existing `benchmarks/` package. No `gpugem/` changes (see plan.md
Project Structure).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare the output location for this feature's results, distinct from every other
feature's own results subdirectory (`results/gurobi_default/`, `results/residual_tradeoff/`, etc.)
and from the objective-panel *source* CSVs (`benchmarks/objective_candidates/`, prior work, read but
never written here).

- [X] T001 Create `benchmarks/results/objective_panel/` directory with a `.gitkeep`

**Checkpoint**: Output location exists; no new dependencies required (plan.md confirms gurobipy and
cuopt-cu12 are already used elsewhere in this project).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The reaction-lookup helper and the panel/settings loaders are needed by every user
story — US1 solves using them, US2's figures and US3's correctness data both depend on what US1
produces from them.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 In `benchmarks/objective_panel.py`, implement `_build_lp_with_objective(model,
  reaction_id)`: call `benchmarks.models.build_lp(model)` for the base LP/provenance, then resolve
  `reaction_id` to a column index per the model's kind — `model.reactions` order for `kind="cobra"`
  models, `benchmarks.models._mat_rxns(path, model_key)` + `np.where` for `kind="mat"` models
  (research R2, generalizing the lookup `models.build_lp`'s own `meta["objective"]` branch and
  `s85_objectives.py::build_lp_for_objective` already use) — override `lp["c"]` to a zero vector
  with `1.0` at that index and `lp["maximize"]=True`
- [X] T003 In `benchmarks/objective_panel.py`, implement `_load_panel(model)`: read
  `benchmarks/objective_candidates/<model>.csv`, return a list of `{"reaction_id":...,
  "category":...}` dicts in file order (research R3 — only these two columns are consumed), error
  out clearly if the file is missing
- [X] T004 In `benchmarks/objective_panel.py`, implement `_load_settings(model)`: read
  `benchmarks/results/<model>.json`, return `{"reps":..., "time_limit":..., "res_tol":...,
  "obj_tol":...}` (research R1), error out clearly if missing
- [X] T005 [P] Create `tests/test_objective_panel.py` with tests for `_build_lp_with_objective`:
  correct index resolution for a known `e_coli_core` (cobra-kind) reaction using the already-cached
  `benchmarks/model_cache/e_coli_core.xml`, and correct index resolution for a mat-kind model with
  `benchmarks.models._mat_rxns` monkeypatched to a small synthetic reaction-ID array (no large
  `.mat` file load required) — depends on T002
- [X] T006 [P] In `tests/test_objective_panel.py`, add tests for `_load_panel` (fixture CSV in
  `tmp_path`, confirms `reaction_id`/`category` extraction and file-order preservation, and a clear
  error on a missing file) and `_load_settings` (fixture JSON, confirms field extraction and a clear
  error on a missing file) — depends on T003, T004

**Checkpoint**: Foundation ready — an arbitrary objective can be resolved to an LP for any model, and
that model's panel and settings can be loaded; user story implementation can now begin.

---

## Phase 3: User Story 1 - Check whether the published single-objective numbers are representative, not a fluke (Priority: P1) 🎯 MVP

**Goal**: For every model, produce a real, repeated, median-based result for every objective in that
model's committed panel, using both solvers exactly as already published for that model.

**Independent Test**: Run the benchmark tooling against every objective already curated for a given
model and confirm a runtime and objective-value result (each the median of multiple repeated runs)
is produced for every one of them, with both solvers.

### Implementation for User Story 1

- [X] T007 [US1] In `benchmarks/run_objective_panel.py`, implement `solve_one_objective(model,
  reaction_id, category, settings, reps, heartbeat_s)`: build the LP via
  `_build_lp_with_objective` (T002), solve with both `benchmarks.solve.solve_gurobi` and
  `benchmarks.solve.solve_cuopt` `reps` times each (reusing `run_objective_sweep.py`'s
  `_with_heartbeat` + per-repeat loop pattern verbatim), compute each solver's median `solve_s`/
  `objective`/`residual_inf` across repeats (FR-003/FR-004), gate feasibility as `all()` across
  every individual repeat — never the median alone (research R7) — and assemble the
  `ObjectivePanelResult` dict per `data-model.md` (depends on T002, T004)
- [X] T008 [US1] Implement the `main()` CLI in `benchmarks/run_objective_panel.py`: `--model NAME`
  / `--all`, `--reps` (default `3`, research R1), `--force`, `--heartbeat-s` (default `30.0`); for
  each requested model, load its panel (T003) and settings (T004), iterate objectives in panel
  order, skip (`[skip] <model>/<objective_id>`) if
  `results/objective_panel/<model>/<objective_id>.json` already exists and `--force` wasn't given
  (spec FR-011), otherwise call `solve_one_objective` (T007) and write the result JSON; call
  `aggregate_objective_panel.main()` at the end of the run (depends on T003, T004, T007)
- [X] T009 [US1] In `tests/test_objective_panel.py`, add a test for the correctness-gate-per-repeat
  rule (research R7): a synthetic case where one repeat individually fails (bad status or
  out-of-tolerance residual) while the *median* residual looks acceptable still yields
  `both_feasible=False` — no GPU/Gurobi required (depends on T007)
- [X] T010 [US1] On a host with both solvers available, run `python -m
  benchmarks.run_objective_panel --model e_coli_core` (the smallest panel, 10 objectives) and
  confirm 10 result JSONs are written, each with `reps=3` repeats per solver and correctly computed
  median fields — quickstart.md "start small" step (depends on T008)
- [X] T011 [US1] On the same host, run `python -m benchmarks.run_objective_panel --model S85` in
  the background, confirm heartbeat lines print during long solves (research R4), interrupt the run
  partway, and confirm re-running the identical command resumes rather than re-solving
  already-completed objectives — quickstart.md "background run" step (spec FR-011/SC-004; depends
  on T008, T010)

**Checkpoint**: User Story 1 is fully functional and independently testable — real, per-objective,
median-based results exist for every objective in a model's panel, for both solvers.

---

## Phase 4: User Story 2 - See the full comparison and spot outliers at a glance (Priority: P2)

**Goal**: Turn the collected per-objective results into two aggregate CSVs and one figure per
model, so a model's already-published single-objective number can be judged against its full panel
visually.

**Independent Test**: Generate the CSVs and figures from already-collected results and confirm they
show, for every model, every objective's runtime for both solvers, regenerable without either
solver installed.

### Implementation for User Story 2

- [X] T012 [P] [US2] Create `benchmarks/aggregate_objective_panel.py`: read whichever
  `results/objective_panel/<model>/*.json` files exist, in `benchmarks.models.ALL_MODELS` registry
  order, write `results/objective_panel/objective_runtime.csv` and `benchmark_details.csv` per
  `contracts/csv-columns.md` (two rows per (model, objective) — one per solver) — standalone, no
  solver import (spec FR-007; depends on T007's `ObjectivePanelResult` schema, not on host runs)
- [X] T013 [US2] Create `benchmarks/make_objective_panel_figures.py`: read both CSVs, produce one
  `benchmarks/figures/objective_panel_<model>.png` per model with at least one result (log-scale
  y-axis on `runtime_s_median`, two bars per objective using the already CVD-validated
  `CONFIG_COLOR` pair from `make_gurobi_default_figure.py`, a `both_feasible=False` objective
  visually marked as failed, and that model's already-published baseline objective visually
  distinguished from the rest of the panel) per `contracts/figure-contract.md` — no solver import
  (depends on T012)
- [X] T014 [P] [US2] In `tests/test_objective_panel.py`, add tests for
  `aggregate_objective_panel`'s row assembly (two rows per (model, objective), correct columns per
  `contracts/csv-columns.md`) using fixture JSONs — no GPU/Gurobi required (depends on T012)
- [X] T015 [US2] On the host (or with T010/T011's already-committed results), run `python -m
  benchmarks.aggregate_objective_panel && python -m benchmarks.make_objective_panel_figures` and
  visually confirm the `e_coli_core` and `S85` figures show every objective, correctly colored and
  annotated, with the baseline objective visually distinguished — quickstart.md "regenerate" steps
  (depends on T011, T013)

**Checkpoint**: User Stories 1 AND 2 both work — the raw per-objective data (US1) is now visible as
a comparison view and per-model figure (US2).

---

## Phase 5: User Story 3 - Trust the constraint-violation and correctness picture, not just speed (Priority: P2)

**Goal**: Make the correctness/constraint-violation data trustworthy and impossible to silently
lose, on top of the speed data US1/US2 already surface.

**Independent Test**: Inspect the saved results for any (model, objective, solver) combination and
confirm the constraint-violation residual and other correctness data are present as medians, and
that a failed combination is never silently dropped.

### Implementation for User Story 3

- [X] T016 [US3] In `tests/test_objective_panel.py`, add a test confirming a fixture
  `ObjectivePanelResult` JSON with `both_feasible=False` still produces a row in
  `benchmark_details.csv` (via `aggregate_objective_panel`) rather than being omitted — no
  GPU/Gurobi required (depends on T012)
- [X] T017 [US3] On the host, exercise the failure path directly (e.g. temporarily pass an
  artificially short `--reps`/time budget for one objective via `--force`, or inspect any objective
  that already failed the gate if one exists from T010/T011) and confirm it appears in
  `benchmark_details.csv` marked `both_feasible=False` with its real `status`/
  `residual_inf_median` rather than being silently dropped — quickstart.md "validate the
  correctness gate is enforced" step (depends on T015, T016)

**Checkpoint**: All three user stories are independently functional — this benchmark produces
per-objective data, a visual comparison, and a correctness picture that survives failures without
silently hiding them.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, lint, and the final end-to-end confirmation that nothing was changed
that shouldn't have been.

- [X] T018 [P] Add a "Cross-model objective-panel credibility benchmark" section to
  `benchmarks/README.md` documenting `run_objective_panel.py` / `aggregate_objective_panel.py` /
  `make_objective_panel_figures.py` usage, per plan.md's Project Structure note
- [X] T019 [P] Run `ruff check` on `benchmarks/objective_panel.py`,
  `benchmarks/run_objective_panel.py`, `benchmarks/aggregate_objective_panel.py`,
  `benchmarks/make_objective_panel_figures.py`, `tests/test_objective_panel.py` and fix only
  violations that are new, not violations already present as accepted style throughout this
  project's other `benchmarks/` files (Constitution Quality Standards: `line-length = 100`),
  consistent with feature 010's established precedent for this check
- [X] T020 Run quickstart.md's "no previously-published result changed" and "no shipped default
  changed" `git diff` checks end-to-end and confirm both produce no output (spec
  FR-009/FR-010/SC-003/SC-005; depends on T011, T015, T017)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion — no dependency on US2/US3
- **User Story 2 (Phase 4)**: Depends on Foundational + US1's result-file shape (T007); its own new
  file (`aggregate_objective_panel.py`, T012) only needs T007's schema, not US1's actual host runs,
  so it can be drafted in parallel with T010/T011
- **User Story 3 (Phase 5)**: Builds directly on US2's `aggregate_objective_panel.py` (same file),
  so sequenced after it here, though its Independent Test doesn't require US2's figure-generation
  task specifically
- **Polish (Phase 6)**: Depends on all three user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependency on US2/US3 — raw per-objective results exist whether or not
  the comparison view or correctness-detail verification exist yet
- **User Story 2 (P2)**: Independently testable once US1's result-file shape is fixed (T007);
  CSV/figure generation doesn't require US1's own host-validation tasks to have completed first
- **User Story 3 (P2)**: Independently testable (failed-combination visibility can be verified on
  synthetic data alone via T016) — sequenced last here only because it edits/reuses the same file
  US2 built

### Within Each User Story

- Reaction lookup before the per-objective solve before the CLI that wires them together (US1)
- Two-CSV aggregation before figures before the failure-path verification (US2 → US3)
- Host validation task last in each phase

### Parallel Opportunities

- T005/T006 (test file) can run in parallel with continued work on `objective_panel.py` once
  T002-T004 land
- T012 (`aggregate_objective_panel.py`, new file) can proceed in parallel with T010/T011 (host
  validation of `run_objective_panel.py`) — different files, only needs T007's schema
- T014 (test file) can run in parallel with T015 (host/visual validation) once T012/T013 land
- T018 and T019 (Polish) can run in parallel — different files

---

## Parallel Example: Foundational Phase

```bash
# After T002-T004 (lookup helper + loaders) land, run together:
Task: "Reaction-lookup and loader tests in tests/test_objective_panel.py"  # T005, T006
Task: "Continue User Story 1 implementation in run_objective_panel.py"    # T007+
```

## Parallel Example: User Story 1 / User Story 2 overlap

```bash
# Once T007 (ObjectivePanelResult schema) is fixed, run together:
Task: "Host-validate e_coli_core and background S85 runs"                # T010, T011
Task: "Implement aggregate_objective_panel.py against the fixed schema"  # T012
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: run `--model e_coli_core` (fast) then `--model S85` in the background
   (slow, resumable) — the raw per-objective, median-based credibility data already exists, even
   before any CSV or figure is generated
5. Phases 4-5 turn that raw data into a legible comparison view and a verified-trustworthy
   correctness picture, but the core research answer (is the published number representative?) is
   available per-model as soon as that model's Phase 3 run finishes

### Incremental Delivery

1. Setup + Foundational → reaction lookup and panel/settings loading ready for any model
2. User Story 1 → real per-objective results for whichever models have been run, testable
   end-to-end per model
3. User Story 2 → same data, now visualized alongside every model's already-published baseline
4. User Story 3 → same figures, now with a verified-never-silently-dropped correctness picture
5. Polish → docs, lint, final confirmation that no previously-published result or shipped default
   changed

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Given the realistic multi-day total runtime (research R4), Phase 3's host-validation tasks
  (T010/T011) are expected to run per-model over an extended period, not all at once — later phases
  should not assume every model's results exist yet, only that whichever models have been run
  produce correct output
- No `gpugem/` changes anywhere in this feature — every task touches only `benchmarks/` or `tests/`
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently
