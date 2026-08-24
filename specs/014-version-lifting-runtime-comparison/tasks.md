---

description: "Task list for Version x Lifting Runtime Comparison"

---

# Tasks: Version x Lifting Runtime Comparison

**Input**: Design documents from `/specs/014-version-lifting-runtime-comparison/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all present)

**Tests**: Included — plan.md's Technical Context commits to pytest coverage for the aggregation/
row-building logic and correctness-gate reuse, matching this project's established `benchmarks/`
testing convention (Constitution Principle III does not strictly apply here — no `gpugem/` file is
touched by this feature).

**Organization**: Tasks are grouped by user story (P1/P1/P2 from spec.md) so each can be
implemented and independently tested on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Single project — entirely new `benchmarks/` tooling; no `gpugem/`-internal change (plan.md Project
Structure) — the smallest footprint of any feature building on the cuOpt-tuning/lifting work so
far.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare the output location for this feature's new per-model results, distinct from
every prior feature's `results/` subdirectory.

- [X] T001 Create `benchmarks/results/version_lifting/` directory with a `.gitkeep`

**Checkpoint**: Output location exists; no new dependency required (plan.md confirms
pandas/matplotlib/numpy/scipy/gpugem/cuopt-cu12/gurobipy already satisfy this feature).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The worker, orchestrator, and aggregator are needed, unchanged, by every user story —
US1 needs them to produce the figure's data, US2 needs them to prove the correctness gate is
actually reused (not reimplemented), US3 needs their output to document.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 Create `benchmarks/_version_lifting_worker.py` per contracts/cli-contract.md:
  `--model NAME --lift/--no-lift --time-limit SECONDS`, resolves the model via
  `benchmarks.models.build_lp`, calls `gpugem.solve(**lp, lift=<flag>, time_limit=...)` (no new
  `gpugem` surface — reuses `specs/013-cobra-model-lifting/`'s existing `lift`/`lift_big`
  parameters as-is), computes `residual_inf` via `benchmarks.residual.feasibility_residual`
  against the model's *original* `S`/`b`, and prints one `RuntimeConfiguration`-shaped JSON
  object (data-model.md) to stdout as the last line (cuOpt's native logging bypasses
  `sys.stdout`, same convention as every prior worker in this project) — subprocess entry point,
  never invoked directly
- [X] T003 Create `benchmarks/run_version_lifting_comparison.py` per contracts/cli-contract.md:
  for each requested model (default: all six in-scope models), determine which of the three
  additional configurations are missing per research.md R3's exact accounting (read
  `benchmark.csv` for old-unlifted; check `specs/013-cobra-model-lifting/benchmarks/results/
  model_lifting/<model>.json` for `e_coli_core`/`S85`'s already-existing old-lifted result); for
  each still-missing combination, check for `/tmp/cuopt-26.8-venv` and provision it if absent
  using the exact command already established in `specs/012-cuopt-native-tuning/` (research.md
  R4), then launch `_version_lifting_worker` via `subprocess.run` under `sys.executable` (old
  version) or the venv's interpreter (new version); write
  `benchmarks/results/version_lifting/<model>.json` (data-model.md `VersionLiftingResult`);
  `--force` re-runs an existing combination; skip logic prints `[skip] <model>/<config>` matching
  this project's established resumability convention (depends on T002)
- [X] T004 [P] Create `tests/test_version_lifting_comparison.py` with tests for the
  "which combinations are missing" determination logic (research.md R3) on synthetic/mocked
  presence of `benchmark.csv` rows and `model_lifting/*.json` files — no GPU required: confirms
  exactly 6 old-unlifted + 2 old-lifted (`e_coli_core`, `S85`) are recognized as already existing
  and never re-solved, and that the remaining up-to-16 combinations are correctly identified as
  missing (depends on T003)
- [X] T005 [P] Create `benchmarks/aggregate_version_lifting_comparison.py` per
  contracts/cli-contract.md: read `benchmark.csv` (unmodified — all 10 models' existing Gurobi +
  old-unlifted-cuOpt columns), `benchmarks/results/version_lifting/*.json`, and
  `specs/013-cobra-model-lifting/benchmarks/results/model_lifting/{e_coli_core,S85}.json`; write
  `benchmarks/results/version_lifting_comparison.csv` per data-model.md's `ExtendedComparisonRow`
  (10 rows; the four out-of-scope models' new columns left `NaN`) — reuses
  `benchmarks.residual.objectives_agree`/`feasibility_residual` for any gate recomputation needed
  rather than reimplementing them (research.md R7); standalone, no GPU/solver import required
  (mirrors this project's established "regenerable from committed results alone" convention)
- [X] T006 [P] In `tests/test_version_lifting_comparison.py`, add tests for the CSV row-building
  logic on synthetic `RuntimeConfiguration`/`VersionLiftingResult`-shaped data (no GPU): a model
  with all three new configurations present produces a 5-column-group row; a model with none
  present (the four out-of-scope models) produces `NaN` for all new columns, not zeros or omitted
  rows; a `verified_correct=False` combination (mirroring the already-known S85 case) is present
  in the output, never dropped (depends on T005)

**Checkpoint**: Foundation ready — the worker, orchestrator, and aggregator exist and their
logic is validated on synthetic data; user story implementation can now begin.

---

## Phase 3: User Story 1 - See every combination of cuOpt version and lifting side by side (Priority: P1) 🎯 MVP

**Goal**: The existing runtime figure gains three new bars per model, for exactly the six in-scope
models, reusing already-existing data wherever it exists.

**Independent Test**: For each of the six models, the figure shows cuOpt under all four
{version} x {lifted} combinations alongside the existing Gurobi bar, in one figure; the four
out-of-scope models are unaffected.

### Implementation for User Story 1

- [X] T007 [US1] Create `benchmarks/make_extended_solvetime_figure.py` per contracts/
  cli-contract.md: read `version_lifting_comparison.csv`, plot up to 5 bars per model (Gurobi +
  up to 4 cuOpt configurations) in a fixed, documented color order (never re-cycled per model —
  Constitution Principle VI), gracefully rendering only the original 2 bars for any row whose new
  columns are `NaN` (research.md R6); generalize `make_figure.py`'s existing `both_feasible`
  gate-fail annotation from one hardcoded bar pair to a loop over however many configuration
  columns are present for a row; write to `benchmarks/figures/benchmark_solvetime.png` (same path
  as `make_figure.py`'s own output — research.md R6); `make_figure.py` itself is not modified
  (depends on T005)
- [X] T008 [US1] On the GPU host, run `python -m benchmarks.run_version_lifting_comparison
  --model e_coli_core --model iML1515 --model Harvey --model Harvetta` and confirm: the six
  already-existing old-unlifted combinations are skipped (not re-solved), `e_coli_core`'s
  already-existing old-lifted combination (from `specs/013-.../`) is reused, and the remaining
  new combinations for these four models solve quickly, consistent with research.md R2's
  fast-baseline table (depends on T003)
- [X] T009 [US1] On the GPU host, run `python -m benchmarks.run_version_lifting_comparison
  --model S84` and confirm all three new configurations solve (S84 is the largest of the
  fast-baseline group at ~24.6s old-unlifted — worth confirming individually rather than assuming
  it behaves like the smaller models) (depends on T003)
- [X] T010 [US1] On the GPU host, run `python -m benchmarks.run_version_lifting_comparison
  --model S85` and confirm: the isolated venv is provisioned (if not already present) or reused
  without disturbing the shared environment (verify `cuopt.__version__` outside the venv still
  reports the old version afterward), `S85`'s already-existing old-lifted result (with its known
  `verified_correct=False`) is reused rather than re-solved, and the two new S85 configurations
  (new-unlifted, new-lifted) complete — whatever their outcome, per User Story 2 (depends on T003)
- [X] T011 [US1] On the GPU host, run `python -m benchmarks.aggregate_version_lifting_comparison`
  and `python -m benchmarks.make_extended_solvetime_figure`, then visually confirm the figure
  shows 5 bars for each of the six in-scope models and exactly today's original 2 bars,
  unchanged, for the other four; confirm via `git diff` that `benchmark.csv` and `make_figure.py`
  are untouched (depends on T007, T008, T009, T010)

**Checkpoint**: User Story 1 is fully functional and independently testable — the extended figure
exists and shows every combination for the six in-scope models.

---

## Phase 4: User Story 2 - Never plot a number that hasn't passed the correctness gate (Priority: P1)

**Goal**: Every new bar's correctness outcome is recorded and honestly shown; the already-known
S85 failure is neither hidden nor silently re-passed.

**Independent Test**: The aggregated CSV and the figure both show S85's already-known old-lifted
failure as a visible failure, and any newly-discovered failure (if one occurs) is shown the same
way, never omitted.

### Implementation for User Story 2

- [X] T012 [US2] On the GPU host (or from T011's already-generated CSV), confirm
  `version_lifting_comparison.csv`'s `S85` row has `cuopt_old_lifted_verified_correct == False`
  — the already-known failure from `specs/013-cobra-model-lifting/`, reused and carried through,
  not silently dropped or reinterpreted as a pass (quickstart.md step 3; depends on T011)
- [X] T013 [US2] Visually inspect the regenerated `benchmark_solvetime.png` and confirm S85's
  old-lifted bar carries a gate-fail annotation matching the figure's existing visual convention
  (spec FR-004/User Story 2 Acceptance Scenario 2) — not omitted, not rendered as if it passed
  (depends on T011)
- [X] T014 [P] [US2] In `tests/test_version_lifting_comparison.py`, add a regression test
  confirming the aggregator never silently drops or reinterprets a combination whose
  `verified_correct` is `False` — synthetic input mirroring the S85 case, asserting the resulting
  row is present with `verified_correct == False`, not omitted or overwritten (depends on T005)

**Checkpoint**: User Stories 1 AND 2 both work — the comparison is both complete and honest about
what did and didn't pass correctness.

---

## Phase 5: User Story 3 - Read the answer without opening a results file (Priority: P2)

**Goal**: The comparison is documented in this project's established benchmarks documentation
style, stating plainly which configuration is fastest per model.

**Independent Test**: `benchmarks/README.md` gains a section, in the same style as every other
benchmark section, stating the fastest configuration per model and any correctness caveats.

### Implementation for User Story 3

- [X] T015 [US3] Append a "Version x lifting runtime comparison" section to
  `benchmarks/README.md` documenting the new scripts (usage per quickstart.md), the exact
  reused-vs-newly-solved accounting (research.md R3), and — once T011's real results exist — a
  plain-language summary per model of which configuration is fastest and whether lifting and/or
  the version upgrade changes the answer (spec SC-003/SC-004), explicitly calling out S85's known
  correctness failure rather than only reporting its speed (depends on T011, T012)
- [X] T016 [US3] If any new correctness failure beyond the already-known S85 one is found during
  the host runs (T008-T010), add it to `README.md`'s "Known limitations" section per Constitution
  Principle V — conditional: only makes a change if a new failure is actually found (depends on
  T008, T009, T010)

**Checkpoint**: All three user stories are independently functional — the comparison exists, is
correct and honestly reported, and is documented.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Lint, full regression check, and final end-to-end confirmation.

- [X] T017 [P] Run `ruff check` on `benchmarks/_version_lifting_worker.py`,
  `benchmarks/run_version_lifting_comparison.py`,
  `benchmarks/aggregate_version_lifting_comparison.py`,
  `benchmarks/make_extended_solvetime_figure.py`, `tests/test_version_lifting_comparison.py` and
  fix any violations (Constitution Quality Standards: `line-length = 100`), matching the
  established project style
- [X] T018 [P] Run the full repo-wide test suite (`pytest tests/`) and confirm no regressions —
  in particular that `tests/test_scaling.py`, `tests/test_lifting.py`, and every prior feature's
  tests still pass unchanged, since this feature touches no `gpugem/` file
- [X] T019 Run quickstart.md end-to-end (steps 1-4) on the GPU host, confirm via `git diff` that
  `benchmark.csv`, `make_figure.py`, `gpugem/scaling.py`, and `gpugem/lifting.py` are all
  untouched (research.md R6, plan.md Constraints), and record the final answer to spec
  SC-003/SC-004 in `benchmarks/README.md` (depends on T011, T015, T017, T018)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion — no dependency on US2/US3
- **User Story 2 (Phase 4)**: Depends on Foundational + US1's actual host runs (T011) having
  produced the CSV/figure to inspect — genuinely sequenced after US1, not just file-shared
- **User Story 3 (Phase 5)**: Depends on Foundational + US1's results (T011) to document; T016
  additionally depends on US1's host-run tasks (T008-T010) to know whether a new failure exists
- **Polish (Phase 6)**: Depends on all three user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependency on US2/US3 — the figure exists and shows all combinations
  regardless of whether their correctness has been separately spot-checked or documented yet
- **User Story 2 (P1)**: Genuinely depends on US1's host runs existing to inspect — equal spec
  priority to US1, but implementation-sequenced after it (same pattern as
  `specs/013-cobra-model-lifting/`'s US1/US2 relationship)
- **User Story 3 (P2)**: Depends on US1's real results to write real numbers into the
  documentation, not placeholder ones

### Within Each User Story

- Worker before orchestrator (Foundational)
- Orchestrator's output before the aggregator can produce anything real (Foundational -> US1)
- Aggregator before the figure script (US1)
- Cheap models' host runs before the expensive S85 one, so any issue in the worker/orchestrator
  surfaces on a fast iteration first (US1's own task ordering, T008 before T009 before T010)

### Parallel Opportunities

- T004 and T006 (different test functions, same file) can be drafted in parallel once T003/T005
  land respectively
- T008 (four fast models) can run in parallel with T009 (S84) — different model sets, same
  orchestrator, no shared state
- T017 and T018 (Polish, different concerns) can run in parallel

---

## Parallel Example: Foundational Phase

```bash
# Once T003 lands:
Task: "Missing-combination determination tests"                # T004

# Once T005 lands:
Task: "CSV row-building tests"                                  # T006
```

## Parallel Example: User Story 1 host runs

```bash
# Independent model sets, same orchestrator:
Task: "Run e_coli_core/iML1515/Harvey/Harvetta"                 # T008
Task: "Run S84"                                                  # T009
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: the extended figure exists and shows all four cuOpt configurations for
   the six in-scope models — this alone already answers the motivating question (does lifting
   and/or the version upgrade change cuOpt's runtime), before any dedicated correctness spot-check
   or documentation pass
5. Phases 4-5 turn that into a verified-honest, documented result

### Incremental Delivery

1. Setup + Foundational → worker/orchestrator/aggregator ready, validated on synthetic data
2. User Story 1 → the extended figure exists, testable end-to-end on the GPU host
3. User Story 2 → confirmed honest about the already-known S85 failure (and any new one)
4. User Story 3 → documented in the project's established style
5. Polish → lint, full regression check, final confirmation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- This feature touches no `gpugem/` file at all — the smallest footprint of any feature built on
  the cuOpt-tuning/lifting investigation
- `benchmark.csv`, `make_figure.py`, `gpugem/scaling.py`, and `gpugem/lifting.py` are explicitly
  out of scope for modification — do not "helpfully" edit them in place while implementing this
  feature (research.md R6)
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently
