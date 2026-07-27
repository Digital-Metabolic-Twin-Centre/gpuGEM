# Phase 1 Data Model: S85 Multi-Objective cuOpt vs Gurobi Benchmark

Three entities, matching spec.md's Key Entities. All are plain JSON/CSV records (no database) —
consistent with `002-benchmark-cuopt-gurobi`'s existing `results/*.json` / `benchmark.csv`
convention, which this feature extends rather than replaces.

## ObjectiveDefinition

One entry per selected objective, stored as a list in
`benchmarks/results/s85_objectives/objectives.json`. Written once when the objective set is
finalized (research R1); read by both the sweep runner and the aggregator.

| Field | Type | Description |
|---|---|---|
| `id` | string | Stable short identifier used in filenames and CLI `--objective`, e.g. `liver_biomass`. |
| `reaction` | string | Exact reaction id from the model's `rxns` array, e.g. `Liver_biomass_maintenance`. |
| `category` | string | One of `whole_body`, `organ_biomass`, `immune_cell_biomass`, `microbiome`. |
| `rationale` | string | One-sentence reason this reaction is biologically meaningful (spec FR-003). |
| `is_baseline` | bool | `true` only for the single entry reusing S85's existing objective (`Whole_body_objective_rxn`), so the sweep's average can be compared back to the `002` result. |

**Validation rules** (enforced by `tests/test_s85_objectives.py`, no GPU required):
- `reaction` values MUST be unique across all entries (spec FR-002 — no duplicate underlying
  reaction) and MUST each resolve to exactly one index in the S85 model's `rxns` array.
- Exactly one entry MUST have `is_baseline = true`.
- `len(objectives) >= 20` unless fewer valid, non-duplicate candidates exist in the model (spec
  Edge Cases), in which case the actual count is used and recorded.

## ObjectiveSweepResult

One JSON file per objective at `benchmarks/results/s85_objectives/<id>.json`, holding both
solvers' outcomes for that objective — same shape as the existing per-model result
(`benchmarks/results/S85.json`) so the two benchmarks stay easy to cross-read, plus the
objective's own identity fields at the top level.

| Field | Type | Description |
|---|---|---|
| `objective` | object | `{id, reaction, category, rationale, is_baseline}` copied from `ObjectiveDefinition`. |
| `provenance` | object | Model-level provenance (source path, sha256, dims, nnz) — identical for every objective since it's the same S85 LP with only `c` changed; reused from `benchmarks.models.build_lp`. |
| `build_s` | float | LP build time for this run. |
| `reps` | int | Repeats per solver for this objective (default 1, spec Assumptions). |
| `time_limit` | float | Per-solve cap in seconds (default 900, unchanged from `002`). |
| `res_tol`, `obj_tol` | float | Correctness-gate tolerances, unchanged from `002`. |
| `versions` | object | Solver/GPU versions, same shape as `002`. |
| `timestamp` | string (ISO-8601) | When this objective's solves completed. |
| `gurobi`, `cuopt` | object | `{repeats: [...], solve_s_median, solve_s_min, solve_s_max, objective, feasible}` — identical shape to the existing per-model JSON's solver blocks. |
| `obj_rel_diff` | float \| null | Relative disagreement between the two solvers' objective values. |
| `both_feasible` | bool | Correctness gate outcome for this objective (spec FR-008) — `false` excludes it from the aggregated averages but it is still present in this file. |

**Validation rules**:
- `gurobi.repeats` / `cuopt.repeats` length MUST equal `reps`.
- If `both_feasible` is `false`, the aggregator (R4/R5) MUST exclude this file's solve times from
  averaging but MUST still list it (spec FR-008, Edge Cases: infeasible/unbounded/time-limited
  objectives are recorded, not silently dropped).

## SweepSummary

One record at `benchmarks/results/s85_objectives/summary.json` (machine-readable) and
`summary.csv` (one row per objective, human-inspectable), produced by `aggregate_sweep.py` from
all `ObjectiveSweepResult` files present.

| Field | Type | Description |
|---|---|---|
| `n_objectives_total` | int | Objectives in `objectives.json`. |
| `n_objectives_gated` | int | Objectives with `both_feasible = true`, i.e. included in averages. |
| `gurobi_solve_s_mean`, `gurobi_solve_s_median`, `gurobi_solve_s_min`, `gurobi_solve_s_max` | float | Across gated objectives. |
| `cuopt_solve_s_mean`, `cuopt_solve_s_median`, `cuopt_solve_s_min`, `cuopt_solve_s_max` | float | Across gated objectives. |
| `runtime_ratio_median` | float | Median of per-objective `cuopt_solve_s / gurobi_solve_s`. |
| `baseline_ratio` | float | The `is_baseline` objective's own `cuopt_solve_s / gurobi_solve_s`, for direct comparison against `runtime_ratio_median` (spec SC-001, User Story 1 Acceptance Scenario 3). |
| `outliers` | list[object] | `{id, ratio, direction: "faster"|"slower"}` for objectives whose ratio is outside `[median/2, median*2]` (research R4). |
| `per_objective_csv_row` | — | `summary.csv` carries one row per gated *and* non-gated objective (with `both_feasible` as a column) so nothing is silently dropped (spec Edge Cases). |

**Validation rules**:
- Mean/median/min/max fields are computed only over `both_feasible = true` rows; `n_objectives_gated` MUST equal that row count.
- `summary.csv` row count MUST equal `n_objectives_total` (gated and non-gated both present),
  matching spec's edge-case requirement that failed objectives are reported, not dropped.
