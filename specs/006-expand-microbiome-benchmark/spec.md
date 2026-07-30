# Feature Specification: Expand Cross-Scale Benchmark to Additional Microbiome Models

**Feature Branch**: `006-expand-microbiome-benchmark`

**Created**: 2026-07-29

**Status**: Draft

**Input**: User description: "Extend the existing cross-scale cuOpt vs Gurobi benchmark (specs 002/003/005) to include the additional microbiome whole-body models the user has added to benchmarks/model_cache/ -- mWBM_S9, mWBM_S15, mWBM_S23, and mWBM_S83 (male, each with a plain .mat and a "_lifted" .mat variant already present; the existing benchmark's registry only ever used the plain, non-lifted variant for S84/S85, so these four follow that same established pattern) -- alongside the five models already covered (e_coli_core, iML1515, Harvey, S84, S85). For every newly-added model, solve with both cuOpt (gpugem shipped defaults) and Gurobi on the identical LP, using the exact same correctness gate (feasibility residual tolerance, solver status, cross-solver objective agreement) already established in the existing benchmark -- no new comparison methodology, this is coverage expansion of the existing one. Regenerate and save the existing benchmark_solvetime.png-style comparison figure so it includes all nine models (the five existing plus the four new ones), with models ordered by model size (variable/reaction count) along the axis rather than by scale-class then size as today, since scale-class grouping stops being the most useful ordering once several same-scale-class microbiome models of different sizes are present. The new models' results must be produced through the exact same reproducible, resumable benchmark tooling already in place (not a one-off/ad-hoc script), and the correctness gate must be enforced identically -- a new model that fails the gate must be reported as such, not silently included in the figure as if it succeeded."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Get correctness-gated results for the four new models (Priority: P1)

A researcher who has added four new microbiome whole-body models to the project wants each one
solved with both cuOpt and Gurobi on the identical LP, checked against the same correctness gate
already trusted for the five existing models, using the project's existing benchmark tooling
rather than a separate one-off process.

**Why this priority**: This is the entire point of the feature — without correctness-gated
results for the new models, there is nothing to add to the comparison, and no way to trust
whatever numbers a one-off script might produce.

**Independent Test**: Can be fully tested by running the existing benchmark tooling against each
of the four new models and confirming a result (solve time, objective, solver status, feasibility
residual, pass/fail against the correctness gate) is produced for both cuOpt and Gurobi, in the
same form already used for the five existing models.

**Acceptance Scenarios**:

1. **Given** a newly-added microbiome model, **when** the existing benchmark tooling is run
   against it, **then** both cuOpt and Gurobi solve the identical LP and a result is recorded for
   each, gated by the same feasibility-residual tolerance, solver-status check, and cross-solver
   objective-agreement check already used for the five existing models.
2. **Given** all four new models have been run, **when** the five existing models' results are
   checked afterward, **then** they are unchanged from before this feature — no existing result
   was re-solved or altered as a side effect.
3. **Given** the benchmark is re-run after all nine models already have results, **when** it
   completes, **then** no model is re-solved unnecessarily (consistent with the existing
   resumable/skip behavior).

---

### User Story 2 - See all nine models in one size-ordered comparison (Priority: P2)

Having results for all nine models, the researcher wants a single comparison figure — the same
kind already produced for the five existing models — showing all nine together, ordered by model
size rather than grouped by scale class first, since several models now share the same
"microbiome" scale class but span a wide range of sizes.

**Why this priority**: Lower priority than having correct results (User Story 1) — the figure is
what makes the expanded comparison usable at a glance, but the underlying data has value on its
own even before the figure is regenerated.

**Independent Test**: Can be fully tested by regenerating the comparison figure from the
committed results and confirming it shows all nine models, positioned along the axis in strictly
increasing order of model size (variable/reaction count), not grouped by scale class first.

**Acceptance Scenarios**:

1. **Given** results exist for all nine models, **when** the comparison figure is regenerated,
   **then** it shows all nine, ordered strictly by size along the axis.
2. **Given** the committed result data alone (no solver installed), **when** the figure is
   regenerated, **then** it reproduces without needing cuOpt or Gurobi, consistent with the
   existing benchmark's reproducibility guarantee.

---

### User Story 3 - Never let a failed new model masquerade as a success (Priority: P3)

If one of the new, previously-untested models behaves unexpectedly — fails to converge, disagrees
with Gurobi's objective, or violates the feasibility tolerance — the researcher wants that failure
visible in the results and the figure, not silently dropped or shown as if it had passed.

**Why this priority**: Lower priority than producing and visualizing results for models that
behave normally, but without this, one badly-behaved new model could quietly corrupt the
credibility of the whole comparison — exactly the kind of silent failure this project's
correctness-first approach exists to prevent.

**Independent Test**: Can be fully tested by observing what happens when a model fails the
correctness gate (e.g. by temporarily using a deliberately too-tight tolerance) and confirming the
failure is recorded and visible, not omitted from the results or figure.

**Acceptance Scenarios**:

1. **Given** a new model whose solve fails the correctness gate, **when** results are recorded,
   **then** the failure is explicitly marked, not merged into the passing results as if it
   succeeded.
2. **Given** a failed model, **when** the comparison figure is regenerated, **then** the failure
   is visibly indicated for that model rather than the model being silently excluded or shown with
   an implied passing result.

---

### Edge Cases

- What happens if a new model is significantly larger or more numerically demanding than any
  existing model and takes substantially longer to solve? It MUST still be governed by the same
  time-budget and correctness-gate conventions already in place — recorded as a time-limit
  outcome if it doesn't converge in time, not treated as a special case.
- What happens if a new model's dimensions or structure differ in some way from S84/S85 (the
  existing microbiome-scale models)? It MUST go through the identical loading and correctness-gate
  pipeline as any other model — no new, model-specific logic.
- What happens to the four "_lifted" file variants that were added alongside the plain ones? They
  are out of scope for this feature — only the plain variant is used, matching the existing
  convention for S84/S85.
- What happens if the comparison figure's size-based reordering changes the relative position of
  any of the five existing models? That is expected and acceptable — the ordering rule applies
  uniformly to all nine models, not just the four new ones.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST solve each of the four newly-added microbiome models with both
  cuOpt (this project's shipped defaults) and Gurobi on the identical LP, using the project's
  existing benchmark tooling — not a separate or one-off solving mechanism.
- **FR-002**: The system MUST apply the same correctness gate already used for the five existing
  models (solver status, feasibility-residual tolerance, cross-solver objective agreement) to
  every newly-added model, with identical pass/fail criteria.
- **FR-003**: A newly-added model that fails the correctness gate MUST be recorded and clearly
  marked as failed; it MUST NOT be silently included in the comparison figure as if it had passed.
- **FR-004**: The system MUST regenerate the existing cross-scale comparison figure so that it
  includes all nine models (the five existing plus the four newly added) in a single view.
- **FR-005**: The regenerated figure MUST order all nine models strictly by model size
  (variable/reaction count) along its axis, replacing the current scale-class-then-size ordering.
- **FR-006**: Results for the four new models MUST be produced and stored in the same
  reproducible, resumable form already used for the five existing models — re-running the
  benchmark MUST NOT require re-solving a model whose result already exists.
- **FR-007**: Adding the four new models MUST NOT alter any of the five existing models' already-
  recorded results unless an existing model is explicitly re-run.
- **FR-008**: This feature MUST NOT modify any of this project's shipped default solver settings,
  regardless of how the new models perform.

### Key Entities *(include if feature involves data)*

- **BenchmarkModel** (extended): the four newly-added microbiome models (S9, S15, S23, S83),
  represented the same way the five existing models already are — name, scale class, loader kind,
  source path, checksum, and dimensions (rows, columns, non-zeros).
- **SolveResult**: unchanged in shape from the existing benchmark — model, solver, timing,
  objective, status, and feasibility residual — now populated for four additional models.
- **BenchmarkComparison**: the full, nine-model view assembled from all `SolveResult`s, ordered by
  model size, used to produce the regenerated figure.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reader can view one figure showing the solve-time comparison across all nine
  models — the five existing plus the four newly added — ordered by model size, without needing
  to cross-reference multiple figures or tables.
- **SC-002**: Every one of the four newly-added models has a recorded, correctness-gated result
  (a pass or a documented failure) — none silently missing from the results or the figure.
- **SC-003**: The five existing models' previously-recorded results are byte-for-byte unchanged
  after this feature is implemented, unless one is explicitly re-run.
- **SC-004**: The comparison figure remains regenerable from committed result data alone, without
  requiring cuOpt or Gurobi to be installed, consistent with the existing benchmark's
  reproducibility guarantee.

## Assumptions

- Only the plain (non-`_lifted`) `.mat` file for each new model is used, matching the established
  convention for S84/S85; the `_lifted` variants remain available but are out of scope for this
  feature — a possible follow-up if the lifted/free-variable formulation is later of interest.
- Each new model uses its own shipped objective with no explicit override, matching the S84/S85
  convention (Harvey is currently the only model in the existing set that needs an explicit
  objective override).
- New models are solved with the same repeat count and per-model time-limit convention already
  used by the existing benchmark, for consistency with the five existing results.
- "Model size" for ordering purposes means variable/reaction count, consistent with how the
  existing figure already labels each bar.
- The four new models currently live under `benchmarks/model_cache/`, a different location than
  where the existing large `.mat` models (S84/S85) are configured to be found; reconciling this
  file-location detail (e.g. pointing the existing model-loading configuration at the new files,
  or moving them) is a planning-level detail, not a change to what this feature delivers.
