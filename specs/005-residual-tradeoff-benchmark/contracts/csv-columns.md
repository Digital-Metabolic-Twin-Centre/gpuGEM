# comparison.csv columns (contract)

model, scale, n_cols, configuration, source,
solve_s, iterations, status, objective, residual_inf, rows_violated, time_limit,
speedup_residual_0_vs_shipped, violation_ratio_residual_0_vs_shipped

- One row per (model, configuration) — 5 models x 3 configurations = 15 rows, always, regardless
  of outcome.
- `speedup_residual_0_vs_shipped` and `violation_ratio_residual_0_vs_shipped` are per-model
  values, repeated across that model's 3 rows for convenience (so a plotting script doesn't need
  a separate join).
- `rows_violated` is empty (not zero) for `configuration in {shipped_default, gurobi}` —
  distinguishing "not computed" from "computed as zero" (research R3; data-model.md validation
  rule).
- Times in seconds, solver call only, matching `002`'s `benchmark.csv` convention.
