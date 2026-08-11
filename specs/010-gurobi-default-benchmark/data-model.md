# Phase 1 Data Model: Gurobi Default-Settings Benchmark Across All Models

## GurobiDefaultResult (new)

`benchmarks/results/gurobi_default/<model>.json`, one per model, produced by
`run_gurobi_default_benchmark.py`:

| Field | Type | Notes |
|---|---|---|
| `model` | str | matches `benchmarks.models.REGISTRY` key |
| `n_cols` | int | reused from the model's existing `results/<model>.json` provenance |
| `solve_s` | float | wall time for the `method=-1` solve |
| `objective` | float \| null | |
| `status` | str | e.g. `"Optimal"`, `"TimeLimit"` — same status vocabulary `solve_gurobi` already uses |
| `residual_inf` | float | `\|\|S v - b\|\|_inf`, via the existing `benchmarks.residual.feasibility_residual` |
| `bar_iters` | int | Gurobi's `BarIterCount` after solving (research R2) |
| `simplex_iters` | int | Gurobi's `IterCount` after solving (research R2) |
| `solved_by` | str | `"barrier"` if `bar_iters > 0` else `"simplex"` — which algorithm automatic mode actually picked |
| `feasible` | bool | correctness gate: `status == "Optimal" and residual_inf <= res_tol` |
| `obj_agree_with_cuopt` | bool | cross-solver objective agreement against the model's already-recorded cuOpt objective, same tolerance convention as the existing benchmark |
| `time_limit` | float | reused from the model's existing result |

## ThreeWayComparison (derived, not separately persisted per-model — assembled into the CSV)

`benchmarks/results/gurobi_default/comparison.csv`, one row per model, columns:

`model, scale, n_cols, cuopt_solve_s, cuopt_status, cuopt_residual_inf, gurobi_barrier_solve_s,
gurobi_barrier_status, gurobi_barrier_residual_inf, gurobi_default_solve_s,
gurobi_default_status, gurobi_default_residual_inf, gurobi_default_solved_by,
gurobi_default_speedup_vs_barrier, both_feasible`

`cuopt_*`/`gurobi_barrier_*` columns are reused verbatim from the model's existing
`results/<model>.json` (never re-solved — spec FR-004); `gurobi_default_*` columns come from the
new `GurobiDefaultResult`. `gurobi_default_speedup_vs_barrier = gurobi_barrier_solve_s /
gurobi_default_solve_s` (pure derived field, > 1 means default was faster than the project's
existing barrier baseline).

## Extended: `solve_gurobi`'s return dict (benchmarks/solve.py)

Two new keys, additive (research R2), every existing caller unaffected:

| New field | Source |
|---|---|
| `bar_iters` | `int(m.BarIterCount)`, already computed today and discarded after collapsing into `iters` |
| `simplex_iters` | `int(m.IterCount)`, same |
