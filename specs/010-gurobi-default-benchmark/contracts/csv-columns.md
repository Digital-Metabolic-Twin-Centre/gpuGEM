# comparison.csv columns (contract)

model, scale, n_cols,
cuopt_solve_s, cuopt_status, cuopt_residual_inf,
gurobi_barrier_solve_s, gurobi_barrier_status, gurobi_barrier_residual_inf,
gurobi_default_solve_s, gurobi_default_status, gurobi_default_residual_inf,
gurobi_default_solved_by, gurobi_default_feasible, gurobi_default_obj_agree_with_cuopt,
gurobi_default_speedup_vs_barrier, both_feasible

- One row per model, covering every model in the main suite (spec FR-005/User Story 2), regardless
  of whether the default-settings solve passed or failed its correctness gate.
- `cuopt_*`/`gurobi_barrier_*` columns are reused verbatim from that model's existing
  `results/<model>.json` — never re-derived or re-solved (spec FR-004).
- `gurobi_default_speedup_vs_barrier = gurobi_barrier_solve_s / gurobi_default_solve_s` (> 1 means
  default settings solved faster than this project's existing deliberately-configured baseline).
- `gurobi_default_feasible` / `gurobi_default_obj_agree_with_cuopt` are explicit booleans, not
  inferred from `status` alone — so a failed gate (spec FR-003) is visible directly in the CSV,
  not just in a nonstandard `status` string.
- Times in seconds, solver call only, matching the existing benchmark's convention.
