# Phase 1 Data Model: cuOpt-Native Settings Tuning for Large Microbiome Models

## TuningCandidate

One entry in `benchmarks/cuopt_tuning_candidates.py`'s registry — mirrors
`specs/004-s85-solver-mode-experiment/`'s `SolverModeVariant` pattern, extended with source
traceability (spec FR-011) and warm-start two-phase support.

| Field | Type | Notes |
|---|---|---|
| `id` | `str` | Unique, filesystem-safe (used as `results/cuopt_tuning/<id>.json`) |
| `user_story` | `"US1" \| "US2" \| "US3"` | Which of the spec's three user stories this candidate belongs to — required for the ranked comparison to label each row (spec FR-010) |
| `cuopt_kwargs` | `dict` | Passed verbatim as `**cuopt_kwargs` to `gpugem.solve` (never edits `gpugem/_defaults.py`) |
| `warm_start` | `bool` (default `False`) | If `True`, this candidate is solved as a **cold phase then a warm phase**: cold solve produces the PDLP warm-start data (`sol.get_pdlp_warm_start_data()`), which is fed into a second solve via `set_pdlp_warm_start_data`; both phases' wall times are recorded, and only the warm phase's time is compared against the baseline (the cold phase is bookkeeping, not the candidate's claimed result) |
| `source_note` | `str` | Which research.md finding (R2/R3/R4/etc.) motivated this candidate — spec FR-011's traceability requirement |
| `requires_isolated_venv` | `bool` (default `False`) | `True` only for User Story 2's version-upgrade re-runs; tells the orchestrator to invoke the upgrade venv's interpreter instead of the base env's |

## CandidateResult

One `results/cuopt_tuning/<id>.json` — the on-disk record for one candidate (or one cold+warm
pair).

| Field | Type | Notes |
|---|---|---|
| `id` | `str` | Matches the `TuningCandidate.id` that produced it |
| `user_story` | `str` | Copied from the candidate |
| `cuopt_version` | `str` | `26.6.0` or `26.8.0` — which interpreter actually ran this |
| `cuopt_kwargs` | `dict` | Exact settings used (recorded, not just referenced by id, so a result JSON is self-describing even if the registry changes later) |
| `phases` | `list[PhaseResult]` | Length 1 for a normal candidate; length 2 (`cold`, `warm`) for a `warm_start` candidate |
| `status` | `str` | The claimed phase's (last phase's) cuOpt status string |
| `solve_s` | `float` | The claimed phase's wall time |
| `iterations` | `int \| None` | The claimed phase's iteration count |
| `objective` | `float \| None` | The claimed phase's objective value |
| `residual_inf` | `float` | `\|\|S v - b\|\|_inf` against S85's stoichiometric equalities |
| `objective_agrees_with_gurobi` | `bool` | Compared against S85's already-published Gurobi result (read-only; never re-solved — spec FR-003) |
| `verified_correct` | `bool` | `status == "Optimal" and residual_inf <= res_tol and objective_agrees_with_gurobi` — the single correctness gate every candidate is graded by (research.md R7); a candidate that errors, times out, or is rejected as invalid still gets a `CandidateResult` with `verified_correct=False`, never a missing file |
| `error` | `str \| None` | Populated for a crashed/rejected/timed-out candidate (`"timeout"`, `"crashed"`, or cuOpt's own rejection message) — spec Edge Cases: never silently dropped |

### PhaseResult (nested)

| Field | Type | Notes |
|---|---|---|
| `phase` | `"single" \| "cold" \| "warm"` | |
| `solve_s` | `float` | |
| `status` | `str` | |
| `iterations` | `int \| None` | |
| `objective` | `float \| None` | |

## TuningComparison (aggregate output)

`results/cuopt_tuning/summary.json` / `summary.csv` — the single ranked comparison spec
FR-010/SC-004 require, built by `aggregate_cuopt_tuning.py` from every committed
`CandidateResult` (never re-solving).

| Column | Type | Notes |
|---|---|---|
| `candidate_id` | `str` | |
| `user_story` | `str` | |
| `cuopt_version` | `str` | |
| `solve_s` | `float` | The claimed-phase wall time |
| `speedup_vs_baseline` | `float` | `baseline_solve_s / solve_s`; `> 1` is faster than cuOpt's own prior default |
| `speedup_vs_gurobi` | `float` | `gurobi_solve_s / solve_s`, reading S85's already-published Gurobi wall time; `> 1` means this candidate actually **beats Gurobi** — the project's real, preferred goal (not merely "improved over cuOpt's own baseline") — kept as its own first-class column precisely so it's never buried under the baseline comparison |
| `verified_correct` | `bool` | Never omitted — a fast-but-wrong candidate still gets a row, with `verified_correct=False`, so it's visibly disqualified rather than silently absent |
| `source_note` | `str` | Copied from the candidate — keeps the traceability requirement visible in the final artifact, not just the registry |

`aggregate_cuopt_tuning.py` also determines and prints:
- the single best-verified-correct-candidate line by `speedup_vs_baseline` (or "none beat the
  baseline" if that's the honest outcome, matching `004`'s precedent), and
- **whether any verified-correct candidate has `speedup_vs_gurobi > 1`** — printed as its own
  explicit line ("N candidate(s) beat Gurobi" / "no candidate beat Gurobi; closest was Nx slower")
  — since closing/reversing the cuOpt-vs-Gurobi gap, not just beating cuOpt's own prior number, is
  this investigation's actual motivating goal.

Sort order: `verified_correct` candidates first, then by `speedup_vs_gurobi` descending (not
`speedup_vs_baseline`) — the ranking itself reflects the real goal, not a secondary metric.

## PreprocessingCandidate (User Story 3, only if reached)

| Field | Type | Notes |
|---|---|---|
| `id` | `str` | |
| `transform` | `Callable` | Applied to S85's `(S, b, lb, ub, c)` before solving; must be paired with an exact, recorded inverse |
| `inverse` | `Callable` | Maps the preprocessed solution back to the original variable space |
| `reconstruction_verified` | `bool` | Set by re-checking the inverse-mapped result against the same correctness gate as every other candidate — spec FR-008/SC-003: this MUST be `True` before `solve_s` is even reported as relevant |
