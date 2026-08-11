# Feature Specification: Gurobi Default-Settings Benchmark Across All Models

**Feature Branch**: `010-gurobi-default-benchmark`

**Created**: 2026-08-11

**Status**: Draft

**Input**: User description: "currently we have added the gurobi with two defined methods as
benchmarks. Add the runtimes with gurobi with default settings and no optimisations by settings
to the benchmarks for all of the models"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See Gurobi's out-of-the-box runtime, not only the project's own tuned choice, for every model (Priority: P1)

A researcher who already has Gurobi results for every model in the benchmark suite — solved with
a deliberately chosen algorithm setting — wants to also see how Gurobi performs with no algorithm
setting chosen at all: its own default, automatic behavior, exactly what any user who never touches
Gurobi's tuning parameters would get.

**Why this priority**: This is the entire point of the request. Every Gurobi number this project
has published so far reflects one specific, deliberately picked algorithm setting; without an
untouched-default data point, the comparison implicitly favors whichever configuration was chosen,
which cuts against this project's own standard of not letting a tuned number pass as representative
without saying so.

**Independent Test**: Can be fully tested by running the existing benchmark tooling with Gurobi's
algorithm setting left untouched against every model already in the suite and confirming a result
(solve time, objective, status, feasibility residual) is produced for each, gated by the same
correctness checks already used for every other recorded result.

**Acceptance Scenarios**:

1. **Given** a model that already has a recorded cuOpt result and a recorded Gurobi result (solved
   with a specific, deliberately chosen algorithm setting), **when** the existing benchmark tooling
   is run for that model with Gurobi's algorithm setting left at its own default, **then** a new
   result is produced and recorded for that default-settings solve, gated by the same
   feasibility-residual tolerance, solver-status check, and cross-solver objective-agreement check
   already used for every other result.
2. **Given** the default-settings result has been produced for a model, **when** that model's
   already-recorded cuOpt result and already-recorded (deliberately-configured) Gurobi result are
   checked afterward, **then** both are unchanged — neither was re-solved or altered as a side
   effect.
3. **Given** every model in the suite, **when** this work is applied, **then** every one of them
   has a Gurobi default-settings result, not only a subset.

---

### User Story 2 - See all three numbers side by side, per model, in one place (Priority: P2)

Having the raw default-settings numbers, the researcher wants to see them alongside the existing
cuOpt and deliberately-configured-Gurobi numbers in a single comparison, per model, rather than
having to cross-reference separate result files by hand.

**Why this priority**: Lower priority than producing the numbers themselves (User Story 1) — the
comparison view is what makes the new data usable at a glance, but the raw numbers already have
value on their own once recorded.

**Independent Test**: Can be fully tested by generating the comparison from already-collected
results and confirming it shows, for every model, the solve time for cuOpt, for Gurobi with its
deliberately-configured setting, and for Gurobi with its own default setting — regenerable from
committed result data without needing either solver installed.

**Acceptance Scenarios**:

1. **Given** every model has a Gurobi default-settings result, **when** the comparison is
   generated, **then** it shows all three configurations for every model, correctly identified as
   distinct from one another.
2. **Given** the committed result data alone (no solver installed), **when** the comparison is
   regenerated, **then** it reproduces without needing cuOpt or Gurobi, consistent with this
   project's existing reproducibility guarantee for its other comparisons.

---

### Edge Cases

- What happens if Gurobi's own default, automatic algorithm selection happens to choose the exact
  same underlying algorithm as the project's already-configured setting (e.g. both end up using
  barrier for a particular model)? That is an expected, informative possible outcome — not an
  error condition — and MUST be reported as-is, not treated as a failure or suppressed.
- What happens if a model's default-settings solve fails the correctness gate (non-optimal status,
  residual beyond tolerance, or objective disagreement with the already-recorded cuOpt result)? It
  MUST be recorded and clearly marked as failed, exactly like any other model in this project's
  existing benchmarks — never silently included in the comparison as if it had passed.
- What happens to the separate, narrower two-method Gurobi comparison already recorded for a
  single supplemental problem (Harvey's alternate two-demand LP, distinct from the whole-body
  objective used in the main comparison)? It is out of scope for this feature — this feature
  covers the main, whole-suite benchmark's models, not that supplemental single-problem comparison.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST solve every model currently in the benchmark suite with Gurobi using
  its own default, automatic algorithm-selection behavior — no explicit algorithm choice or other
  performance-tuning setting applied — using the project's existing benchmark tooling, not a
  separate or one-off solving mechanism.
- **FR-002**: The system MUST apply the same correctness gate already used for every other
  recorded result (solver status, feasibility-residual tolerance, cross-solver objective agreement
  against the model's already-recorded cuOpt result) to every default-settings solve.
- **FR-003**: A default-settings solve that fails the correctness gate MUST be recorded and
  clearly marked as failed; it MUST NOT be silently included in any comparison as if it had passed.
- **FR-004**: Producing default-settings results MUST NOT alter any model's already-recorded cuOpt
  result or already-recorded deliberately-configured Gurobi result.
- **FR-005**: The system MUST produce a comparison, covering every model in the suite, showing
  cuOpt, the already-configured Gurobi setting, and the new Gurobi default-settings result
  side by side per model.
- **FR-006**: Results MUST be produced and stored in the same reproducible, resumable form already
  used by this project's other benchmarks — re-running MUST NOT require re-solving a model whose
  default-settings result already exists.
- **FR-007**: The comparison MUST remain regenerable from committed result data alone, without
  requiring cuOpt or Gurobi to be installed.
- **FR-008**: This feature MUST NOT modify any of this project's shipped default solver settings.

### Key Entities *(include if feature involves data)*

- **GurobiDefaultResult**: per model — solve time, objective, solver status, feasibility residual,
  and which underlying algorithm Gurobi's automatic selection actually used, for the
  default-settings solve.
- **ThreeWayComparison**: per model — the cuOpt result, the already-configured Gurobi result, and
  the new Gurobi default-settings result, assembled for side-by-side viewing.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reader can see, for every model in the benchmark suite, Gurobi's out-of-the-box
  runtime alongside the already-published cuOpt and deliberately-configured-Gurobi numbers.
- **SC-002**: No previously-recorded cuOpt or Gurobi result for any model changes as a side effect
  of this work.
- **SC-003**: The comparison remains regenerable from committed result data alone.
- **SC-004**: This project's shipped default solver behavior is unchanged after this work is
  applied.

## Assumptions

- "Gurobi with default settings and no optimisations by settings" means Gurobi's algorithm-choice
  parameter is left at its own factory default (automatic selection) rather than the specific
  algorithm this project's existing benchmark tooling currently chooses deliberately; run-control
  housekeeping (a time budget, quiet logging) is not considered an "optimisation by settings" and
  stays consistent with every other recorded result so the comparison is apples-to-apples on
  everything except the one setting under study.
- "All of the models" refers to every model in the project's main cross-scale benchmark suite (the
  same set already covered by the existing cuOpt-vs-Gurobi comparison), not the separate,
  narrower two-method Gurobi comparison already recorded for the supplemental Harvey two-demand
  problem, which this feature does not touch.
- Unlike this project's earlier cuOpt-side experiments (e.g. `per_constraint_residual=0`), running
  Gurobi with its own default settings is not a correctness-risk configuration needing a
  non-recommendation caveat — it is Gurobi's own fully-supported standard behavior, so this
  comparison is presented as an equally valid data point, not a trade-off investigation.
- Default-settings results are produced with the same repeat count and per-model time-limit
  convention already used by the existing benchmark, for direct comparability.
