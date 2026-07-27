# Phase 1 Data Model: S85 Alternative Solver-Mode Experiment

Three entities, matching spec.md's Key Entities. Plain JSON/CSV records, consistent with `002`
and `003`'s existing `results/*.json` / `*.csv` convention.

## SolverModeVariant

One entry per candidate, stored in `benchmarks/solver_mode_variants.py` (mirrors `003`'s
`s85_objectives.OBJECTIVES` pattern — a plain importable list, not a data file, since both the
orchestrator and the subprocess worker need to import it directly, per research R2).

| Field | Type | Description |
|---|---|---|
| `id` | string | `baseline`, `methodical1`, `concurrent`, or `barrier_cold`. |
| `cuopt_kwargs` | dict | Overrides passed to `gpugem.solve(..., **cuopt_kwargs)`. Empty for `baseline` (research R5). `{"pdlp_solver_mode": 2}` for `methodical1`. `{"method": 0}` for `concurrent`. `{"method": 3}` for `barrier_cold`. |
| `rationale` | string | Why this variant might help, drawn from prior investigation notes (spec input). |
| `is_baseline` | bool | `true` only for `baseline`. |

**Validation rules**: exactly one `is_baseline=True` entry; `id` values unique; every
`cuopt_kwargs` key MUST be a real cuOpt parameter name (checked against
`get_solver_parameter_names()`, the same live registry used to confirm no LP scaling parameter
exists — see spec's originating investigation).

## VariantResult

One JSON file per variant at `benchmarks/results/s85_solver_modes/<id>.json`, written by the
orchestrator after each subprocess returns (or times out/crashes).

| Field | Type | Description |
|---|---|---|
| `variant` | object | `{id, cuopt_kwargs, rationale, is_baseline}` copied from `SolverModeVariant`. |
| `provenance` | object | Same shape as `003`'s per-objective provenance (model=S85, dims, nnz, sha256) — identical across all four variants since only solver settings change. |
| `outcome` | string | One of `"Completed"`, `"DidNotComplete"` (research R4). |
| `outcome_reason` | string \| null | When `outcome="DidNotComplete"`: `"timeout"` or `"crashed"`; `null` when `"Completed"`. |
| `subprocess_exit_code` | int \| null | The worker's exit code, recorded for crash diagnosis; `null` on a clean timeout (process killed by the timeout handler) or normal completion. |
| `solve_s` | float \| null | Wall-clock solve time; `null` if `DidNotComplete`. |
| `status` | string \| null | cuOpt termination status (`Optimal`, `TimeLimit`, ...); `null` if `DidNotComplete`. |
| `solved_by` | string \| null | `sol.get_solved_by()` result (`PDLP`, `DualSimplex`, `Barrier`, `Concurrent`, `Unset`) — research R8. |
| `iters` | int \| null | `nb_iterations` from cuOpt's `get_lp_stats()`, where reported. |
| `objective` | float \| null | cuOpt's reported objective value. |
| `residual_inf` | float \| null | Feasibility residual against the original `S`, `b` (same computation as `002`/`003`). |
| `gurobi_objective` | float | The single shared Gurobi reference value (research R6) — same for every variant's file. |
| `obj_rel_diff` | float \| null | Relative difference vs. `gurobi_objective`. |
| `verified_correct` | bool | `true` only if `outcome="Completed"`, `status="Optimal"`, `residual_inf <= res_tol`, and `obj_rel_diff <= obj_tol`. |
| `time_limit` | float | The cuOpt-level time budget passed to this variant. |
| `subprocess_timeout` | float | `time_limit + 60` (research R3). |

**Validation rules**: `verified_correct` MUST be `false` whenever `outcome != "Completed"` (a
variant that didn't complete can never be "correct"); `solve_s`/`status`/`objective` MUST all be
`null` together when `outcome="DidNotComplete"` (no partial-field states).

## VariantComparison

One record at `benchmarks/results/s85_solver_modes/summary.json` (and `summary.csv`, one row per
variant), produced by `aggregate_solver_modes.py` from the four `VariantResult` files.

| Field | Type | Description |
|---|---|---|
| `baseline_solve_s` | float | The baseline variant's `solve_s` (for candidates to be compared against). |
| `candidates` | list[object] | One entry per non-baseline variant: `{id, solve_s, verified_correct, speedup}` where `speedup = baseline_solve_s / solve_s` (research R7), `null` if the candidate didn't complete. |
| `best_candidate_id` | string \| null | `argmin(solve_s)` among `verified_correct` candidates with `speedup > 1`; `null` if none qualify. |
| `best_candidate_speedup` | float \| null | That candidate's speedup factor; `null` if `best_candidate_id` is `null`. |
| `any_did_not_complete` | bool | `true` if at least one variant has `outcome="DidNotComplete"` — surfaced prominently so a reader doesn't mistake an incomplete run for "no improvement found." |

**Validation rules**: `summary.csv` MUST have exactly 4 rows (baseline + 3 candidates) regardless
of outcome, so a crashed or timed-out variant is visible in the comparison, not silently absent
(spec Edge Cases, User Story 3 Acceptance Scenario 2).
