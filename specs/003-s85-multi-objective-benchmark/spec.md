# Feature Specification: S85 Multi-Objective cuOpt vs Gurobi Benchmark

**Feature Branch**: `003-s85-multi-objective-benchmark`

**Created**: 2026-07-27

**Status**: Draft

**Input**: User description: "The cuOpt is outperforming the gurobi in the benchmarks in the big models but for the S85 it looks like there is an outlier. I wonder if this big runtime gap for the S85 is accurate. I want to run the cuOpt on the S85 using different objective functions and see how it performs and how gurobi performs then we can judge about their run time more fairly. These objectives must be the most biologically meaningful objectives in the model. We can identify about 20 of them and then average out the run time to see how it performed. Along the way I want the test to be verbose so that I can monitor the progress and runtime, because it may take hours and I want to know how it is progressing."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Compare solvers across many objectives on S85 (Priority: P1)

A researcher who already has the cross-scale benchmark's single-objective (biomass) result for
the S85 model — where cuOpt was roughly 10x slower than Gurobi, unlike every other model in the
suite — wants to know whether that gap is a genuine, general property of solving S85 with cuOpt,
or an artifact of that one objective. They run a sweep that solves S85 with both cuOpt and
Gurobi across a set of about 20 distinct, biologically meaningful objective functions, and get
back a per-objective and averaged runtime comparison.

**Why this priority**: This is the entire point of the feature — without it there is no answer
to the motivating question, and nothing else in this spec has value on its own.

**Independent Test**: Can be fully tested by running the sweep against the S85 model and
confirming that a report is produced containing, for every configured objective, cuOpt's and
Gurobi's solve time, objective value, and feasibility status, plus an overall average runtime
for each solver across the objective set.

**Acceptance Scenarios**:

1. **Given** the S85 model and a defined set of ~20 biologically meaningful objective
   reactions, **when** the sweep is run, **then** each objective is solved by both cuOpt and
   Gurobi on the identical LP, and a result (time, objective value, status, feasibility) is
   recorded for each (objective, solver) pair.
2. **Given** a completed sweep, **when** the researcher reviews the output, **then** they can
   see the average and spread of cuOpt solve time and of Gurobi solve time across all objectives
   that passed the correctness gate, and the resulting runtime ratio between the two solvers.
3. **Given** the completed sweep's averaged ratio, **when** compared against the original
   single-objective (biomass) result, **then** the report makes clear whether that original
   result sits close to the average or is an outlier relative to the other objectives.

---

### User Story 2 - Monitor a multi-hour run in progress (Priority: P2)

Because solving a large model like S85 repeatedly across ~20 objectives with two solvers can
take hours, the researcher wants to be able to check at any point which objective and solver are
currently running and how much time has elapsed, without waiting for the whole sweep to finish.

**Why this priority**: Without visibility into progress, a multi-hour unattended run is opaque —
the researcher cannot tell a slow-but-healthy run from a stuck one, which undermines trust in the
eventual result and makes the run impractical to babysit.

**Independent Test**: Can be fully tested by starting the sweep and, while it is running,
observing progress output that identifies the current objective (name and position out of the
total count), which solver is active, and elapsed time for that step and for the run overall.

**Acceptance Scenarios**:

1. **Given** a sweep in progress, **when** the researcher checks its output at any time,
   **then** they can tell which objective (by name and index, e.g. "7 of 20") and which solver
   is currently being solved, and how long it has been running.
2. **Given** a single objective/solver solve that is taking a long time, **when** the researcher
   observes the output, **then** they can distinguish "still solving, this long so far" from a
   silent/hung process.

---

### User Story 3 - Resume an interrupted sweep (Priority: P3)

If a multi-hour sweep is interrupted (host restart, accidental Ctrl-C, timeout), the researcher
wants to restart it without losing the objectives that already finished and without waiting for
them to re-solve.

**Why this priority**: Lower priority than getting a correct comparison and seeing progress, but
important given the run length implied by ~20 objectives x 2 solvers on a model this large —
without resumability, one interruption near the end could cost most of a day.

**Independent Test**: Can be fully tested by interrupting a sweep partway through, restarting it,
and confirming that already-completed objectives are skipped (not re-solved) while remaining
objectives are solved and added to the results.

**Acceptance Scenarios**:

1. **Given** a sweep interrupted after some objectives have completed, **when** it is restarted,
   **then** previously completed (objective, solver) results are reused rather than recomputed.
2. **Given** a researcher who wants to force a clean re-run of an objective (e.g. after fixing a
   problem with it), **when** they explicitly request it, **then** that objective is re-solved
   and its stored result is replaced.

---

### Edge Cases

- What happens when a candidate objective reaction has zero feasible flux range or otherwise
  makes the LP infeasible/unbounded for S85? The result MUST be recorded and clearly marked as
  not usable for the runtime comparison, rather than silently dropped or averaged in as if it
  succeeded.
- What happens when one solver hits its time limit on a particular objective while the other
  solves normally? That (objective, solver) result MUST be marked as not reaching a verified
  optimum and excluded from the averaged runtime comparison, but still reported individually.
- What happens if fewer than 20 distinct biologically meaningful objective reactions can actually
  be identified in the S85 model? The sweep MUST proceed with however many valid, non-duplicate
  objectives were identified, and the report MUST state the actual count used.
- What happens if two candidate objectives resolve to the same underlying reaction? Duplicates
  MUST be removed before the sweep runs so each reported objective is solved once.
- What happens if the process running the sweep is interrupted mid-solve (neither solver finished
  for the current objective)? On resume, that objective's incomplete result MUST be re-solved
  from scratch for both solvers, not treated as complete.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST solve the S85 model's linear program with both cuOpt and Gurobi,
  using the same LP construction and correctness gating (feasibility residual tolerance, solver
  status, cross-solver objective agreement) already established for the cross-scale benchmark,
  for each objective in a defined set of at least 20 distinct, biologically meaningful objective
  functions.
- **FR-002**: Each objective in the set MUST represent a distinct, biologically interpretable
  quantity in the S85 model (for example: overall community or whole-body biomass, an individual
  taxon's biomass, or production/exchange of a specific metabolite of physiological interest) and
  MUST NOT duplicate another objective's underlying reaction.
- **FR-003**: The rationale for why each selected objective is considered biologically meaningful
  MUST be documented alongside the sweep's results.
- **FR-004**: For every (objective, solver) pair, the system MUST record wall-clock solve time,
  objective value, solver status, and feasibility residual.
- **FR-005**: While a sweep is running, the system MUST emit progress output identifying the
  current objective (name and position within the total set), which solver is currently
  executing, and elapsed time — at minimum when each (objective, solver) step starts and
  finishes, so a multi-hour run can be monitored as it goes.
- **FR-006**: The system MUST compute and report, across all objectives that passed the
  correctness gate, the average and spread (e.g. min/max or median) of cuOpt solve time and of
  Gurobi solve time, and the resulting cuOpt-to-Gurobi runtime ratio.
- **FR-007**: The system MUST identify and separately call out any objective whose cuOpt-vs-Gurobi
  runtime ratio deviates markedly from the overall average, so the researcher can see whether the
  original single-objective (biomass) result was representative or an outlier.
- **FR-008**: An (objective, solver) result MUST be excluded from the averaged runtime comparison,
  but still individually reported, whenever it fails the correctness gate (non-optimal status,
  residual above tolerance, or the two solvers' objective values disagreeing beyond tolerance for
  that objective).
- **FR-009**: The sweep MUST be resumable: restarting it after an interruption MUST skip
  (objective, solver) results that already completed successfully, unless the researcher
  explicitly requests a forced re-run.
- **FR-010**: The system MUST persist per-objective, per-solver results and the aggregated
  summary in a form that can be reviewed after the run completes, not only as transient console
  output.

### Key Entities *(include if feature involves data)*

- **ObjectiveDefinition**: One of the ~20 selected objectives — which reaction(s) it optimizes,
  a short biological category/rationale (e.g. community biomass, single-taxon biomass, metabolite
  exchange), and whether it is the same objective used in the original single-objective S85
  benchmark result.
- **ObjectiveSweepResult**: The outcome of solving one objective with one solver — solve time,
  objective value, solver status, feasibility residual, and whether it passed the correctness
  gate.
- **SweepSummary**: The aggregated view across all objectives — per-solver average/median/min/max
  solve time, the runtime ratio between solvers, the list of outlier objectives, and how the
  original single-objective result compares to the average.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: From a single report, a researcher can determine whether cuOpt's runtime
  disadvantage on S85 (originally observed as roughly 10x slower than Gurobi on the biomass
  objective) holds on average across at least 20 biologically distinct objectives, or is specific
  to that one objective.
- **SC-002**: At any point during a sweep expected to run for multiple hours, a researcher can
  determine which objective and solver are currently running and how much time has elapsed,
  without waiting for the full run to finish.
- **SC-003**: If a multi-hour sweep is interrupted partway through, restarting it resumes from
  where it left off — no already-completed objective's result is lost or recomputed unnecessarily.
- **SC-004**: The final report presents the average and spread of cuOpt and Gurobi runtimes across
  the objective set, and flags any objective whose solver runtime gap is markedly different from
  the rest, without requiring the researcher to read implementation code to find this out.

## Assumptions

- The specific list of ~20 objective reactions (which reactions, and why each is biologically
  meaningful) will be identified and documented during planning with domain input; this spec
  fixes the requirement that they be distinct, biologically interpretable, and documented, but
  not the exact list.
- Each objective is solved once per solver by default, rather than the 3-repeat protocol used for
  the single-objective cross-scale benchmark, because the statistical signal here comes from
  averaging across ~20 distinct objectives rather than from repeating one objective. A researcher
  can separately re-run any individual objective with repeats if its result looks anomalous.
- The per-solve time limit and the feasibility/objective-agreement tolerances already established
  for the cross-scale benchmark carry over unchanged for this sweep.
- This effort targets only the S85 model. Extending the same multi-objective comparison to other
  models (S84, Harvey, etc.) is out of scope here but is a natural follow-on if S85's outlier
  status turns out to be model-specific.
- "Verbose" progress means human-readable output sufficient to monitor which objective/solver is
  active and how much time has elapsed; it does not require a graphical dashboard.
