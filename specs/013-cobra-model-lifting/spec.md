# Feature Specification: Opt-In Model Lifting for Badly-Scaled LPs

**Feature Branch**: `013-cobra-model-lifting`

**Created**: 2026-08-21

**Status**: Draft

**Input**: User description: "according to the attached paper methodology for lifting model and also the cobra toolbox function "reformulate.m" write a feature for gpuGEM so that the default input when calculating the LP is not lifted but by setting that to on, it lift the model, does the LP, map the results back to the unlifted model. Benchmark the results to ensure the full consistency and exact translation of the reformulate function in the COBRA Toolbox. make sure the model's scale is correct after the lifting. We want to later benchmark to see if lifted models have lower runtimes on the solver."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Solve with lifting on, get back an unlifted-model-shaped, correct answer (Priority: P1)

A researcher solving a badly-scaled model (e.g. a whole-body or microbiome model whose
stoichiometric coefficients span many orders of magnitude) wants to opt into model lifting —
today the model is always solved in its original, badly-scaled form. When they turn lifting on,
gpuGEM should transform the model into an equivalent, better-scaled formulation, solve that
instead, and hand back a result expressed in terms of the original model's own reactions — not a
different-shaped result the researcher has to manually reinterpret.

**Why this priority**: This is the entire feature — without a working solve-lift-map-back round
trip that a caller can opt into with one setting, there is nothing to benchmark or validate.

**Independent Test**: Can be fully tested by solving the same model once with lifting off
(today's existing behavior) and once with lifting on, and confirming both produce a result
described in terms of the original model's reactions, with lifting left off by default unless
explicitly requested.

**Acceptance Scenarios**:

1. **Given** a model solved without specifying the lifting setting, **when** gpuGEM solves it,
   **then** the behavior is identical to today's (no lifting applied) — existing callers see no
   change.
2. **Given** the same model solved with lifting explicitly turned on, **when** gpuGEM solves it,
   **then** the returned result's flux values correspond one-to-one to the original model's own
   reactions (same count, same order), with no extra "helper" values the caller has to know to
   ignore.
3. **Given** lifting turned on for a model that already has coupling constraints, **when** gpuGEM
   solves it, **then** the returned result is still expressed purely in terms of the original
   model's reactions, regardless of whether the mass-balance rows, the coupling rows, both, or
   neither needed lifting for that particular model.

---

### User Story 2 - Trust that lifting doesn't change the answer (Priority: P1)

Before anyone trusts a lifted solve for real modelling work, they need proof that lifting a model
and mapping the result back gives the *same* answer as solving the model unlifted — not a
different, "close enough" answer. This must hold across models of different scale, not just one
convenient example.

**Why this priority**: Equal in priority to User Story 1 — a lifting feature that can't be trusted
to preserve the answer is worse than useless for a project whose entire premise (Constitution
Principle I) is that shipped behavior must be correctness-validated, not just fast or novel.

**Independent Test**: Can be fully tested by solving a set of models spanning small to large scale
both with and without lifting, and confirming that for every model, the lifted-and-mapped-back
result matches the unlifted result's objective and satisfies this project's existing feasibility
tolerance.

**Acceptance Scenarios**:

1. **Given** a small, well-conditioned model with no badly-scaled rows, **when** it is solved with
   lifting turned on, **then** lifting is a safe no-op (no auxiliary reactions are introduced) and
   the result matches the unlifted solve exactly.
2. **Given** a large whole-body or microbiome model with badly-scaled stoichiometric coefficients,
   **when** it is solved with lifting turned on, **then** the mapped-back result's objective and
   flux values match the unlifted solve's, within this project's existing correctness tolerance.
3. **Given** any model solved with lifting on, **when** the result is compared to the unlifted
   solve, **then** a mismatch is reported clearly as a failure — never silently accepted or
   averaged away.

---

### User Story 3 - Confirm the lifted model's scale is actually fixed, and the translation is faithful (Priority: P2)

A researcher (or a future paper reviewer) wants independent evidence that the lifting
transformation itself does what it claims — that badly-scaled coefficients are genuinely brought
within a safe range, not just restructured — and that it faithfully implements the published
method (the paper's algorithm, as realized in COBRA Toolbox's `reformulate.m`), not an
approximation of it.

**Why this priority**: Secondary to Users Stories 1-2 (a correct answer is necessary but not
sufficient on its own for a scientific claim of "faithful translation") — this is what makes the
feature citable/defensible, not just functional.

**Independent Test**: Can be fully tested by inspecting the lifted model's coefficient ranges
before and after lifting for a badly-scaled model, and by tracing the lifting logic's mass-balance
and coupling-constraint handling back to their corresponding parts of `reformulate.m`.

**Acceptance Scenarios**:

1. **Given** a badly-scaled model, **when** it is lifted, **then** every coefficient in the rows
   that were flagged as badly-scaled falls within the configured magnitude threshold after
   lifting — reported explicitly, not just asserted.
2. **Given** the lifting implementation, **when** it is reviewed, **then** its mass-balance
   transform and its coupling-constraint transform can each be traced to the corresponding section
   of `reformulate.m`, so a reviewer without access to a MATLAB/Octave installation can still
   confirm the translation is faithful.

---

### Edge Cases

- A model with no badly-scaled rows at all — lifting must be a safe no-op, not an error and not a
  spurious transformation.
- A model with coupling constraints where none match the specific structural pattern `reformulate.m`
  targets (rows with exactly two nonzero, opposite-sign entries and a zero right-hand side) — those
  rows must pass through unlifted, exactly as `reformulate.m` itself leaves them.
- The magnitude threshold is set unreasonably small or large — lifting must not crash; it may
  legitimately produce zero or many auxiliary reactions depending on the threshold, but must
  always remain well-defined.
- The model's original variable bounds include infinities, and new auxiliary variables are
  themselves unbounded — the two must not be confused or mishandled by gpuGEM's existing
  infinity-bound conventions.
- Lifting is requested on a model that has no coupling constraints at all (e.g. a plain metabolic
  model with only mass-balance rows) — only the mass-balance transform applies; nothing breaks
  because there is no coupling block.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: gpuGEM's LP-solving entry points MUST accept an explicit, opt-in lifting setting
  that defaults to off — every existing caller's behavior MUST be unchanged unless lifting is
  explicitly requested.
- **FR-002**: When lifting is enabled, gpuGEM MUST transform badly-scaled stoichiometric
  (mass-balance) rows into an equivalent formulation using auxiliary reactions whose coefficients
  are bounded by a configurable magnitude threshold, following the reformulation method described
  in the referenced paper's methodology and realized in COBRA Toolbox's `reformulate.m`.
- **FR-003**: When lifting is enabled and the model has coupling constraints, gpuGEM MUST apply
  the equivalent transform to badly-scaled coupling-constraint rows that match `reformulate.m`'s
  targeted structural pattern (exactly two nonzero, opposite-sign entries; zero right-hand side);
  rows not matching this pattern MUST be left unchanged.
- **FR-004**: The lifting transform MUST NOT alter, reorder, rescale, or remove any of the model's
  original variables (reactions) — only new auxiliary variables and constraint rows may be added.
- **FR-005**: After solving a lifted LP, gpuGEM MUST map the result back to the original model's
  variable space by direct, lossless extraction of the original variables' values — never an
  approximation or a rescaling operation.
- **FR-006**: A lifted-and-mapped-back solve MUST be verified-correct against the same model's
  unlifted solve (matching objective, feasibility residual within this project's existing
  tolerance) before lifting is considered validated for that model; a mismatch MUST be surfaced,
  never silently accepted.
- **FR-007**: gpuGEM MUST verify and report, for every badly-scaled row lifting was applied to,
  that the resulting coefficients fall within the configured magnitude threshold — confirming the
  model's scale is actually corrected, not merely restructured.
- **FR-008**: The lifting implementation MUST be validated for faithful correspondence to
  `reformulate.m`'s published algorithm (traceable, section-by-section correspondence), since no
  live MATLAB/Octave installation is available in this project's environment for a direct
  reference-output comparison.
- **FR-009**: This feature MUST NOT include or depend on a runtime/performance comparison between
  lifted and unlifted solves — that comparison is explicitly deferred to future work.
- **FR-010**: Lifting correctness MUST be validated across multiple models spanning different
  scales already present in this project's benchmark suite (at least one small, well-conditioned
  model and at least one large whole-body/microbiome model), since which rows are flagged as
  badly-scaled is data-dependent and may differ across models.

### Key Entities

- **Lifted LP**: The transformed linear program produced by applying the mass-balance and (if
  applicable) coupling-constraint lifting transforms to an original model's LP; contains every
  original variable plus new auxiliary variables, and every original constraint row plus new
  auxiliary rows.
- **Magnitude Threshold**: The configurable value controlling which coefficients are considered
  "badly-scaled" and how aggressively they are decomposed during lifting (corresponds to
  `reformulate.m`'s `BIG` parameter).
- **Mapped-Back Result**: The solution of a lifted LP restricted to the original model's own
  variables — the form every caller of gpuGEM actually sees, regardless of whether lifting was
  used internally.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For every model this feature is validated against, solving with lifting enabled and
  mapping the result back produces an outcome that is verified-correct against that same model's
  unlifted solve, with zero exceptions.
- **SC-002**: For every validated model that has badly-scaled rows, the lifted model's
  previously-badly-scaled coefficients are measurably brought within the configured magnitude
  threshold — reported as an explicit before/after comparison, not merely asserted.
- **SC-003**: Lifting is available as a single, explicit opt-in setting; every existing gpuGEM
  caller continues to behave exactly as before when the setting is left at its default.
- **SC-004**: The lifting implementation's mass-balance and coupling-constraint transforms are
  each independently traceable to their corresponding part of `reformulate.m`, so correctness can
  be reviewed without requiring a MATLAB/Octave installation.

## Assumptions

- No MATLAB/Octave installation is available in this project's environment; "exact translation" is
  validated via (a) direct, traceable algorithmic correspondence to `reformulate.m`'s published
  source and (b) solve-and-compare correctness against the unlifted model, matching this project's
  existing, already-established correctness-verification convention (residual + objective
  agreement) rather than a live MATLAB output diff.
- Lifting follows `reformulate.m`'s algorithm specifically — the paper-faithful implementation
  already confirmed (in prior work on this project) to lift both the mass-balance (`S`) block and
  the coupling (`C`) block — rather than COBRA Toolbox's separate, WBM-tailored
  `liftCouplingConstraints.m`, which only lifts coupling rows and leaves `S` untouched.
- gpuGEM's model loader already has a code path that consumes a model file with pre-computed
  lifted fields (`evars`/`E`/`D`); this feature computes those fields itself from an unlifted
  model at solve time, rather than requiring them to be pre-supplied in an externally-prepared
  file — the precise reuse of that existing representation is a planning-level decision.
- The magnitude threshold, corresponding to `reformulate.m`'s `BIG` parameter, is configurable,
  with a documented default consistent with COBRA Toolbox's own recommended range (1,000-10,000).
- Runtime/performance comparison between lifted and unlifted solves is explicit future work and is
  not a success criterion of this feature.
