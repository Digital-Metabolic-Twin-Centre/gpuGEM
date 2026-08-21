---

description: "Task list for cuOpt-Native Settings Tuning for Large Microbiome Models"

---

# Tasks: cuOpt-Native Settings Tuning for Large Microbiome Models

**Input**: Design documents from `/specs/012-cuopt-native-tuning/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all present)

**Tests**: Included — plan.md's Technical Context commits to pytest coverage for the candidate
registry (well-formed `cuopt_kwargs`, correct warm-start pairing) and the ranking/speedup math
(GPU/Gurobi-free), and quickstart.md step 2 runs them explicitly.

**Organization**: Tasks are grouped by user story (P1/P2/P3 from spec.md) so each can be
implemented and independently tested on its own.

**Reminder carried through every story**: the project's actual preferred goal (recorded in the
user's own words while generating this task list) is a setup that **outperforms Gurobi** on
whole-body/microbiome models — not merely one that improves on cuOpt's own prior baseline. Every
result-producing task below reports `speedup_vs_gurobi` as a first-class number, not just
`speedup_vs_baseline` (data-model.md, amended during this task-generation pass).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Single project — extends the existing `benchmarks/` package only; no `gpugem/`-internal change
this time (plan.md Project Structure).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare the output location for this feature's results, distinct from `002`'s
`results/S85.json`, `004`'s `results/s85_solver_modes/`, and `005`'s `results/residual_tradeoff/`.

- [X] T001 Create `benchmarks/results/cuopt_tuning/` directory with a `.gitkeep`

**Checkpoint**: Output location exists; no new dependency required (plan.md confirms
cuopt-cu12/gurobipy/scipy/numpy already satisfy this feature).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The candidate registry is needed by all three user stories — this MUST exist,
correctly grounded in research.md's verified parameter/enum semantics (R2-R4), before any user
story phase starts.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 In `benchmarks/cuopt_tuning_candidates.py`, create the `CANDIDATES` list per
  data-model.md's `TuningCandidate` schema. Each entry needs `id`, `user_story`, `cuopt_kwargs`,
  `warm_start` (default `False`), `source_note`, `requires_isolated_venv` (default `False`).
  Populate the **US1 settings-sweep entries**, each `cuopt_kwargs` value taken directly from
  research.md's verified enum tables (never guessed):
  - `baseline`: `{}` (large-model default, unchanged) — `source_note="R1 cross-check"`
  - `pdlp_mode_fast1`: `{"pdlp_solver_mode": 3}` (`Fast1`) — `source_note="R2: never tried in 004"`
  - `pdlp_precision_mixed`: `{"pdlp_precision": 2}` (true Mixed) — `source_note="R3: never actually tried under either name"`
  - `pdlp_precision_single`: `{"pdlp_precision": 0}` (Single/FP32) — `source_note="R3: completeness, expected to hit the FP32 wall"`
  - `pdlp_precision_double_explicit`: `{"pdlp_precision": 1}` — `source_note="R3: confirm -1 Default == Double on S85 scale too, not just e_coli_core"`
  - `presolve_pslp_retest`: `{"presolve": 2}` (PSLP) — `source_note="R4: does the 26.04 PSLP false-infeasible fix hold on S85"`
  - `first_primal_feasible`: `{"first_primal_feasible": True}` — `source_note="R2: new, untested axis"`
  - `infeasibility_detection_strict`: `{"infeasibility_detection": True, "strict_infeasibility": True}` — `source_note="R2: new, untested axis"`
  - `save_best_primal`: `{"save_best_primal_so_far": True}` — `source_note="R2: new, untested axis"`
  - `warm_start_stable2`: `{"presolve": 0, "pdlp_solver_mode": 1}`, `warm_start=True` — `source_note="R4: presolve=0 is OFF (distinct from PSLP=2); Stable2 is one of the two modes set_pdlp_warm_start_data's own docstring supports"`
  - `warm_start_fast1`: `{"presolve": 0, "pdlp_solver_mode": 3}`, `warm_start=True` — `source_note="R4: Fast1 is the other supported warm-start mode"`
  Do **not** add a plain `method=Concurrent` candidate — `specs/004-s85-solver-mode-experiment/`
  already published this exact result (PDLP won, ~513s, a tie); re-running it would contradict
  spec FR-001's "going beyond the specific settings already tried."
- [X] T003 In the same file, add a `LINKED_RESULTS` list (not fresh-solved candidates) with one
  entry: `per_constraint_residual_0`, pointing at
  `benchmarks/results/residual_tradeoff/S85.json`'s already-published `per_constraint_residual=0`
  timing (research.md R2) — so the final comparison (T3xx below) can include it for completeness
  without re-spending GPU time on a result `specs/005-residual-tradeoff-benchmark/` already
  produced (depends on T002)
- [X] T004 [P] Create `tests/test_cuopt_tuning.py` with registry-validation tests (no GPU/Gurobi
  required): every `CANDIDATES` entry's `cuopt_kwargs` keys resolve against cuOpt's live
  `get_solver_parameter_names()`, `id` values are unique, exactly one entry has `id="baseline"`,
  and every `warm_start=True` entry sets `presolve=0` (the only value that permits warm start per
  research.md R4) (depends on T002)

**Checkpoint**: Foundation ready — the candidate registry exists, is grounded in verified research
findings (not guesses), and is validated; user story implementation can now begin.

---

## Phase 3: User Story 1 - Systematic cuOpt-native settings sweep on S85 (Priority: P1) 🎯 MVP

**Goal**: Solve S85 with cuOpt under the baseline settings and under every settings-sweep
candidate from T002, recording wall time, iteration count, solver status, and correctness for
each — including the warm-start candidates' cold+warm phase pair.

**Independent Test**: Run the sweep against S85 and confirm every candidate in `CANDIDATES` with
`user_story="US1"` produces a recorded `CandidateResult` (data-model.md), including the baseline.

### Implementation for User Story 1

- [X] T005 [US1] Create `benchmarks/_cuopt_tuning_worker.py`: given a `candidate_id` CLI argument,
  look it up in `CANDIDATES` (T002), build S85's LP via `benchmarks.models.build_lp("S85")`. If
  `warm_start=False`: call `gpugem.solve(..., time_limit=<passed in>, **candidate.cuopt_kwargs)`
  once (`phase="single"`). If `warm_start=True`: first solve cold with `presolve=0,
  pdlp_solver_mode=<candidate's mode>` (`phase="cold"`), retrieve
  `sol.get_pdlp_warm_start_data()` from the underlying cuOpt solution object, then solve again
  passing that data via `set_pdlp_warm_start_data` on a fresh `SolverSettings` with the same
  kwargs (`phase="warm"`). Compute `residual_inf` via `benchmarks.residual.feasibility_residual`
  for each phase, print one `CandidateResult`-shaped JSON object to stdout per data-model.md
  (`phases` list, `status`/`solve_s`/`iterations`/`objective` taken from the last/claimed phase)
  — subprocess entry point, never invoked directly by a user (research R6; `contracts/cli-contract.md`)
- [X] T006 [US1] Create `benchmarks/run_cuopt_tuning.py` orchestrator with `--baseline`,
  `--settings`, `--force`, `--time-limit` (default 900.0) flags per `contracts/cli-contract.md`.
  Read S85's Gurobi ground truth from the already-published `benchmarks/results/S85.json` (never
  re-solved — spec FR-003/FR-006). For each `US1` candidate in `CANDIDATES` order: skip if
  `results/cuopt_tuning/<id>.json` exists and `--force` wasn't given (print `[skip] <id>`),
  otherwise launch `python -m benchmarks._cuopt_tuning_worker <id>` via `subprocess.run(timeout=
  time_limit + 60, capture_output=True, text=True, check=False)` (research R6), classify the
  outcome (`verified_correct` via `benchmarks.residual`'s existing gate against the Gurobi
  reference — status Optimal + residual within tolerance + objective agreement; timeout/crash
  recorded with `error` set, never silently dropped per spec FR-005/FR-010), and write
  `results/cuopt_tuning/<id>.json` per data-model.md's `CandidateResult` schema (depends on T005)
- [X] T007 [US1] On the GPU host, run `python -m benchmarks.run_cuopt_tuning --baseline` alone and
  confirm `results/cuopt_tuning/baseline.json`'s `solve_s` is consistent with the already-published
  `results/S85.json` cuOpt figure (~505-520s) — reproduce the trusted number before trusting the
  new subprocess-based worker for untested candidates (quickstart.md step 3; depends on T006)
- [X] T008 [US1] On the GPU host, run `python -m benchmarks.run_cuopt_tuning --settings` and
  confirm every US1 candidate (10 settings candidates + baseline = 11) produces a recorded
  `CandidateResult`, none silently missing from `results/cuopt_tuning/` — including both
  warm-start candidates' cold+warm phase pairs (depends on T006, T007)

**Checkpoint**: User Story 1 is fully functional and independently testable — raw per-candidate
results exist for the baseline and every settings-sweep candidate, which alone already answers
"does any purely cuOpt-native setting help" (spec SC-001).

---

## Phase 4: User Story 2 - Check whether a newer cuOpt release changes the picture (Priority: P2)

**Goal**: Determine whether `cuopt-cu12==26.8.0`, tested in an isolated venv that never touches
the shared environment, changes S85's solve time, correctness, or the warm-start behavior — for
the baseline and the best-performing US1 candidate(s).

**Independent Test**: Provision the isolated venv, re-run the baseline and best US1 candidate(s)
under it, and confirm results are recorded the same way as US1, without altering the shared
environment's `cuopt-cu12` version.

### Implementation for User Story 2

- [X] T009 [US2] In `benchmarks/cuopt_tuning_candidates.py`, add a `select_upgrade_candidates()`
  helper that reads the US1 results already on disk (T008) and returns `["baseline"] +
  [the id of the single fastest verified_correct US1 candidate, if any]` — the concrete,
  data-driven list User Story 2 re-runs, not a hardcoded guess (depends on T008)
- [X] T010 [US2] In `benchmarks/run_cuopt_tuning.py`, add `--upgrade-venv PATH` handling per
  `contracts/cli-contract.md`: validate `PATH` exists (non-zero exit with a clear message if not,
  per the CLI contract's exit-code rule), call `select_upgrade_candidates()` (T009), and for each
  selected id launch `subprocess.run([f"{PATH}/bin/python", "-m",
  "benchmarks._cuopt_tuning_worker", id, ...])` instead of `sys.executable` — write results to
  `results/cuopt_tuning/<id>_26.8.0.json` (never overwriting the `26.6.0` result), with
  `cuopt_version` correctly recorded on the `CandidateResult` (research R1/R9; depends on T006, T009)
- [X] T011 [US2] On the GPU host, provision the isolated venv per quickstart.md step 5
  (`python3 -m venv /tmp/cuopt-26.8-venv && /tmp/cuopt-26.8-venv/bin/pip install
  cuopt-cu12==26.8.0 numpy scipy`), run `python -m benchmarks.run_cuopt_tuning --upgrade-venv
  /tmp/cuopt-26.8-venv`, and confirm: (a) `results/cuopt_tuning/baseline_26.8.0.json` and the best
  candidate's `_26.8.0.json` both exist; (b) `python -c "import cuopt; print(cuopt.__version__)"`
  run **outside** the venv still reports `26.6.0` afterward, proving the shared environment was
  untouched (depends on T010)

**Checkpoint**: User Stories 1 AND 2 both work — it's now known whether the newer release changes
anything, without any already-published benchmark result put at risk.

---

## Phase 5: User Story 3 - Non-simplifying preprocessing as a last resort (Priority: P3)

**Goal**: Only if US1 and US2 produce no verified-correct candidate that beats the baseline,
evaluate one preprocessing transform whose result is provably reconstructible to the original
model before its speed is even considered.

**Independent Test**: Apply the transform to S85, solve with cuOpt, reconstruct the result to the
original variable space, and confirm the reconstructed result passes the same correctness gate as
every other candidate before any speed claim is made.

### Implementation for User Story 3

- [X] T012 [US3] In `benchmarks/cuopt_tuning_candidates.py`, add one `PreprocessingCandidate`
  entry (data-model.md) implementing row/column equilibration scaling on S85's `(S, b, lb, ub, c)`
  tuned to its known `[1e-6, 2e5]` range (research.md R5/R8), with an exact, recorded inverse
  transform for the solution — `source_note="R8: last-resort fallback, external scaling given
  cuOpt's own internal Ruiz equilibration already covers most of this"` (depends on T002)
- [X] T013 [US3] In `benchmarks/_cuopt_tuning_worker.py`, add a `--preprocessing <id>` mode: apply
  the transform (T012), solve the transformed LP, apply the inverse, and run the **same**
  correctness gate (`benchmarks.residual`) against the reconstructed result — set
  `reconstruction_verified` accordingly. If `reconstruction_verified=False`, the result JSON MUST
  still record `solve_s` (for transparency) but the orchestrator (T014) MUST NOT treat it as a
  viable candidate in the ranked comparison, per spec FR-008/SC-003 (depends on T012)
- [X] T014 [US3] In `benchmarks/run_cuopt_tuning.py`, add `--preprocessing` handling that invokes
  T013's worker mode and records the result under `results/cuopt_tuning/<id>.json` with
  `user_story="US3"` — only prints a "this preprocessing candidate is viable" line if
  `reconstruction_verified=True` (spec User Story 3 Acceptance Scenario 2: a failed reconstruction
  is disqualified outright, never reported as viable regardless of speed) (depends on T006, T013)
- [X] T015 [US3] On the GPU host, run `python -m benchmarks.run_cuopt_tuning --preprocessing` and
  manually confirm the console output and `results/cuopt_tuning/<preprocessing_id>.json` clearly
  distinguish this as the fallback path it is (spec User Story 3 Acceptance Scenario 3), whether
  or not `reconstruction_verified` ends up `True` (depends on T014)

**Checkpoint**: All three user stories are independently functional — the investigation has
exhausted the settings sweep, the version-upgrade check, and (if needed) one honestly-gated
preprocessing fallback.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: The single ranked comparison (spec FR-010/SC-004), documentation, lint, and the final
end-to-end run that answers the motivating question — including the project's real preferred goal
of beating Gurobi outright, not just cuOpt's own prior baseline.

- [X] T016 [P] Create `benchmarks/aggregate_cuopt_tuning.py`: read every `results/cuopt_tuning/
  *.json` (all three user stories) plus `LINKED_RESULTS` (T003), compute `speedup_vs_baseline`
  and **`speedup_vs_gurobi`** (reading S85's already-published Gurobi wall time from
  `results/S85.json`) for each, and write `results/cuopt_tuning/summary.json` + `summary.csv` per
  data-model.md's `TuningComparison` and `contracts/csv-columns.md` — sorted `verified_correct`
  first, then by `speedup_vs_gurobi` descending (not `speedup_vs_baseline` — the ranking itself
  must reflect the real goal). Print two headline lines: the best verified-correct candidate vs.
  baseline (or "none beat the baseline"), and **separately**, whether any verified-correct
  candidate has `speedup_vs_gurobi > 1` ("N candidate(s) beat Gurobi" / "no candidate beat Gurobi;
  closest was Nx slower") — runnable standalone with no solver import (depends on T006 for the
  result-file shape)
- [X] T017 [US2] In `benchmarks/run_cuopt_tuning.py`, call `aggregate_cuopt_tuning`'s summary
  regeneration at the end of every run mode (`--baseline`, `--settings`, `--upgrade-venv`,
  `--preprocessing`, `--all`), per `contracts/cli-contract.md` (depends on T006, T016)
- [X] T018 [P] In `tests/test_cuopt_tuning.py`, add ranking-math unit tests on synthetic
  `CandidateResult`-shaped data: `speedup_vs_baseline` and `speedup_vs_gurobi` computed correctly,
  best-candidate selection picks correctly, a candidate with `verified_correct=False` never wins
  regardless of `solve_s`, and the "no candidate beats Gurobi" case is reported explicitly rather
  than omitted (depends on T016)
- [X] T019 [P] Add a "cuOpt-native settings tuning (S85)" section to `benchmarks/README.md`
  documenting `run_cuopt_tuning.py`/`aggregate_cuopt_tuning.py` usage, the three user stories, and
  — regardless of outcome — the `pdlp_precision` documentation correction from research.md R3
  (`gpugem/_defaults.py`'s comment mislabels `pdlp_precision=1` as "mixed" when it is actually
  "double"; the shipped numeric default and its validated result are unaffected, this is a
  comment-accuracy fix flagged here for visibility, not bundled into this feature's own code
  changes)
- [X] T020 [P] Run `ruff check` on `benchmarks/cuopt_tuning_candidates.py`,
  `benchmarks/_cuopt_tuning_worker.py`, `benchmarks/run_cuopt_tuning.py`,
  `benchmarks/aggregate_cuopt_tuning.py`, `tests/test_cuopt_tuning.py` and fix any violations
  (Constitution Quality Standards: `line-length = 100`), matching the established `benchmarks/`
  style
- [X] T021 Run quickstart.md end-to-end (steps 1-8) on the GPU host and record, in
  `results/cuopt_tuning/summary.json`, the final answer to spec SC-001/SC-002/SC-004 **and** the
  project's real preferred-goal question: did any verified-correct candidate (across all three
  user stories, any cuOpt version) actually beat Gurobi on S85? State the answer plainly either
  way (matching `004`'s honest-null-result precedent) — this is the headline finding, not a
  secondary detail. If any candidate surfaces a new solver limitation, add it to `README.md`'s
  "Known limitations" section per Constitution Principle V (depends on T008, T011, T015, T017)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion — no dependency on US2/US3
- **User Story 2 (Phase 4)**: Depends on Foundational + US1's results existing (T008; T009 reads
  them to pick which candidates to re-run) — genuinely sequenced after US1, not just file-shared
- **User Story 3 (Phase 5)**: Depends on Foundational; its Independent Test doesn't strictly need
  US1/US2 to have finished, but per the spec it is only *meaningful* to run after US1/US2 show no
  win — sequenced last among the three stories
- **Polish (Phase 6)**: Depends on all three user stories being complete for T021's final report;
  T016/T018/T019/T020 can start once T006 lands (don't need US2/US3's actual GPU runs)

### User Story Dependencies

- **User Story 1 (P1)**: No dependency on US2/US3 — raw results exist regardless of whether the
  upgrade check or preprocessing fallback ever run
- **User Story 2 (P2)**: Genuinely depends on US1's results (picks which candidates to re-test) —
  the one story in this feature that isn't fully independent of another, by the spec's own design
- **User Story 3 (P3)**: Independently testable (the transform/inverse/gate logic doesn't need
  US1/US2 to exist to be correct), but its *purpose* — being a last resort — only makes sense
  chronologically after US1/US2

### Within Each User Story

- Worker (subprocess entry point) before orchestrator (US1)
- Orchestrator's result-file shape fixed before the aggregator consumes it (US1 → Polish)
- Manual/quickstart GPU validation task last in each phase

### Parallel Opportunities

- T004 (test file) can run in parallel with nothing yet — needs T002 first, but is otherwise
  isolated from T003
- T016, T018, T019, T020 (Polish, different files) can all proceed in parallel once T006 lands,
  without waiting for T008/T011/T015's actual GPU runs

---

## Parallel Example: Foundational Phase

```bash
# After T002 (candidate registry) lands, run together:
Task: "Add LINKED_RESULTS entry in benchmarks/cuopt_tuning_candidates.py"   # T003
Task: "Registry-validation tests in tests/test_cuopt_tuning.py"             # T004
```

## Parallel Example: Polish, once T006 lands

```bash
Task: "Create aggregate_cuopt_tuning.py"                                    # T016
Task: "Add ranking-math tests in tests/test_cuopt_tuning.py"                # T018
Task: "Add README section"                                                  # T019
Task: "ruff check"                                                          # T020
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: run the full settings sweep on the GPU host, inspect the raw
   `CandidateResult` JSON files by hand — this alone already tells you whether any purely
   cuOpt-native setting helps, and by how much relative to both the baseline and Gurobi, before
   any polish
5. Phases 4-5 extend the investigation (newer version, last-resort preprocessing) only as far as
   User Story 1's own results indicate is worth pursuing

### Incremental Delivery

1. Setup + Foundational → verified, research-grounded candidate registry ready
2. User Story 1 → raw settings-sweep results, testable end-to-end, answers spec SC-001
3. User Story 2 → the same investigation, now also checked against a newer cuOpt release
4. User Story 3 → the same investigation, now with an honestly-gated last-resort fallback if
   needed
5. Polish → the single ranked comparison (explicitly reporting the Gurobi comparison, not just the
   baseline one), docs, lint, final recorded finding

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Unlike `specs/004-s85-solver-mode-experiment/`, this feature touches no file under `gpugem/` —
  everything lives in `benchmarks/` and `tests/`
- User Story 2 is the one genuine cross-story dependency in this feature (it needs US1's results
  to know what to re-test) — called out explicitly rather than glossed over as "independent"
- The `speedup_vs_gurobi` column and headline line (T016) exist specifically because the project's
  real preferred goal, stated directly by the user, is beating Gurobi — not just beating cuOpt's
  own prior number. Do not let `speedup_vs_baseline` alone stand in for that answer anywhere in
  this feature's output.
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently
