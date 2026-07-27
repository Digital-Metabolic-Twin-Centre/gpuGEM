# benchmark.csv columns (contract)

model, scale, kind, n_rows, n_cols, nnz,
gurobi_solve_s_median, gurobi_solve_s_min, gurobi_solve_s_max, gurobi_obj, gurobi_status, gurobi_iters, gurobi_residual_inf,
cuopt_solve_s_median, cuopt_solve_s_min, cuopt_solve_s_max, cuopt_obj, cuopt_status, cuopt_iters, cuopt_residual_inf,
obj_rel_diff, both_feasible,
gurobi_version, cuopt_version, gpu_name

- Times in seconds (solver call only). Objectives raw. residual_inf = ||S v - b||_inf.
- both_feasible must be True for the row to contribute a bar to the figure.
