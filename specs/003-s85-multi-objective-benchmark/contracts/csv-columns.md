# summary.csv columns (contract)

objective_id, reaction, category, is_baseline,
gurobi_solve_s, gurobi_status, gurobi_residual_inf,
cuopt_solve_s, cuopt_status, cuopt_residual_inf,
obj_rel_diff, both_feasible,
runtime_ratio, is_outlier, outlier_direction

- One row per objective in `objectives.json` — gated **and** non-gated (spec Edge Cases: a
  failed objective is reported, not dropped). `both_feasible = False` rows carry their solve
  times/status for inspection but are excluded from the aggregate stats in `summary.json`.
- `runtime_ratio` = `cuopt_solve_s / gurobi_solve_s`; empty for non-gated rows.
- `is_outlier` = `runtime_ratio` outside `[median_ratio / 2, median_ratio * 2]` across gated rows
  (research.md R4); `outlier_direction` in `{faster, slower, ""}`.
- Times in seconds, solver call only (matches `002`'s `benchmark.csv` convention).
