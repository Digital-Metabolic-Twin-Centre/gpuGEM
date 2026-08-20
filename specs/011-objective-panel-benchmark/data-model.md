# Phase 1 Data Model: Cross-Model Objective-Panel Credibility Benchmark

## ObjectivePanelResult (new, per model x objective x solver)

`benchmarks/results/objective_panel/<model>/<objective_id>.json`, one per (model, objective) pair
-- both solvers' results live together in this one file (mirrors `run_objective_sweep.py`'s
existing per-objective JSON shape):

| Field | Type | Notes |
|---|---|---|
| `model` | str | matches `benchmarks.models.REGISTRY` key |
| `objective_id` | str | the `reaction_id` value from that model's `objective_candidates/<model>.csv` |
| `reaction_id` | str | duplicated for convenience alongside `objective_id` (they're the same value; `objective_id` is the stable key, `reaction_id` documents what it means) |
| `category` | str | carried through from the objective-candidate CSV, for readability in results/plots |
| `time_limit` / `res_tol` / `obj_tol` | float | reused from the model's own `results/<model>.json` (research R1) |
| `reps` | int | reused the same way; `3` for every model as of this feature |
| `gurobi` | object | `{"repeats": [...], "solve_s_median": float, "objective_median": float, "residual_inf_median": float, "iters_median": float, "status": str, "feasible": bool}` -- `feasible` is `all()` across repeats (research R7), the `_median` fields are medians across repeats (FR-003/FR-004) |
| `cuopt` | object | same shape as `gurobi` |
| `obj_agree_with_cuopt` | bool | cross-solver agreement on the *median* objective values, via `benchmarks.residual.objectives_agree` |
| `both_feasible` | bool | `gurobi.feasible and cuopt.feasible and obj_agree_with_cuopt` -- the correctness gate (FR-005/FR-006) |

Each solver's `repeats` list has the same per-repeat shape already used by `run_objective_sweep.py`/
`run_benchmark.py`: `{"repeat": int, "solve_s": float, "objective": float, "status": str, "iters": int,
"residual_inf": float, "feasible": bool}`.

## CrossModelObjectiveComparison (derived, assembled into the two CSVs -- not separately persisted)

### `results/objective_panel/objective_runtime.csv` (FR-007, "only the objective value and runtime")

`model, objective_id, reaction_id, solver, objective_value_median, runtime_s_median`

One row per (model, objective, solver) -- i.e. two rows per `ObjectivePanelResult` (one for `gurobi`, one
for `cuopt`). No status, no residual, no category -- deliberately minimal per FR-007's first sentence.

### `results/objective_panel/benchmark_details.csv` (FR-007, "also save... violations and other benchmarks")

`model, objective_id, reaction_id, category, solver, status, residual_inf_median, iters_median, feasible,
obj_agree_with_cuopt, both_feasible`

Same row grain (two rows per `ObjectivePanelResult`), additive to `objective_runtime.csv` -- a reader who
only wants speed reads the first file; a reader who wants the correctness picture reads the second. Both
regenerate purely from the committed per-(model, objective) JSONs, no solver import (research R6).

## Validation rules

- Every `objective_id` in a model's `ObjectivePanelResult` set MUST correspond to an existing row in that
  model's `objective_candidates/<model>.csv` (no fabricated or renamed objectives -- spec Assumptions).
  `benchmarks.models.REGISTRY` model names are the only valid `model` values.
- `both_feasible=False` combinations MUST still appear in both CSVs (never dropped) -- FR-006.
- `runtime_s_median`/`objective_value_median` MUST come from `statistics.median` over exactly `reps`
  per-repeat values, never a single repeat's value and never `min`/`max` (FR-003/FR-004).
