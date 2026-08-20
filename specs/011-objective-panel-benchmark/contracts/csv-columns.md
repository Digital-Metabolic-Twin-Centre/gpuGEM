# CSV column contracts

## `results/objective_panel/objective_runtime.csv` (FR-007, minimal view)

```
model, objective_id, reaction_id, solver, objective_value_median, runtime_s_median
```

- Two rows per (model, objective) combination present in `results/objective_panel/<model>/*.json` --
  one row where `solver="cuopt"`, one where `solver="gurobi"`.
- `runtime_s_median` / `objective_value_median` are the `*_median` fields from `data-model.md`'s
  `ObjectivePanelResult`, never a single repeat's value.
- No status/residual/feasibility columns here by design -- that data lives in `benchmark_details.csv`
  instead (FR-007's "only the objective value and runtime").

## `results/objective_panel/benchmark_details.csv` (FR-007, "also save" view)

```
model, objective_id, reaction_id, category, solver, status, residual_inf_median, iters_median,
feasible, obj_agree_with_cuopt, both_feasible
```

- Same row grain as `objective_runtime.csv` (two rows per combination).
- A combination that failed the correctness gate (`both_feasible=False`) MUST still appear with its
  real `status`/`residual_inf_median` values, never omitted (FR-006).
- `obj_agree_with_cuopt` and `both_feasible` are per-(model, objective) values, repeated identically
  across that combination's two solver rows (mirrors `residual_tradeoff`'s comparison.csv convention of
  repeating per-model derived fields across that model's rows).

## Shared

- Both CSVs regenerate byte-for-byte reproducibly from the committed per-(model, objective) JSON files
  alone -- no wall-clock, no solver import, no random elements (spec SC-001/FR-007).
- Row order: models in `benchmarks.models.ALL_MODELS` registry order; within a model, objectives in the
  order they appear in that model's `objective_candidates/<model>.csv`; within an objective, `cuopt` row
  before `gurobi` row.
