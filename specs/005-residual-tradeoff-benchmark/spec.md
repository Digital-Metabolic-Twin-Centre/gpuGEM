# Feature Specification: Constraint-Residual Speed/Correctness Trade-off Benchmark

**Feature Branch**: `005-residual-tradeoff-benchmark`

**Created**: 2026-07-29

**Status**: Draft

**Input**: User description: "Add a benchmark comparing cuOpt's per_constraint_residual solver-mode setting on the genome-scale models already covered by the existing cross-scale benchmark (specs 002/003), motivated by a direct finding: on the S85 whole-body objective, setting per_constraint_residual=0 (cuOpt's own actual default, an aggregate L2-norm feasibility check) instead of gpugem's shipped per_constraint_residual=1 (a per-row L-infinity feasibility check requiring every one of ~2 million constraint rows to individually satisfy the tolerance) cuts cuOpt's solve time from ~510s to ~6.5s (a ~78x speedup, 984,000 iterations down to 3,800) but the returned solution's worst-row constraint violation grows from ~8.9e-05 to ~156 -- a large, real correctness regression, not numerical noise. This benchmark must NOT recommend or silently adopt per_constraint_residual=0 as a new default; the point is to produce a rigorous, reproducible, honest record of the speed-vs-correctness trade-off itself, computed the same way for both cuOpt configurations and cross-checked against Gurobi's own constraint violations on the identical LP. For each covered model, solve with: (a) cuOpt under gpugem's current shipped defaults, (b) cuOpt with per_constraint_residual=0 and everything else identical, and (c) Gurobi (reused from 002, not re-solved). Record wall-clock solve time, iteration count, and constraint-violation/residual statistics for each. Produce graphs comparing constraint violations and solve time across the three configurations per model, following this project's existing figure conventions. This is exploratory/diagnostic benchmarking work, not a proposal to change any shipped default."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See exactly what per_constraint_residual trades away, per model (Priority: P1)

A researcher who found that disabling cuOpt's per-row constraint-residual check made S85 dramatically faster wants to know precisely how much correctness that speed costs, on every model already in the project's cross-scale benchmark — not just S85 — and wants Gurobi's own violation level alongside both cuOpt configurations as an independent reference point, so "faster" is never reported without "how much less correct."

**Why this priority**: This is the entire point of the feature — without per-model, per-configuration violation and timing data, there is nothing to compare or visualize, and no way to judge the trade-off honestly.

**Independent Test**: Can be fully tested by running the benchmark and confirming that, for every model already covered by the existing cross-scale benchmark, a result exists for cuOpt under shipped defaults, cuOpt with `per_constraint_residual=0`, and Gurobi — each with wall-clock time, iteration count (where applicable), and constraint-violation statistics.

**Acceptance Scenarios**:

1. **Given** a model already benchmarked in the existing cross-scale benchmark, **when** this benchmark runs for that model, **then** it records solve time, iteration count, and worst-row absolute constraint violation for cuOpt under shipped defaults and for cuOpt with `per_constraint_residual=0`, computed with the identical residual calculation used elsewhere in this project.
2. **Given** the existing cross-scale benchmark already has a Gurobi result for a model, **when** this benchmark assembles its comparison, **then** it reuses that existing Gurobi result (and its own constraint-violation figure) rather than re-solving with Gurobi.
3. **Given** all three configurations' results for a model, **when** a researcher reviews them, **then** they can directly see the speed gained and the violation-severity cost of `per_constraint_residual=0` relative to both the shipped cuOpt default and Gurobi.

---

### User Story 2 - See the trade-off at a glance, not by reading raw numbers (Priority: P2)

Having the raw per-model, per-configuration numbers, the researcher wants a visual comparison — constraint violations and solve times side by side across the three configurations for each model — so the trade-off is immediately legible without cross-referencing JSON or CSV files by hand.

**Why this priority**: Raw numbers (User Story 1) establish the facts; a graph is what actually makes the trade-off usable for a reader deciding how seriously to weigh it, and orders-of-magnitude differences (microseconds to hundreds in violation, seconds to minutes in time) are hard to compare from a table alone.

**Independent Test**: Can be fully tested by generating the figures from already-collected results and confirming they show, per model, the constraint-violation level and the solve time for all three configurations, regenerable from the committed result data without needing a solver installed.

**Acceptance Scenarios**:

1. **Given** collected results for all covered models, **when** the comparison figures are generated, **then** one figure shows constraint violations across the three configurations for every model, and another shows solve time across the same three configurations.
2. **Given** the committed result data alone (no solver dependency), **when** the figures are regenerated, **then** they reproduce without needing cuOpt or Gurobi installed, consistent with this project's existing figure-regeneration convention.
3. **Given** a model where the violation is many orders of magnitude larger under one configuration than another, **when** the violation figure is produced, **then** the difference remains readable (not compressed into invisibility by a linear scale).

---

### User Story 3 - Never mistake "faster" for "recommended" (Priority: P3)

A project maintainer skimming this benchmark's output — months later, without the full context of why it was built — wants it to be unmistakable that `per_constraint_residual=0` is a diagnostic data point, not an endorsed configuration, so nobody accidentally treats the faster number as "the new default to switch to."

**Why this priority**: Lower priority than producing and visualizing the data itself, but without explicit framing, a stripped-down "cuOpt is 78x faster this way" figure — read out of context — could easily be misread as a recommendation, undermining the project's own correctness-first stance.

**Independent Test**: Can be fully tested by reviewing the benchmark's written output (report, figure captions, or accompanying notes) and confirming it explicitly states that the `per_constraint_residual=0` configuration is not validated for correctness and is not a suggested replacement for the shipped default.

**Acceptance Scenarios**:

1. **Given** the benchmark's output artifacts, **when** a reader unfamiliar with the backstory reviews them, **then** they encounter an explicit statement that `per_constraint_residual=0` results are shown for comparison only and are not a recommended or adopted configuration.
2. **Given** this benchmark has run, **when** the project's shipped default solver behavior is checked afterward, **then** it is unchanged — nothing in this feature alters what any other tool or user gets by default.

---

### Edge Cases

- What happens when a model shows little or no difference between the two cuOpt configurations (e.g., a small, well-conditioned model where `per_constraint_residual` rarely binds)? It MUST be recorded and shown plainly, not omitted — a negligible difference is itself informative evidence about which models the effect matters for.
- What happens if a cuOpt solve under either configuration fails to reach a solution within its time budget? That result MUST be recorded as such (consistent with this project's existing correctness-gate conventions) rather than silently dropped or misreported as a violation figure of zero.
- What happens when a violation value is exactly zero for a log-scale comparison? The figure generation MUST handle this without crashing or silently omitting the data point (e.g., a documented floor value or an explicit visual marker for "no measurable violation").
- What happens for a model where Gurobi's own existing violation figure is itself non-trivial (not near-zero)? It MUST still be shown as the reference point exactly as already recorded, not adjusted or excluded, so the comparison stays honest about all three configurations.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST, for every model already covered by the existing cross-scale benchmark, solve with cuOpt under the project's current shipped defaults, reusing an existing result if one is already available rather than re-solving unnecessarily.
- **FR-002**: The system MUST, for every covered model, solve with cuOpt using `per_constraint_residual=0` with every other setting identical to the shipped defaults for that model's size class.
- **FR-003**: The system MUST reuse each covered model's existing Gurobi result (solve time and constraint violation) from the existing cross-scale benchmark rather than re-solving with Gurobi.
- **FR-004**: For every (model, configuration) combination produced by this benchmark, the system MUST record wall-clock solve time, iteration count (where the solver reports one), the worst-row absolute constraint violation, and the count of constraint rows violated beyond a documented threshold, computed using the same residual calculation already used elsewhere in this project.
- **FR-005**: The system MUST produce a figure comparing constraint violations across the shipped-default cuOpt configuration, the `per_constraint_residual=0` configuration, and Gurobi, for every covered model.
- **FR-006**: The system MUST produce a figure comparing solve time across the same three configurations, for every covered model.
- **FR-007**: Both figures MUST be regenerable from committed result data alone, without requiring cuOpt or Gurobi to be installed, and MUST follow this project's existing figure styling conventions.
- **FR-008**: The benchmark's output MUST explicitly and unmistakably state that `per_constraint_residual=0` results are a diagnostic comparison point, not a validated or recommended configuration.
- **FR-009**: The benchmark MUST NOT modify this project's shipped default solver settings under any circumstance, regardless of what the comparison shows.
- **FR-010**: The benchmark MUST be re-runnable, producing a fresh, independently reviewable result each time, consistent with how this project's other benchmarks are reproduced.

### Key Entities *(include if feature involves data)*

- **ResidualModeResult**: The outcome of solving one model under one configuration (shipped-default cuOpt, `per_constraint_residual=0` cuOpt, or reused Gurobi) — solve time, iteration count (if applicable), worst-row absolute violation, count of rows violated beyond the documented threshold, objective value, and solver status.
- **ModelComparison**: The three `ResidualModeResult`s for a single model, aligned for direct comparison (same LP, same objective) and used as the unit the figures are built from.
- **TradeoffReport**: The full set of `ModelComparison`s across every covered model, plus the two comparison figures and the explicit non-recommendation statement.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For every model already covered by the existing cross-scale benchmark, a reader can determine — from one figure — how much solve-time speedup `per_constraint_residual=0` provides and how much larger its constraint violation is, relative to both the shipped cuOpt default and Gurobi, without reading raw result files.
- **SC-002**: The project's shipped default solver behavior is unchanged after this benchmark is built and run — re-running the existing cross-scale benchmark afterward reproduces the same settings-derived behavior as before.
- **SC-003**: No model requires a redundant Gurobi re-solve — every model's Gurobi reference comes from the existing cross-scale benchmark's already-committed results.
- **SC-004**: A reader unfamiliar with why this benchmark exists cannot come away believing `per_constraint_residual=0` is an endorsed or adopted configuration — the output states otherwise explicitly.

## Assumptions

- This benchmark covers all models already in the existing cross-scale benchmark (currently: e_coli_core, iML1515, Harvey, S84, S85), even though the motivating finding came from S85 specifically — smaller, better-conditioned models are expected to show a much smaller (or negligible) difference between the two cuOpt configurations, and that is itself a useful data point about which models the effect matters for, not a reason to narrow scope.
- The violated-rows-beyond-threshold statistic reuses the same threshold convention already used in this project's existing feasibility diagnostics, unless a specific model's scale makes that threshold uninformative, in which case the threshold actually used is documented alongside the result.
- Each (model, configuration) pair is solved once, consistent with this project's established practice (specs `003`/`004`) of prioritizing coverage across configurations over repeated runs of one, given the added compute cost of a full second cuOpt pass per model.
- Per-model time limits and correctness tolerances (for the shipped-default and Gurobi-reused results) match whatever the existing cross-scale benchmark already used for that model; the new `per_constraint_residual=0` solves use the same per-model time limit as their shipped-default counterpart for a fair timing comparison.
- "Graphs" means static, regenerable figure files consistent with the project's existing `benchmark_solvetime.png` convention — not an interactive dashboard.
