# Feature Specification: Version x Lifting Runtime Comparison

**Feature Branch**: `014-version-lifting-runtime-comparison`

**Created**: 2026-08-21

**Status**: Draft

**Input**: User description: "for the runtime comparison now also add the runtime for the newer version of cuOpt for original models and ANOTHER set of runs with the newer version of cuOpt for lifted models. Add these extra bars beside the already recorded ones in the figure and document the results as before. Only continue to up to S85 because rest of the microbiome models have the same property as the S85. So the models would be ecoli_core, iML1515, Harvey, Harvetta, S84 and S85"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See every combination of cuOpt version and lifting side by side (Priority: P1)

A researcher who already knows two separate facts — upgrading cuOpt's version measurably changes
runtime (established for S85), and lifting a badly-scaled model is a validated, correct
transformation whose effect on runtime was deliberately left unmeasured — wants both questions
answered together, for every model already in the project's main runtime comparison up through
S85: does cuOpt get faster on the *original* model with a newer version, does lifting itself help,
and does that answer change once the newer version is factored in? Today's figure only shows one
cuOpt configuration (shipped default settings, current version, unlifted) next to Gurobi; the
researcher wants the three missing configurations added next to it, not shown separately.

**Why this priority**: This is the entire point of the feature — without all four cuOpt
configurations sitting next to each other for the same model, there is no way to actually compare
them, which is the whole reason this comparison is being built.

**Independent Test**: Can be fully tested by confirming that, for every one of the six specified
models, a runtime figure shows cuOpt's shipped-default solve time under all four combinations of
{current version, newer version} x {unlifted, lifted}, alongside the already-existing Gurobi
reference bar, all in the same figure.

**Acceptance Scenarios**:

1. **Given** the existing runtime comparison already has a bar for Gurobi and a bar for cuOpt
   (current version, unlifted) for each of the six models, **when** this feature's work is
   applied, **then** three additional bars appear for each of those same six models: cuOpt (newer
   version, unlifted), cuOpt (current version, lifted), and cuOpt (newer version, lifted) — placed
   beside the existing bars, not in a separate figure.
2. **Given** a model and configuration combination whose result already exists from prior work
   (e.g. a model already solved lifted under the current cuOpt version), **when** this feature
   runs, **then** that existing, already-verified result is reused rather than solved again from
   scratch.
3. **Given** the four microbiome/whole-body models beyond S85 that this project's benchmark suite
   already covers, **when** this comparison is built, **then** none of them are included — only
   e_coli_core, iML1515, Harvey, Harvetta, S84, and S85 appear, matching the explicit scope
   decision that the remaining microbiome models share S85's relevant properties.

---

### User Story 2 - Never plot a number that hasn't passed the correctness gate (Priority: P1)

Because one of the four configurations (lifted, current cuOpt version) is already known, from
prior work, to fail this project's own correctness tolerance on at least one model (S85), the
researcher needs every new number in the comparison to go through the same correctness check
everything else in this project goes through — and any number that fails must be visibly marked as
failed on the figure and in the written results, never quietly plotted as if it were a normal,
trustworthy measurement.

**Why this priority**: Equal in importance to User Story 1 — a runtime comparison that silently
plots an unverified or known-incorrect result would directly contradict this project's own
foundational premise (Constitution Principle I: no number is reported on speed alone, correctness
comes first) and would actively mislead a reader who doesn't already know about the prior finding.

**Independent Test**: Can be fully tested by confirming that every one of the newly-added bars has
a recorded pass/fail correctness outcome, and that any bar corresponding to a combination already
known to fail correctness (or newly found to fail it) is visibly, unambiguously marked as failed
rather than shown as a normal bar.

**Acceptance Scenarios**:

1. **Given** a (model, version, lifted) combination that is solved as part of this feature,
   **when** its result is obtained, **then** it is checked against this project's existing
   correctness gate (objective agreement with Gurobi, feasibility residual within tolerance)
   before being reported.
2. **Given** a combination that fails that check, **when** the figure and documentation are
   produced, **then** that bar is visibly marked as failed (matching this project's existing
   convention for a failed bar) rather than omitted or plotted as if valid.
3. **Given** the already-known failing case (S85, lifted, current cuOpt version, from prior work),
   **when** this feature reuses that existing result, **then** its already-recorded failure status
   is carried through and shown, not silently dropped or re-interpreted as a pass.

---

### User Story 3 - Read the answer without opening a results file (Priority: P2)

A researcher (or a reader of this project's documentation) wants to know, for each model, which of
the four cuOpt configurations is fastest, and whether lifting or upgrading (or both) actually
helps — described in the same narrative style this project already uses for every other benchmark
finding — without having to open individual JSON result files themselves.

**Why this priority**: Secondary to actually having the data (User Stories 1-2) — this is about
making the finding usable and consistent with how every other benchmark in this project is
already documented, not about producing the data itself.

**Independent Test**: Can be fully tested by confirming the project's existing benchmarks
documentation gains a section, in the same style as every other benchmark section, that states in
plain language which configuration is fastest for each of the six models and highlights any
correctness failures.

**Acceptance Scenarios**:

1. **Given** the completed comparison, **when** the documentation is written, **then** it follows
   the same narrative + summary style already established by every prior benchmark section in this
   project's README.
2. **Given** a model where lifting or the version upgrade doesn't change the picture (e.g. a small
   model where lifting is already known to be a no-op), **when** the documentation is written,
   **then** that is stated plainly rather than implied or omitted.

---

### Edge Cases

- A (version, lifted) combination fails the correctness gate for a model — shown visibly as failed
  on the figure and called out explicitly in the write-up (User Story 2), not hidden.
- Testing the newer cuOpt version must not disturb the shared environment every other benchmark in
  this project depends on for reproducibility.
- A model where lifting is already known to be a safe no-op (e_coli_core) still gets all four
  bars — its lifted and unlifted bars are expected to be nearly identical, not skipped as
  "nothing to show."
- A combination whose result already exists from prior work but was produced with different
  settings than this feature would otherwise use — reused only if it used the same settings this
  project already established as its lifting/version defaults; otherwise re-solved.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The comparison MUST measure cuOpt's runtime for each of six models — e_coli_core,
  iML1515, Harvey, Harvetta, S84, S85 — under four configurations: {current cuOpt version,
  unlifted}, {newer cuOpt version, unlifted}, {current cuOpt version, lifted}, {newer cuOpt
  version, lifted}.
- **FR-002**: "Current" and "newer" cuOpt version MUST be the same two versions already
  established and isolated-environment-tested in this project's prior cuOpt version investigation
  — not a different or newly-chosen release.
- **FR-003**: "Lifted" MUST use this project's existing, already-validated model-lifting
  capability exactly as already implemented, with no change to the lifting algorithm or its
  existing default settings.
- **FR-004**: Every newly-measured runtime MUST be checked against this project's existing
  correctness gate (objective agreement with Gurobi, feasibility residual within tolerance) before
  being reported; a result that fails MUST be visibly marked as failed, never silently plotted or
  reported as if it passed.
- **FR-005**: The existing cuOpt-vs-Gurobi runtime figure MUST be extended with the three new
  per-model configurations placed beside the two already-recorded ones (Gurobi, current-version
  unlifted cuOpt) — the result MUST be one figure per model showing all five bars together, not a
  separate or disconnected figure.
- **FR-006**: Models beyond S85 in this project's microbiome/whole-body model set MUST NOT be
  included in this comparison.
- **FR-007**: Already-published runtime results (Gurobi; current-version, unlifted cuOpt) MUST be
  reused from existing committed results, never re-measured as part of this feature.
- **FR-008**: Where a (model, version, lifted) combination's result already exists from prior work
  under this project's established settings, it MUST be reused rather than re-solved; this
  includes carrying through an already-known correctness failure rather than re-litigating it.
- **FR-009**: The results MUST be documented in this project's existing benchmarks documentation,
  following the same narrative-plus-summary style already established by every prior benchmark
  section.

### Key Entities

- **Runtime Configuration**: One of the four (cuOpt version x lifted/unlifted) combinations
  measured for a given model; tracks which version and lifting state produced it, its solve time,
  and its correctness-gate outcome.
- **Extended Runtime Figure**: The existing cuOpt-vs-Gurobi comparison figure, extended to show
  five bars (Gurobi plus all four cuOpt configurations) per model, for the six in-scope models.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For every one of the six models, the extended figure shows exactly five bars —
  Gurobi plus all four cuOpt configurations — each traceable to a specific, committed result.
- **SC-002**: Every newly-added bar's underlying result has a recorded correctness-gate outcome,
  with any failure visibly and honestly marked, never hidden or silently omitted.
- **SC-003**: For each of the six models, the comparison states plainly whether lifting reduces
  cuOpt's runtime, and whether that answer changes between the current and newer cuOpt version —
  directly answering the question left open when model lifting was first implemented.
- **SC-004**: A reader can determine, from the figure and its accompanying documentation alone,
  which of the four cuOpt configurations is fastest for each model, without needing to open a
  results file.

## Assumptions

- "The newer version of cuOpt" refers to the same release (`26.8.0`) already investigated and
  isolated-environment-tested in this project's prior cuOpt-tuning work — testing it again here
  reuses that same isolation approach so the shared environment other benchmarks depend on is
  never disturbed.
- "Lifted" refers to this project's existing `lift=True` model-lifting capability, using its
  already-established default settings — this feature does not introduce a new lifting
  configuration to tune.
- Gurobi's bar is reused unchanged from existing results; Gurobi itself is not re-run under any
  new configuration as part of this feature — it remains the fixed correctness reference point,
  consistent with every prior benchmark in this project.
- A configuration that fails the correctness gate is still shown on the figure (visibly marked
  failed, matching this project's existing "gate fail" annotation convention), not silently
  dropped — consistent with this project's stated principle that speed is never reported without
  correctness.
