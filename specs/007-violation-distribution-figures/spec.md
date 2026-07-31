# Feature Specification: Violation Distribution Figures for per_constraint_residual=0

**Feature Branch**: `007-violation-distribution-figures`

**Created**: 2026-07-31

**Status**: Draft

**Input**: User description: "add the cuOpt per_constraint_residual = 0 runtime to the figure as well. I also want seperate figure to show how many and with what magniture the results violate the equations and mass balance. To show the violated equations for each model Make a back-to-back / mirrored bar chart (population-pyramid style). The y-axis is the magnitude of equation violation. The x-axis is a count, number of reactions/equations with that magnitude of violation. category A on the left (values plotted as negative), category B on the right (positive). If I have multiple time points, overlay them as semi-transparent filled areas rather than bars, using a sequential colormap ordered by year, and label each contour with its model name. We can make a seperate similar figure to show the violated constraints numbers and magnitude for each model. These two figures will show the violated constraints or equations with per_constraint_residual = 0 setting"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See the per_constraint_residual=0 runtime for every benchmarked model, not just the original five (Priority: P1)

A researcher who already has a three-way runtime comparison (cuOpt shipped default, cuOpt with
`per_constraint_residual=0`, Gurobi) for the five models originally in the benchmark suite wants
that same comparison extended to cover every model now in the suite — including the four
microbiome models added after that comparison was first built — so the picture stays complete as
the benchmark grows.

**Why this priority**: The runtime comparison already exists and is trusted; extending its
coverage is the smallest, most immediately valuable step, and the two new distribution figures
(User Stories 2-3) are about visualizing data this story's underlying solves produce.

**Independent Test**: Can be fully tested by confirming that every model currently in the
benchmark suite has a recorded `per_constraint_residual=0` result, and that the existing
three-configuration runtime comparison figure includes all of them, not only the original five.

**Acceptance Scenarios**:

1. **Given** a model already in the benchmark suite that does not yet have a
   `per_constraint_residual=0` result, **when** this work is applied, **then** a result is
   produced for it the same way the original five models' results were produced, without
   altering any of those five's already-recorded results.
2. **Given** every model now has a `per_constraint_residual=0` result, **when** the runtime
   comparison figure is regenerated, **then** it shows all three configurations for every model
   currently in the suite.

---

### User Story 2 - See how many mass-balance equations are violated, and by how much, per model (Priority: P2)

Having runtime numbers, the researcher wants to see the *shape* of what `per_constraint_residual=0`
costs in correctness — not just a single worst-row number, but how many mass-balance equations are
violated and at what magnitude, for every model, in one figure that makes it possible to compare
models against each other directly.

**Why this priority**: This is the core new insight this feature exists to deliver — the existing
worst-row-residual figure (from prior work) already shows the single worst violation per model,
but not how widespread or how the violations are distributed, which matters for judging how
serious the correctness cost really is.

**Independent Test**: Can be fully tested by generating the figure from committed results and
confirming it shows, for every model, the count of violated mass-balance equations at each
magnitude of violation, with under-satisfied and over-satisfied violations visually separated.

**Acceptance Scenarios**:

1. **Given** `per_constraint_residual=0` results exist for every model, **when** the figure is
   generated, **then** each model's distribution of mass-balance-equation violations is shown:
   magnitude of violation on one axis, count of equations at that magnitude on the other, with
   equations that fall short of the required balance visually mirrored against equations that
   exceed it.
2. **Given** more than one model is shown together, **when** the figure is generated, **then**
   each model's distribution is rendered so that overlapping distributions remain individually
   visible (not one opaque distribution hiding another), and each is clearly identified by its
   model name.
3. **Given** a model whose solve under `per_constraint_residual=0` violates no equations at all
   (or negligibly few), **when** the figure is generated, **then** that model still appears with
   its (near-)empty distribution, rather than being silently left out.

---

### User Story 3 - See the same picture for coupling constraints (Priority: P3)

The researcher wants the equivalent view for coupling constraints (the whole-body/microbiome
models' cross-compartment constraints, distinct from the mass-balance equations) in its own,
comparably-structured figure.

**Why this priority**: Lower priority than the equation-violation figure — coupling constraints
only exist for the whole-body/microbiome models, not the small BiGG models, so this figure covers
a subset of what User Story 2 covers — but it completes the picture for the models where coupling
constraints are a real part of the formulation.

**Independent Test**: Can be fully tested by generating the second figure from committed results
and confirming it shows, for every model that has coupling constraints, the count of violated
coupling constraints at each magnitude of violation, in the same visual style as the equation
figure.

**Acceptance Scenarios**:

1. **Given** `per_constraint_residual=0` results exist for every model, **when** this figure is
   generated, **then** it shows the violated-coupling-constraint distribution for every model that
   has coupling constraints, in the same magnitude-vs-count, mirrored layout as the equation
   figure.
2. **Given** a model that has no coupling constraints at all, **when** this figure is generated,
   **then** that model is simply absent from this figure (not shown as an empty or misleading
   entry) — its absence here does not affect its presence in the equation-violation figure.

---

### Edge Cases

- What happens for a model with zero violated equations (or constraints) under
  `per_constraint_residual=0`? It MUST still be represented in the relevant figure, contributing
  an empty or near-empty distribution, not be silently dropped as if it were missing data.
- What happens for a single equation or constraint whose violation magnitude is extreme
  compared to the rest of that model's distribution? It MUST still be represented on the shared
  scale, not clipped off invisibly.
- What happens for a violation magnitude of exactly zero, on an axis meant to span many orders of
  magnitude? It MUST be handled without breaking the figure's scale, consistent with how this
  project's existing violation figures already handle this case.
- What happens for a model that has no coupling constraints (the small BiGG models)? It is
  included in the equation-violation figure but correctly excluded from the coupling-constraint
  figure, per User Story 3's Acceptance Scenario 2.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST produce a `per_constraint_residual=0` result for every model
  currently in the benchmark suite that does not already have one, using the same method already
  used to produce this result for the original five models.
- **FR-002**: Producing new results MUST NOT alter any previously-recorded
  `per_constraint_residual=0` result for the original five models.
- **FR-003**: The existing three-configuration runtime comparison (cuOpt shipped default, cuOpt
  with `per_constraint_residual=0`, Gurobi) MUST be regenerated to include every model currently in
  the benchmark suite.
- **FR-004**: For every model's `per_constraint_residual=0` result, the system MUST capture the
  full per-equation mass-balance violation (not only the single worst-row summary value already
  captured), so a distribution — not just an extreme value — can be shown.
- **FR-005**: The system MUST produce a figure showing, for every model, the count of violated
  mass-balance equations at each magnitude of violation.
- **FR-006**: This figure's layout MUST place violation magnitude on one axis and equation count
  on the other, with equations that fall short of the required balance mirrored against equations
  that exceed it around a shared axis (population-pyramid style), so the two directions of
  violation are visually distinguishable at a glance.
- **FR-007**: Where more than one model's distribution is shown together, each MUST be rendered
  so that overlapping distributions all remain individually visible, and each MUST be identified
  by its model name directly in the figure, not only via a separate legend.
- **FR-008**: Each model's distribution MUST be visually distinguished using a single ordered
  color progression, ordered by model size, consistent with how this project already orders
  models elsewhere.
- **FR-009**: The system MUST produce a second figure, structured the same way as the equation
  figure, showing violated coupling constraints instead of violated equations, covering every
  model that has coupling constraints.
- **FR-010**: Both new figures MUST be regenerable from committed result data alone, without
  requiring cuOpt or Gurobi to be installed, consistent with this project's existing figure
  reproducibility convention.
- **FR-011**: This work MUST NOT modify any of this project's shipped default solver settings.

### Key Entities *(include if feature involves data)*

- **ViolationDistribution**: for one model, under the `per_constraint_residual=0` configuration,
  the full set of individual row violations for a given row population (mass-balance equations or
  coupling constraints) — each entry's magnitude and whether it falls short of or exceeds the
  required balance.
- **EquationViolationFigure**: the population-pyramid-style comparison of every model's
  mass-balance `ViolationDistribution`.
- **ConstraintViolationFigure**: the equivalent comparison for coupling constraints, covering only
  models that have them.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reader can see the `per_constraint_residual=0` runtime alongside the two existing
  configurations for every model currently in the benchmark suite, not only the original five.
- **SC-002**: A reader can see, from one figure, how many mass-balance equations are violated and
  by what magnitude for every model, without inspecting raw result files.
- **SC-003**: A reader can see the equivalent picture for coupling constraints in a second,
  comparably-structured figure, correctly limited to models that have coupling constraints.
- **SC-004**: Both new figures remain regenerable from committed result data alone.
- **SC-005**: This project's shipped default solver behavior is unchanged after this work is
  applied.

## Assumptions

- "The figure" in the original request refers to this project's existing three-configuration
  runtime comparison (already built for the original five models); this feature extends its
  coverage rather than creating a competing figure.
- "Equations" means the stoichiometric mass-balance rows, and "constraints" means the coupling
  rows, matching the distinction this project's models already have between these two row
  populations; a model with no coupling rows is simply absent from the constraint figure.
- "Category A" and "category B" in the mirrored layout correspond to the two directions a row's
  violation can take: falling short of the required balance versus exceeding it.
- The original request's "multiple time points... ordered by year" is reinterpreted for this
  dataset as "multiple models... ordered by model size," since there is no time dimension in this
  benchmark; model size is this project's existing, established ordering convention (see the
  cross-scale benchmark's model comparisons).
- Because both figures always compare more than one model at once, the semi-transparent
  overlaid-distribution rendering the original request described for the multi-series case applies
  by default, rather than a single-series bar rendering.
- Violation magnitude is shown on a logarithmic scale, consistent with every other
  violation-magnitude figure already in this benchmark suite, given violations span many orders of
  magnitude.
- Each model is solved once under `per_constraint_residual=0` (no repeats), matching this
  project's existing convention for this specific configuration (established when it was first
  introduced for the original five models).
