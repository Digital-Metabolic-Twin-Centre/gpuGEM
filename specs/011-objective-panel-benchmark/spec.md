# Feature Specification: Cross-Model Objective-Panel Credibility Benchmark

**Feature Branch**: `011-objective-panel-benchmark`

**Created**: 2026-08-14

**Status**: Draft

**Input**: User description: "run the analysis on all the models. Use all the objective functions in
the csv files for each model. Benchmark the models for all the objectives for each model. Use
previously tested cuOpt and gurobi settings. This test is to ensure the credibility of previous
results. Using the median of runtimes instead of one test. Plot the results. Save all the results
in csv files. Only the objective value and runtime. Also save the constraint violations and other
benchmarks. So for other benchmarks also use the median of the results instead of on run results.
The objectives for each model are under objective_candidates"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Check whether the published single-objective numbers are representative, not a fluke (Priority: P1)

Every runtime number this project has published so far for cuOpt vs. Gurobi, per model, comes from
solving that model with exactly one objective (its own shipped whole-body or biomass objective). A
researcher wants to know whether that one number is representative of the model in general, or
whether it happens to be unusually fast or slow compared to what any other biologically meaningful
objective on the same model would show.

**Why this priority**: This is the entire point of the request -- without checking many objectives
per model, every previously-published single-objective comparison in this project could be
(unintentionally) cherry-picked, and there is currently no way to tell.

**Independent Test**: Can be fully tested by running the existing benchmark tooling, with each
solver's already-established settings left untouched, against every objective already curated and
committed for a given model, and confirming a runtime and objective-value result (each the median
of multiple repeated runs, not a single run) is produced for every one of them.

**Acceptance Scenarios**:

1. **Given** a model with a committed, reviewed panel of objective reactions, **when** the existing
   benchmark tooling is run for that model, **then** every objective reaction in that panel is
   solved with both cuOpt (this project's shipped, scale-selected settings) and Gurobi (this
   project's already-established deliberately-configured setting), and a result is recorded for
   each.
2. **Given** a (model, objective, solver) combination is solved multiple times, **when** its result
   is recorded, **then** the reported runtime is the median across those repeated runs, not the
   time of any single run.
3. **Given** every model already covered by the main cross-scale benchmark, **when** this work is
   applied, **then** every one of them has a full set of per-objective results, not only a subset.

---

### User Story 2 - See the full comparison and spot outliers at a glance (Priority: P2)

Having the raw per-objective numbers, the researcher wants to see them plotted, so an objective on
which cuOpt or Gurobi behaves unusually (much faster or slower than the rest of that model's panel)
is visible immediately rather than requiring a manual scan of raw numbers.

**Why this priority**: Lower priority than producing the numbers themselves (User Story 1) -- the
plot is what makes the credibility check usable at a glance, but the raw numbers already have
value on their own once recorded.

**Independent Test**: Can be fully tested by generating the plot from already-collected results and
confirming it shows, for every model, the runtime of every objective in that model's panel for both
solvers, without needing either solver installed.

**Acceptance Scenarios**:

1. **Given** every objective in a model's panel has a recorded result, **when** the plot is
   generated, **then** it shows that model's full panel, both solvers, clearly distinguishable from
   one another.
2. **Given** the committed result data alone (no solver installed), **when** the plot is
   regenerated, **then** it reproduces without needing cuOpt or Gurobi, consistent with this
   project's existing reproducibility guarantee for its other figures.

---

### User Story 3 - Trust the constraint-violation and correctness picture, not just speed (Priority: P2)

Alongside the objective value and runtime, the researcher wants the constraint-violation residual
and other correctness-relevant benchmark data recorded for every (model, objective, solver)
combination, so a fast result that is actually infeasible or incorrect is never mistaken for a good
one.

**Why this priority**: Equal in importance to seeing the numbers plotted, but reported separately
here because it is a distinct kind of data (correctness, not speed) with its own save requirement
called out explicitly in the request.

**Independent Test**: Can be fully tested by inspecting the saved results for any (model,
objective, solver) combination and confirming the constraint-violation residual and other
correctness/benchmark data are present, each as the median across repeated runs.

**Acceptance Scenarios**:

1. **Given** a (model, objective, solver) combination has been solved multiple times, **when** its
   constraint-violation residual is recorded, **then** it is the median across those repeated
   runs, matching the same repeat-then-median treatment already required for runtime.
2. **Given** a (model, objective) combination whose solve fails the correctness gate already used
   elsewhere in this project (non-optimal status, residual beyond tolerance, or cross-solver
   objective disagreement), **when** its result is recorded, **then** it is clearly marked as
   failed, never silently included as if it had passed.

---

### Edge Cases

- What happens if a (model, objective, solver) combination fails the correctness gate? It MUST be
  recorded and clearly marked as failed, exactly like every other benchmark result in this project
  -- never silently dropped from the results or plotted as if it had passed.
- What happens when the objective reaction already used as a model's currently-published
  single-objective result also appears in that model's objective panel (as its baseline entry)?
  That is expected and required, not an error -- it is the direct point of comparison back to the
  number already published for that model.
- What happens if a full run across every model and every objective is interrupted partway through
  (a realistic possibility given the total number of objectives across all ten models)? Already
  -completed (model, objective) combinations MUST NOT be silently lost or need to be re-solved --
  the run must be resumable.
- What happens for a model whose objective panel is much smaller than another's (e.g. ten
  objectives vs. fifty)? Every objective actually present in that model's committed panel is run;
  panel size itself is not something this feature changes or second-guesses.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST solve, for every model already covered by the main cross-scale
  benchmark, every objective reaction listed in that model's already-committed, reviewed objective
  panel, using that reaction as the model's sole (maximized) objective.
- **FR-002**: Each (model, objective) combination MUST be solved with both solvers exactly as
  already established and published for that model in the main cross-scale benchmark -- neither
  solver's settings may be changed, tuned, or substituted for this analysis.
- **FR-003**: Each (model, objective, solver) combination MUST be solved multiple times (repeated
  runs), and the runtime recorded for it MUST be the median across those repeats, not the result of
  a single run.
- **FR-004**: The constraint-violation residual, and any other per-run benchmark measurement
  recorded for a (model, objective, solver) combination that can vary from run to run, MUST also be
  reported as the median across the repeated runs -- not a single run's value and not an extreme
  (minimum/maximum) value.
- **FR-005**: The system MUST apply the same correctness gate already used for every other recorded
  result in this project (solver status, feasibility-residual tolerance, cross-solver objective
  agreement) to every (model, objective) combination.
- **FR-006**: A (model, objective, solver) combination that fails the correctness gate MUST be
  recorded and clearly marked as failed; it MUST NOT be silently included in any results or plot as
  if it had passed.
- **FR-007**: Results MUST be saved to CSV files. At least one saved CSV MUST contain, for every
  (model, objective, solver) combination, only the objective value and the runtime. Constraint
  -violation residuals and other benchmark measurements for every combination MUST also be saved to
  CSV, in addition to (not instead of) the objective-value-and-runtime CSV.
- **FR-008**: The system MUST produce a plot of the results, allowing a reader to compare runtime
  across every objective in a model's panel, for both solvers, without reading the raw CSVs by
  hand.
- **FR-009**: Producing this feature's results MUST NOT alter any model's already-published
  single-objective result, nor any other model's already-recorded data.
- **FR-010**: This feature MUST NOT modify any of this project's shipped default solver settings,
  regardless of what the results show.
- **FR-011**: Given the number of (model, objective, solver) combinations involved, the system MUST
  allow the overall run to be resumed without repeating any (model, objective) combination that has
  already been completed.

### Key Entities *(include if feature involves data)*

- **ObjectivePanelResult**: per (model, objective, solver) combination -- objective value, runtime,
  solver status, constraint-violation residual, and any other per-run benchmark measurement, each
  as the median across repeated runs, plus whether the combination passed the correctness gate.
- **CrossModelObjectiveComparison**: the full set of `ObjectivePanelResult`s across every model and
  every objective in that model's panel, assembled for the plot and for at-a-glance comparison back
  to each model's already-published single-objective result.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For every model already covered by the main cross-scale benchmark, a runtime and
  objective-value result exists for every objective in that model's committed panel, for both
  solvers.
- **SC-002**: A reader can determine, for any given model, whether its already-published
  single-objective runtime is representative of that model's broader objective panel or an outlier,
  without re-running anything.
- **SC-003**: No previously-published single-objective result for any model changes as a side
  effect of this work.
- **SC-004**: Work already completed for a given (model, objective) combination is never lost or
  required to be redone if the overall run is interrupted and resumed.
- **SC-005**: This project's shipped default solver behavior is unchanged after this work is
  applied.

## Assumptions

- "Previously tested cuOpt and gurobi settings" means the exact configuration already used and
  published for each model in the main cross-scale benchmark (`results/<model>.json`): gpugem's
  shipped, scale-selected cuOpt settings, and Gurobi's deliberately-configured (barrier) setting --
  not the separately-added Gurobi default-settings (automatic-algorithm) configuration from a more
  recent, not-yet-established feature, which this credibility check is not yet scoped to include.
- Each model's objective panel is exactly and only what is already listed in that model's committed
  `benchmarks/objective_candidates/<model>.csv` file -- this feature does not add, remove, or
  substitute objectives; that curation already happened as separate, reviewed work.
- Repeats per (model, objective, solver) combination follow this project's established
  multiple-repeats-then-median convention (the same one already used for every other recorded
  result in this project), since the explicit purpose of this feature is a median across several
  runs, not a single run.
- This feature is independent of, and does not modify or deprecate, any prior model-specific
  objective-sweep tooling already in this project for an individual model -- every model, including
  ones with prior model-specific sweep work, is covered here uniformly through its own committed
  objective panel.
- Given the total number of (model, objective, solver) combinations across every model in the
  suite, this is expected to be a long-running batch operation rather than a single quick command --
  practical only because it is resumable per (model, objective) combination (FR-011).
