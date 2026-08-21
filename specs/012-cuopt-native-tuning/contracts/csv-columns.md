# CSV Contract: `results/cuopt_tuning/summary.csv`

One row per candidate (across all three user stories); never omits a failed/timed-out candidate
(spec FR-010).

| Column | Type | Description |
|---|---|---|
| `candidate_id` | string | |
| `user_story` | string | `US1`, `US2`, or `US3` |
| `cuopt_version` | string | `26.6.0` or `26.8.0` |
| `solve_s` | float | Claimed-phase wall time |
| `speedup_vs_baseline` | float | `baseline_solve_s / solve_s` — vs. cuOpt's own prior default |
| `speedup_vs_gurobi` | float | `gurobi_solve_s / solve_s` — vs. S85's already-published Gurobi time; `> 1` means this candidate actually beats Gurobi, the project's real preferred goal, not just cuOpt's own baseline |
| `status` | string | cuOpt's own status string for the claimed phase |
| `residual_inf` | float | |
| `objective_agrees_with_gurobi` | bool | |
| `verified_correct` | bool | The single correctness gate result — never blank |
| `source_note` | string | Which research.md finding motivated this candidate |

Row order: `US1` candidates (registry order), then `US2`, then `US3` — never alphabetical by
`candidate_id` (matches the ordering-bug lesson already learned and regression-tested in
`specs/011-objective-panel-benchmark/`'s `aggregate_objective_panel.py`).
