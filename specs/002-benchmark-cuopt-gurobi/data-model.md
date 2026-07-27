# Data Model: benchmark suite

## BenchmarkModel (registry entry, benchmarks/models.py)
| field | type | notes |
|---|---|---|
| name | str | "e_coli_core","iML1515","Harvey","S84","S85" |
| scale | str | "small","medium","large" |
| kind | str | "cobra" | "mat" |
| source | str | cobra model name, or absolute .mat path |
| sha256 | str/null | file checksum for .mat; null for cobra (pinned by name+version) |
| objective | str/int/null | biomass reaction id / column index for .mat; null => cobra default |

## SolveResult (one per model x solver x repeat, benchmarks/results/*.json)
| field | type |
|---|---|
| model, solver, repeat | str,str,int |
| n_rows, n_cols, nnz | int |
| load_s, build_s, solve_s | float |
| objective | float |
| status | str (raw solver status) |
| iters | int/null (PDLP iters for cuOpt; simplex/barrier iters for Gurobi if available) |
| residual_inf | float (||S v - b||_inf on original system) |
| feasible | bool (residual <= tol AND status optimal) |
| solver_version, gpu_name | str |
| timestamp | ISO8601 |

## BenchmarkTable (aggregated, benchmarks/results/benchmark.csv)
One row per (model, solver): dims, nnz, median/min/max solve_s, objective,
iters, residual_inf, feasible, versions. Consumed by make_figure.py.
