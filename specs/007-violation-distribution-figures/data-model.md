# Phase 1 Data Model: Violation Distribution Figures

## ViolationHistogram

Persisted, binned representation of one row population's (S-block or C-block) signed violations for
one model's `per_constraint_residual=0` solve. Small and fixed-size regardless of model row count.

| Field | Type | Notes |
|---|---|---|
| `bin_edges` | `float[25]` | Shared `numpy.logspace(-9, 3, 25)` across every model/figure (research R5) — magnitude, not signed. |
| `shortfall_counts` | `int[24]` | Count of rows whose violation falls short of the required balance/range (`signed_viol < 0`), by `|signed_viol|` magnitude bin. "Category A" / negative side. |
| `excess_counts` | `int[24]` | Count of rows whose violation exceeds the required balance/range (`signed_viol > 0`), by magnitude bin. "Category B" / positive side. |
| `n_rows` | `int` | Total rows in this population (S-block or C-block row count) — denominator for context. |
| `n_satisfied` | `int` | Rows with `signed_viol == 0` (or below the smallest bin edge) — kept separate so a model with (near-)zero violations is still representable without corrupting the log-scale bins (spec edge case). |

Invariant: `n_satisfied + sum(shortfall_counts) + sum(excess_counts) == n_rows`.

## ModelComparison (existing, from feature 005 — extended)

`benchmarks/results/residual_tradeoff/<model>.json`, produced by
`run_residual_tradeoff.py::build_model_comparison`. Existing fields (`model`, `scale`, `n_cols`,
`shipped_default`, `gurobi`, `speedup_residual_0_vs_shipped`, `violation_ratio_residual_0_vs_shipped`)
are unchanged. The `residual_0` sub-object (a `ResidualModeResult`, unchanged existing fields:
`configuration`, `source`, `solve_s`, `iterations`, `status`, `objective`, `residual_inf`,
`rows_violated`, `time_limit`) gains two new fields:

| New field | Type | Notes |
|---|---|---|
| `violation_histogram_equations` | `ViolationHistogram` | Always present — every model has an S-block. |
| `violation_histogram_constraints` | `ViolationHistogram \| null` | `null` for models with no C-block (the small BiGG models: `e_coli_core`, `iML1515`); present for every whole-body/microbiome model. |

## EquationViolationFigure (output artifact, not persisted data)

`figures/violation_distribution_equations.png`. One overlaid, semi-transparent stepped area per
model, drawn from that model's `violation_histogram_equations`, colored by a single ordinal
colormap keyed to model-size rank, log-scale magnitude axis, mirrored shortfall/excess count axis,
direct per-model text label plus backup legend (research R6). Includes every model currently in the
benchmark suite (no model is excluded — every model has an S-block).

## ConstraintViolationFigure (output artifact, not persisted data)

`figures/violation_distribution_constraints.png`. Same visual structure as
`EquationViolationFigure`, drawn from `violation_histogram_constraints`, limited to models where
that field is non-null (models with a C-block). `e_coli_core` and `iML1515` are simply absent from
this figure (spec User Story 3, Acceptance Scenario 2) — not shown as empty entries.

## RuntimeComparison (existing, from feature 005 — regenerated, not restructured)

`benchmarks/results/residual_tradeoff/comparison.csv`, produced by
`aggregate_residual_tradeoff.py`. Schema unchanged (one row per model per configuration); row count
grows from 15 (5 models x 3 configs) to 27 (9 models x 3 configs) once all nine models have a
`per_constraint_residual=0` result (FR-001/FR-003).
