# Phase 1 Data Model: Constraint-Residual Speed/Correctness Trade-off Benchmark

Three entities, matching spec.md's Key Entities. Plain JSON/CSV records, consistent with prior
features' `results/*.json` / `*.csv` convention.

## ResidualModeResult

The outcome of one (model, configuration) pair. For `shipped_default` and `gurobi`, these fields
are read from `002`'s existing `results/<model>.json` (research R1) — not recomputed. For
`residual_0`, they come from a fresh solve in this feature.

| Field | Type | Description |
|---|---|---|
| `configuration` | string | `shipped_default`, `residual_0`, or `gurobi`. |
| `source` | string | `"reused"` (shipped_default, gurobi) or `"fresh"` (residual_0) — research R1. |
| `solve_s` | float | Wall-clock solve time. |
| `iterations` | int \| null | Solver-reported iteration count where applicable (`null` for Gurobi's barrier — different meaning, not cross-compared; spec Requirements notes iteration count is per-configuration only). |
| `status` | string | Solver termination status (`Optimal`, etc.). |
| `objective` | float | Reported objective value. |
| `residual_inf` | float | Worst-row absolute constraint violation — `benchmarks.residual.feasibility_residual`, identical computation for all three configurations (research R4). |
| `rows_violated` | int \| null | Count of rows with residual beyond the documented threshold (`1e-6`, matching `gpugem`'s own `stoich_rows_violated_1e6` convention) — populated only for `residual_0` (research R3); `null` for reused configurations. |
| `time_limit` | float | The time budget this solve was allowed (research R6). |

**Validation rules**: `rows_violated` MUST be `null` whenever `source == "reused"` (never
fabricated); `residual_inf` MUST be present and non-null for all three configurations of every
model (the one statistic guaranteed uniformly available, per R4).

## ModelComparison

The three `ResidualModeResult`s for one model, aligned for direct comparison.

| Field | Type | Description |
|---|---|---|
| `model` | string | One of `e_coli_core`, `iML1515`, `Harvey`, `S84`, `S85`. |
| `scale` | string | Scale class, copied from `002`'s provenance (`small`/`medium`/`whole-body`/`microbiome`). |
| `n_cols` | int | Variable count, for axis labeling consistent with `make_figure.py`. |
| `shipped_default` | ResidualModeResult | |
| `residual_0` | ResidualModeResult | |
| `gurobi` | ResidualModeResult | |
| `speedup_residual_0_vs_shipped` | float | `shipped_default.solve_s / residual_0.solve_s`. |
| `violation_ratio_residual_0_vs_shipped` | float | `residual_0.residual_inf / shipped_default.residual_inf` — how much worse the violation gets, the other half of the trade-off `speedup` describes. |

## TradeoffReport

The full set of `ModelComparison`s plus the artifacts built from them.

| Field | Type | Description |
|---|---|---|
| `comparisons` | list[ModelComparison] | One per covered model, in `002`'s existing scale order (small → medium → whole-body → microbiome). |
| `csv_path` | string | `results/residual_tradeoff/comparison.csv` — one row per (model, configuration) triple. |
| `violations_figure_path` | string | `figures/residual_tradeoff_violations.png`. |
| `solvetime_figure_path` | string | `figures/residual_tradeoff_solvetime.png`. |
| `non_recommendation_notice` | string | The fixed caption text asserting `residual_0` is diagnostic-only — present verbatim in both figures (spec FR-008). |

**Validation rules**: `comparisons` MUST have exactly 5 entries (one per model already in `002`) —
a missing model is a build error, not a silently incomplete report (spec FR-001 covers "every
model already covered").
