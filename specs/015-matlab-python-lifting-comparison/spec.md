# Feature Specification: MATLAB vs Python Lifted-Model Runtime & Fidelity Comparison

**Feature Branch**: `015-matlab-python-lifting-comparison`

**Created**: 2026-09-09

**Status**: Draft

**Input**: User description: "The purpose of this specification is to compare the run time of lifted models for the ones that are lifted using reformulate.m function in the CORBA Toolbox in MATLAB and the ones that use reformulate use the reformulate.m function in MATLAB and the ones that have been lifted usin the Python version of it. Both solved with gurobi, one in Python and one in MATLAB. This would let us know how both codes are performing in comparison to each other and how accurately they are mapped into one another and how well the lifted models are working."

## Clarifications

### Session 2026-09-09

- Q: This project's constitution (Principle VI) holds every figure under `benchmarks/figures/` to a strict publication standard (colorblind-safe validation, DPI/PDF export, journal-compliance checks). Should this comparison's persisted output be a full publication-quality figure subject to that standard, or a lighter data/summary report not held to it? → A: Full publication-quality figure, subject to Constitution Principle VI's figure standards (in addition to, not instead of, the underlying data being persisted).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See MATLAB-lifted and Python-lifted Gurobi runtimes side by side (Priority: P1)

A researcher who already has a correctness-validated Python translation of COBRA Toolbox's
`reformulate.m` (gpuGEM's own lifting feature) wants to know how that Python pipeline's Gurobi
solve time compares to lifting the same model with `reformulate.m` itself in MATLAB and solving
that with Gurobi. Today the two pipelines have never been run and timed side by side; the
researcher wants, for each model, one clear runtime figure for "lift in MATLAB, solve with
Gurobi in MATLAB" next to "lift in Python, solve with Gurobi in Python" -- both measured on the
same machine so the numbers are directly comparable.

**Why this priority**: This is the entire point of the feature -- without both pipelines actually
run and timed on the same hardware, there is no comparison to make.

**Independent Test**: Can be fully tested by confirming that, for every model in scope, a
runtime record exists showing the MATLAB-lifted-and-Gurobi-solved time and the
Python-lifted-and-Gurobi-solved time, both measured on this machine, reported together.

**Acceptance Scenarios**:

1. **Given** a model in scope, **when** it is lifted with `reformulate.m` in MATLAB and solved
   with Gurobi, **then** its solve runtime is recorded.
2. **Given** the same model, **when** it is lifted with gpuGEM's Python lifting port and solved
   with Gurobi, **then** its solve runtime is recorded using the same machine and comparable
   solver settings as the MATLAB run.
3. **Given** both runtimes for a model, **when** the comparison is produced, **then** the two
   numbers are presented together (not in separate, hard-to-cross-reference places) so a reader
   can immediately see which pipeline was faster and by how much.

---

### User Story 2 - Trust that the Python lifting port matches MATLAB's reformulate.m (Priority: P1)

Before any runtime difference is meaningful, the researcher needs evidence that the two pipelines
are actually solving *the same problem* -- that gpuGEM's Python port of `reformulate.m` produces
a lifted model and a solved result that correspond to what MATLAB's own `reformulate.m` plus
Gurobi produces for that model, not a subtly different formulation. This is a stronger check than
gpuGEM's existing lifting validation (which only compares Python-lifted results against
Python-unlifted results) -- here the reference is MATLAB's own implementation.

**Why this priority**: Equal to User Story 1 -- a runtime comparison between two pipelines that
aren't actually solving equivalent problems is meaningless, and worse, misleading.

**Independent Test**: Can be fully tested by comparing, for each model in scope, the MATLAB
pipeline's solve status and objective value against the Python pipeline's, and confirming they
agree within this project's established correctness tolerance.

**Acceptance Scenarios**:

1. **Given** a model solved by both pipelines, **when** their solve statuses are compared,
   **then** both report the same outcome (e.g. both optimal); any disagreement is reported
   clearly, never silently accepted or averaged away.
2. **Given** a model solved by both pipelines with matching status, **when** their objective
   values and mapped-back flux results are compared, **then** they agree within this project's
   established correctness tolerance.
3. **Given** a mismatch between the two pipelines for any model, **when** the comparison report
   is produced, **then** that mismatch is called out explicitly as a finding, not hidden inside an
   aggregate number.

---

### User Story 3 - A publication-quality figure documenting how well lifting is working in both pipelines (Priority: P2)

A researcher (or a future reviewer, including a journal reader) wants a single, persisted,
publication-quality figure that shows, per model: MATLAB's lifted runtime, Python's lifted
runtime, and whether the two agreed -- backed by the underlying data, without needing to re-run
either pipeline to find out.

**Why this priority**: Secondary to User Stories 1-2 (having both pipelines run and agree is what
matters most) -- this is what makes the comparison usable, citable, and reproducible after the
fact, to the same standard already required of every other benchmark figure in this project.

**Independent Test**: Can be fully tested by locating, after the comparison has been run once, a
figure (plus its underlying data) that shows every in-scope model's MATLAB runtime, Python
runtime, and agreement outcome, without re-executing MATLAB or Gurobi, and confirming the figure
meets this project's publication-figure standard (Constitution Principle VI).

**Acceptance Scenarios**:

1. **Given** the comparison has been run for all models in scope, **when** the figure is opened,
   **then** it shows, per model, both runtimes and the agreement outcome, and the underlying data
   backing the figure is also available for review.
2. **Given** a model that could not be run in one of the two pipelines (e.g. impractical local
   runtime), **when** the figure and its backing data are produced, **then** that model is listed
   as excluded with the reason, rather than silently missing.
3. **Given** the finished figure, **when** it is checked against this project's publication-figure
   standard (Constitution Principle VI), **then** it passes every applicable requirement
   (colorblind-safe color assignment, correct resolution/sizing/vector export for the project's
   target journal, print-legible labels, no baked-in captions).

---

### Edge Cases

- The MATLAB pipeline and Python pipeline report different Gurobi solve statuses for the same
  model (e.g. one optimal, one numerically troubled) -- must be surfaced as a disagreement, not
  averaged or dropped from the comparison.
- A model whose MATLAB-side lift-and-solve takes impractically long on this machine -- the model
  is documented as excluded (with reason), rather than blocking the rest of the comparison.
- The MATLAB and Python solves end up using different Gurobi settings by default (e.g. different
  method/algorithm selection) -- this must be detected and either matched or explicitly reported,
  since an unmatched setting would make the runtime comparison meaningless.
- The Python lifting port and MATLAB's `reformulate.m` produce a different number of auxiliary
  variables/rows for the same model -- this alone is not necessarily a failure (structural
  choices can legitimately differ) but must be reported as a data point, distinct from an actual
  objective/flux mismatch.
- A model that is well-conditioned enough that lifting is a no-op in both pipelines -- still must
  appear in the comparison, showing near-identical runtimes and results.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: For every model in scope, the system MUST produce a runtime measurement of lifting
  that model with `reformulate.m` in MATLAB and solving the lifted model with Gurobi, run locally
  on this machine.
- **FR-002**: For every model in scope, the system MUST produce a runtime measurement of lifting
  that same model with gpuGEM's existing Python lifting implementation and solving the lifted
  model with Gurobi, run locally on the same machine as FR-001.
- **FR-003**: The system MUST report the MATLAB-pipeline and Python-pipeline runtimes for each
  model together, so they can be directly compared model-by-model.
- **FR-004**: The system MUST compare the two pipelines' Gurobi solve status for each model and
  MUST report, explicitly, any model where the two pipelines disagree on status.
- **FR-005**: The system MUST compare the two pipelines' solved objective value and mapped-back
  flux results for each model and report whether they agree within this project's established
  correctness tolerance, as evidence that the Python lifting implementation is an accurate
  translation of `reformulate.m`.
- **FR-006**: The system MUST use matching (or explicitly documented, if unavoidably different)
  Gurobi solver settings between the MATLAB and Python solves, so that any runtime difference
  reflects the lifting-and-solve pipeline itself rather than incidental solver configuration.
- **FR-007**: The MATLAB-side lifting-and-solving MUST be carried out via a temporary, standalone
  script used only to produce this comparison's data; it MUST NOT be added as a permanent part of
  either gpuGEM's or the COBRA Toolbox repository's maintained codebase.
- **FR-008**: The Python-side lifting-and-solving MUST reuse gpuGEM's existing, already
  correctness-validated lifting implementation and Gurobi-solving path, rather than
  re-implementing lifting or solving from scratch.
- **FR-009**: The system MUST record which of the models in scope were actually compared and
  which, if any, were excluded and why, so the comparison's coverage is transparent.
- **FR-010**: The comparison's results MUST be persisted as structured data plus a
  publication-quality figure showing, per model, both pipelines' runtimes and their agreement
  outcome, so they can be reviewed without re-running either pipeline.
- **FR-011**: The comparison figure MUST meet this project's existing publication-figure standard
  (Constitution Principle VI) -- validated colorblind-safe color assignment, resolution/sizing/
  vector export matching this project's target journal, print-legible labels using
  publication-appropriate phrasing, and no baked-in captions or internal setting names -- to the
  same bar already applied to this project's other benchmark figures.

### Key Entities

- **MATLAB Lifted-and-Solved Run**: One model's `reformulate.m`-lifted linear program, solved
  with Gurobi in MATLAB on this machine; captures runtime, solve status, objective value, and
  mapped-back flux results.
- **Python Lifted-and-Solved Run**: The same model's gpuGEM-lifted linear program, solved with
  Gurobi in Python on this machine; captures the same fields as the MATLAB run.
- **Cross-Language Comparison Record**: Pairs a model's MATLAB run and Python run; captures the
  runtime difference, the status-agreement outcome, and the objective/flux agreement outcome (or
  the specific mismatch, if any).
- **Temporary MATLAB Comparison Script**: The one-off script that produces the MATLAB-side runs;
  explicitly not a permanent deliverable of any repository -- only its output data feeds this
  feature.
- **Comparison Figure**: The persisted, publication-quality figure (plus its backing data) that
  presents every in-scope model's Cross-Language Comparison Record together -- the artifact this
  feature is ultimately building toward, held to the same standard (Constitution Principle VI) as
  this project's other benchmark figures.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For every model in scope, the comparison figure shows both the
  MATLAB-lifted-and-solved runtime and the Python-lifted-and-solved runtime, measured on the same
  machine, side by side.
- **SC-002**: For every model in scope that both pipelines could solve, the two pipelines' solved
  objective values agree within this project's established correctness tolerance, with zero
  unexplained mismatches.
- **SC-003**: For every model in scope that both pipelines could solve, the two pipelines'
  mapped-back flux results agree within this project's established correctness tolerance.
- **SC-004**: 100% of models in scope have a resolved outcome in the figure and its backing data
  -- matched success, reported mismatch, or an explicitly documented exclusion reason -- with none
  silently missing.
- **SC-005**: The comparison figure and its backing data are complete enough that a reviewer can
  determine, for every model in scope, which pipeline was faster and whether the two pipelines'
  results agreed, without re-running either pipeline.
- **SC-006**: The comparison figure passes this project's publication-figure standard (Constitution
  Principle VI) -- computed colorblind-safe validation, correct resolution/sizing/vector export
  for the project's target journal, and print-legible labels -- with zero exceptions.

## Assumptions

- MATLAB, the COBRA Toolbox (including `reformulate.m`), and Gurobi are all installed and
  licensed on this machine, so both pipelines can be run locally without relying on any CI
  environment or remote server -- confirmed for this feature specifically, superseding the "no
  MATLAB available" assumption recorded for the unrelated prior feature that ported
  `reformulate.m` to Python.
- Because both pipelines run on this same local machine, their runtimes are directly comparable;
  no cross-environment caveat is needed.
- The models in scope are the same set already established for this project's lifted-model
  runtime work: `e_coli_core`, `iML1515`, `Harvey`, `Harvetta`, `S84`, and `S85` -- the remaining
  microbiome models in this project's benchmark suite are excluded because they share S85's
  relevant properties.
- Runtime is measured using this project's existing repeated-run/median convention, applied
  consistently to both the MATLAB and Python pipelines.
- Correctness/agreement tolerance for comparing objective and flux values between the two
  pipelines follows this project's already-established residual and objective tolerances used to
  validate the Python lifting implementation.
- The MATLAB-side script that produces comparison data is a temporary, throwaway artifact of this
  feature's data collection -- it is not going through, and is not subject to, either repository's
  own change-governance process, since it is never merged as permanent code.
- The comparison figure targets the same journal this project's other benchmark figures already
  target, and reuses this project's existing colorblind-validation and figure-export tooling
  rather than establishing a new, separate figure pipeline.
