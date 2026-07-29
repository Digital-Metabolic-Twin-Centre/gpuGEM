# Phase 0 Research: Constraint-Residual Speed/Correctness Trade-off Benchmark

## R1. What's actually reusable from `002`, and what must be freshly solved

**Decision**: Read `benchmarks/results/<model>.json` (shipped-default cuOpt + Gurobi) directly for
all 5 models — no re-solve. Only the `per_constraint_residual=0` configuration is solved fresh.

**Rationale**: Confirmed by inspecting `results/S85.json` and `results/benchmark.csv`: every model
already has `gurobi.solve_s_median`, `cuopt.solve_s_median`, and — critically — `residual_inf`
(the worst-row `||S v - b||_inf`, computed via `benchmarks.residual.feasibility_residual`, the
exact same function this feature needs) for both solvers already committed. Re-solving either
would waste compute and risk introducing new run-to-run variance into what should be a stable
reference point (spec FR-001/FR-003, SC-003).

## R2. `per_constraint_residual=0` solves run in-process, not via subprocess isolation

**Decision**: Unlike `004`'s untested-setting variants (Concurrent, cold Barrier), the new solve
here calls `gpugem.solve(..., per_constraint_residual=0)` directly, no subprocess wrapper.

**Rationale**: `004`'s subprocess isolation existed specifically because Concurrent and cold
Barrier were *never tried before* on this model family and could plausibly hang or OOM-crash.
`per_constraint_residual=0` is the opposite case: it's cuOpt's own long-standing built-in default
(the value before gpugem's `_defaults.py` overrides it), and this exact configuration was already
run to completion during the investigation that motivated this feature (~6.5s on S85, clean
`Optimal` status, no crash). There is no comparable unknown-behavior risk to guard against, so the
added complexity of a subprocess boundary isn't justified here — matches this project's practice
of not adding machinery beyond what the actual risk calls for.

## R3. "Rows violated beyond threshold" is only available for the freshly-solved configuration

**Decision**: The "count of constraint rows violated beyond a documented threshold" statistic
(spec FR-004) is computed and reported only for the new `per_constraint_residual=0` results. For
the two reused configurations (shipped-default cuOpt, Gurobi), only the worst-row L-infinity
residual (already committed in `002`'s JSON) is available, and the comparison and figures treat
that as the primary, uniformly-available-across-all-three metric.

**Rationale**: The rows-violated-count requires the raw solution vector (`gpugem`'s
`FBAResult.feasibility["stoich_rows_violated_1e6"]`, already computed internally whenever
`check_feasibility=True`, which `benchmarks.solve.solve_cuopt`/`solve_gurobi` already pass). But
`002`/`003`'s committed result JSON files intentionally never persisted flux vectors (to keep
files small — see `002`'s plan.md), so this can't be retroactively recovered for the reused
results without re-solving them, which R1 already ruled out. Rather than silently fabricate a
number or force an apples-to-oranges 3-way comparison on a statistic only 1 of 3 configurations
actually has, this is reported honestly as "available for the new configuration, not for the
reused ones" (spec Assumptions).

**Alternatives considered**: *Re-solve all three configurations for every model to get a uniform
rows-violated-count everywhere* — rejected: directly contradicts spec FR-001/FR-003's explicit
"reuse, don't re-solve" requirement and SC-003, for a secondary/supplementary statistic when the
primary comparison metric (worst-row residual) is already uniformly available.

## R4. Worst-row L-infinity residual is the primary violation metric

**Decision**: The constraint-violation figure (spec FR-005) plots worst-row absolute residual
(`residual_inf`) as its primary series across all three configurations for every model.

**Rationale**: This is the exact metric the motivating S85 finding was expressed in (`8.9e-05` →
`156`), it's already computed identically for every existing result via
`benchmarks.residual.feasibility_residual`, and — per R3 — it's the only violation statistic
available uniformly across all three configurations, making it the only fair basis for a genuine
3-way comparison.

## R5. Figure conventions: log scale, zero-violation floor, and non-recommendation framing

**Decision**: Both figures follow `benchmarks/make_figure.py`'s existing conventions (matplotlib
with `Agg` backend, log-scale y-axis, per-bar value annotations, a reproducibility caption). The
violations figure additionally: (a) uses a log scale given the observed range spans from
`~1e-9` (e_coli_core-scale residuals) to `~1e2` (S85 under `per_constraint_residual=0`) — roughly
11 orders of magnitude; (b) floors any exactly-zero residual to a small epsilon
(matching the smallest non-zero residual observed, documented in the figure's own data prep code)
purely for plotting, with the true value in the annotation and underlying CSV; (c) visually
distinguishes the `per_constraint_residual=0` bars (a distinct hatch pattern, following
`make_figure.py`'s precedent of using annotation to flag `gate fail` bars) plus a caption stating
outright that this configuration is a diagnostic comparison point, not a recommendation (spec
FR-008, User Story 3) — baked into the artifact itself, not left to a separate document that could
get lost.

**Alternatives considered**: *Linear scale* — rejected: an 11-order-of-magnitude range would
render every bar except the largest as invisible. *Separate "safe" vs "diagnostic" figures* —
rejected: spec User Story 2 explicitly wants the trade-off visible "at a glance" in one place, and
splitting the configurations across figures would undermine the direct comparison that's the
entire point of the feature.

## R6. Time budget for the new solves

**Decision**: Each model's `per_constraint_residual=0` solve reuses the exact `time_limit` value
already recorded in that model's `002` result JSON (`d["time_limit"]`), rather than a new
project-wide constant.

**Rationale**: Keeps the timing comparison fair and consistent with what the shipped-default
configuration was actually allowed — a model-specific time budget difference would confound "this
configuration is faster" with "this configuration was given more/less time to prove it."
