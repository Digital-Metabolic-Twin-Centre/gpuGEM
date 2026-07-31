---

description: "Task list for Violation Distribution Figures for per_constraint_residual=0"

---

# Tasks: Violation Distribution Figures for per_constraint_residual=0

**Input**: Design documents from `/specs/007-violation-distribution-figures/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all present)

**Tests**: Included — plan.md's Technical Context commits to pytest coverage for the new signed
per-row violation and histogram-binning functions (pure, synthetic-input, no GPU), matching
`tests/test_residual_tradeoff.py`'s existing precedent.

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

## Phase 1: Setup

**Purpose**: Confirm the prerequisite state this feature builds on before touching any code.

- [X] T001 Confirm `benchmarks/results/S9.json`, `S15.json`, `S23.json`, `S83.json` (feature 006)
  and `benchmarks/results/residual_tradeoff/{e_coli_core,Harvey,iML1515,S84,S85}.json` (feature 005)
  are all present and committed — `_load_002_result`/backfill logic (US1) has nothing to build on
  otherwise

**Checkpoint**: All nine models have the upstream data this feature reads; no new directories
needed (`results/residual_tradeoff/` and `figures/` already exist from feature 005).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The signed per-row violation computation and histogram binning are shared by both the
solve step (US1 writes histogram data) and both figures (US2/US3 read it) — a single module so the
bin edges used at solve time and at render time can never silently drift apart (research R5).

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 Create `benchmarks/violation_histogram.py` with a module-level constant
  `MAGNITUDE_BIN_EDGES = numpy.logspace(-9, 3, 25)` (24 log-scale bins, 1e-9 to 1e3 — research R5)
- [X] T003 In `benchmarks/violation_histogram.py`, implement `signed_row_violations(A, row_lb,
  row_ub, v)`: returns `-numpy.maximum(row_lb - A@v, 0.0) + numpy.maximum(A@v - row_ub, 0.0)` — the
  full signed vector (negative = shortfall, positive = excess, zero = satisfied), reusing
  `gpugem/solver.py`'s own `con_lb`/`con_ub` range-violation definition (research R3); pure
  function, no I/O (depends on T002)
- [X] T004 In `benchmarks/violation_histogram.py`, implement `histogram(violations, edges=
  MAGNITUDE_BIN_EDGES)`: splits `violations` into shortfall (`< 0`) and excess (`> 0`) magnitudes,
  bins each with `numpy.histogram(numpy.abs(...), bins=edges)`, and returns a `ViolationHistogram`
  dict per data-model.md (`bin_edges`, `shortfall_counts`, `excess_counts`, `n_rows`,
  `n_satisfied`) with the invariant `n_satisfied + sum(shortfall_counts) + sum(excess_counts) ==
  n_rows` (depends on T002, T003)
- [X] T005 [P] Create `tests/test_violation_histogram.py` with tests for `signed_row_violations`
  (equality rows via `row_lb==row_ub`, true ranges, satisfied/shortfall/excess cases on synthetic
  input) and `histogram` (a model with zero violations still returns a valid, fully-`n_satisfied`
  histogram — not an error; the invariant holds; magnitude exactly at a bin edge is handled) — no
  GPU required (depends on T002, T003, T004)

**Checkpoint**: Foundation ready — any per-row violation vector can be turned into the shared,
comparable histogram shape both the solve step and the figures depend on.

---

## Phase 3: User Story 1 - See the per_constraint_residual=0 runtime for every benchmarked model, not just the original five (Priority: P1) 🎯 MVP

**Goal**: Every model currently in the benchmark suite (all nine) has a `per_constraint_residual=0`
result, including full per-row violation histograms for both the S-block and (where present)
C-block, and the existing three-configuration runtime comparison covers all nine.

**Independent Test**: Confirm every model in the suite has a recorded `per_constraint_residual=0`
result with both histogram fields, and that the runtime comparison figure includes all nine, not
only the original five.

### Implementation for User Story 1

- [X] T006 [US1] In `benchmarks/run_residual_tradeoff.py::_solve_residual_0`, after solving: slice
  the S-block (`lp["S"]`, `lp["b"]` as `row_lb==row_ub==b`) and, when `lp.get("C") is not None`,
  the C-block (`lp["C"]`, `lp["d_lb"]`, `lp["d_ub"]`) and call
  `violation_histogram.signed_row_violations` + `violation_histogram.histogram` on each using
  `res.fluxes`; add `violation_histogram_equations` (always) and `violation_histogram_constraints`
  (`None` when no C-block) to the returned dict per `contracts/result-json-extension.md` (depends
  on T002, T003, T004)
- [X] T007 [US1] In `benchmarks/run_residual_tradeoff.py::run_model`, change the skip condition:
  when `results/residual_tradeoff/<model>.json` exists but lacks
  `residual_0.violation_histogram_equations` (an old-format file from before this feature), print
  `[backfill] <model>` and re-solve rather than `[skip]`ping — per research R4, this is a
  deliberate, visible one-time schema upgrade, not a silent overwrite of the original five's
  already-trusted numbers; `--force` still forces an unconditional re-solve for any model (depends
  on T006)
- [X] T008 [US1] In `benchmarks/make_residual_tradeoff_figures.py`, apply the same figure-width fix
  feature 006 applied to `make_figure.py` (`figsize=(max(8.2, 1.5 * len(df)), 4.6)` or equivalent
  in `_bar_figure()`) so nine models' bar labels don't overlap (research R7)
- [X] T009 [US1] On the GPU host, run `python -m benchmarks.run_residual_tradeoff --all` and
  confirm: `[backfill]` for `e_coli_core`/`Harvey`/`iML1515`/`S84`/`S85`, a fresh solve for
  `S9`/`S15`/`S23`/`S83`, and `results/residual_tradeoff/comparison.csv` ends with 27 rows (9
  models x 3 configurations) — quickstart.md step 1 (depends on T007, T008)
- [X] T010 [US1] Run `python -m benchmarks.make_residual_tradeoff_figures` and visually confirm
  `residual_tradeoff_solvetime.png` / `residual_tradeoff_violations.png` show all nine models with
  legible, non-overlapping labels — quickstart.md step 2, partial (depends on T009)

**Checkpoint**: User Story 1 is fully functional and independently testable — every model has a
complete, histogram-bearing `per_constraint_residual=0` result, and the existing runtime comparison
covers all nine.

---

## Phase 4: User Story 2 - See how many mass-balance equations are violated, and by how much, per model (Priority: P2)

**Goal**: A single population-pyramid-style figure overlaying every model's mass-balance-equation
violation distribution.

**Independent Test**: Generate the figure from committed results and confirm it shows, for every
model, the count of violated mass-balance equations at each magnitude, with shortfall and excess
visually mirrored and each model individually identifiable.

### Implementation for User Story 2

- [X] T011 [US2] Create `benchmarks/make_violation_distribution_figures.py` with a shared rendering
  helper (e.g. `_pyramid_figure(entries, out_path, title)` where `entries` is a list of `(model,
  n_cols, ViolationHistogram)`) implementing the layout in `contracts/figure-contract.md`: log-scale
  magnitude y-axis, mirrored shortfall(left)/excess(right) count x-axis, one semi-transparent
  (`alpha≈0.4`) stepped fill per model from `matplotlib`'s `Purples` colormap sampled by
  model-size rank (skipping the lightest ~30% of the ramp per research R6), direct per-model text
  label plus a size-ordered backup legend, embedded non-recommendation caption, 300 dpi,
  `bbox_inches="tight"` (depends on T004 for the `ViolationHistogram` shape)
- [X] T012 [US2] In `benchmarks/make_violation_distribution_figures.py`, add the equations entry
  point: read every `results/residual_tradeoff/<model>.json`, extract
  `residual_0.violation_histogram_equations` for every model (always present), call
  `_pyramid_figure` to write `benchmarks/figures/violation_distribution_equations.png` (depends on
  T011)
- [X] T013 [P] [US2] In `tests/test_violation_histogram.py`, add a test for the figure data-prep
  step: a model whose histogram is all-`n_satisfied` (zero violations) still produces a valid,
  plottable (near-empty, not omitted) entry — no GPU required (depends on T004)
- [X] T014 [US2] Run `python -m benchmarks.make_violation_distribution_figures` and visually
  confirm `violation_distribution_equations.png` shows all nine models' distributions overlaid,
  each individually visible (not one opaque region hiding another) and labeled by model name —
  quickstart.md step 2 / validation item 2 (depends on T012)

**Checkpoint**: User Stories 1 AND 2 both work — every model's equation-violation distribution is
visible in one comparable figure.

---

## Phase 5: User Story 3 - See the same picture for coupling constraints (Priority: P3)

**Goal**: The equivalent figure for coupling constraints, limited to models that have them.

**Independent Test**: Generate the second figure and confirm it shows the violated-coupling-
constraint distribution for every model with a C-block, in the same visual style, with models
lacking a C-block simply absent (not shown as empty).

### Implementation for User Story 3

- [X] T015 [US3] In `benchmarks/make_violation_distribution_figures.py`, add the constraints entry
  point: read every `results/residual_tradeoff/<model>.json`, filter to models where
  `residual_0.violation_histogram_constraints is not None`, call the same `_pyramid_figure` helper
  (T011) to write `benchmarks/figures/violation_distribution_constraints.png`; wire both entry
  points into `main()` (depends on T011, T012)
- [X] T016 [US3] Run `python -m benchmarks.make_violation_distribution_figures` and visually
  confirm `violation_distribution_constraints.png` shows exactly the seven models with a coupling
  block, with `e_coli_core`/`iML1515` absent (not shown as empty entries) — quickstart.md step 2 /
  validation item 3 (depends on T015)

**Checkpoint**: All three user stories are independently functional — full runtime coverage, the
equation-violation figure, and the coupling-constraint figure all exist and are individually
verifiable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, lint, and the final end-to-end confirmation that no shipped default
changed.

- [X] T017 [P] Add a section to `benchmarks/README.md` documenting
  `make_violation_distribution_figures.py`, the nine-model `per_constraint_residual=0` coverage,
  and the `[backfill]` behavior in `run_residual_tradeoff.py`, per plan.md's Project Structure note
- [X] T018 [P] Run `ruff check` on `benchmarks/violation_histogram.py`,
  `benchmarks/run_residual_tradeoff.py`, `benchmarks/make_residual_tradeoff_figures.py`,
  `benchmarks/make_violation_distribution_figures.py`, `tests/test_violation_histogram.py` and fix
  any real violations (Constitution Quality Standards: `line-length = 100`), matching this
  project's established convention of following existing `benchmarks/` style rather than diverging
- [X] T019 Run quickstart.md end-to-end (validation items 1-5) on the GPU host, and confirm `git
  diff --stat gpugem/` produces no output — the project's shipped defaults are unchanged regardless
  of what the comparison shows (spec SC-005; depends on T009, T014, T016)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion — no dependency on US2/US3
- **User Story 2 (Phase 4)**: Depends on Foundational + US1's result-file shape (T006/T007 must
  land so real histogram data exists to render); the figure script itself (T011) only needs T004's
  schema and can be written in parallel with US1's GPU validation tasks (T009/T010)
- **User Story 3 (Phase 5)**: Extends the same file US2 built (T011/T012), so sequenced after it
  here, though its Independent Test doesn't require US2's own validation task (T014) to have run
  first
- **Polish (Phase 6)**: Depends on all three user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependency on US2/US3 — full nine-model coverage and histogram data
  exist whether or not either figure has been built yet
- **User Story 2 (P2)**: Needs US1's real data to render against, but its own code (T011) is
  independent of US1's GPU runs
- **User Story 3 (P3)**: Independently testable (absence-of-BiGG-models can be verified on its
  own), sequenced last here only because it shares `make_violation_distribution_figures.py` with US2

### Within Each User Story

- Histogram capture (`_solve_residual_0`, T006) before the backfill-aware skip logic (T007) before
  the figure-width fix (T008) before GPU validation (T009/T010) — US1
- Shared rendering helper (T011) before the equations entry point (T012) before its own visual
  validation (T014) — US2
- Constraints entry point (T015) reuses T011/T012's helper, then its own visual validation (T016) —
  US3

### Parallel Opportunities

- T005 (test file) can run in parallel with continued work on `violation_histogram.py` once
  T002/T003/T004 land
- T011 (`make_violation_distribution_figures.py` skeleton) can be written in parallel with T009/T010
  (GPU validation of `run_residual_tradeoff.py`) — different files, only needs T004's schema
- T013 (test) can run in parallel with T014 (visual validation) once T012 lands
- T017 and T018 (Polish) can run in parallel — different files

---

## Parallel Example: Foundational Phase

```bash
# After T002/T003/T004 (bin edges + signed violation + histogram) land, run together:
Task: "Pure-function tests in tests/test_violation_histogram.py"           # T005
Task: "Begin User Story 1 implementation in run_residual_tradeoff.py"      # T006+
```

## Parallel Example: User Story 1 / User Story 2 overlap

```bash
# Once T004 (ViolationHistogram schema) is fixed, run together:
Task: "GPU-validate the --all backfill + 4 fresh solves"        # T009, T010
Task: "Build make_violation_distribution_figures.py against the fixed schema"  # T011, T012
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: run `--all` on the GPU host, inspect a couple of the nine
   `results/residual_tradeoff/<model>.json` files by hand — full nine-model coverage and per-row
   histogram data already exist, even before either new figure is generated
5. Phases 4-5 turn that histogram data into the two comparable population-pyramid figures, but the
   core new data (per-row violation distributions for every model) is available after Phase 3 alone

### Incremental Delivery

1. Setup + Foundational → shared signed-violation/histogram machinery ready
2. User Story 1 → nine-model `per_constraint_residual=0` coverage with full histogram data,
   testable end-to-end
3. User Story 2 → equation-violation distributions visualized in one regenerable figure
4. User Story 3 → coupling-constraint distributions visualized in a second, comparably-structured
   figure
5. Polish → docs, lint, final confirmation that no shipped default changed

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- US2 and US3 share one file (`make_violation_distribution_figures.py`) by design (plan.md's
  Structure Decision) — the mirrored-histogram rendering logic is identical between the two, only
  which histogram field and which model subset differs
- No `gpugem/` changes anywhere in this feature — every task touches only `benchmarks/` or `tests/`
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently
