# Feature Specification: Add Harvetta to the Benchmark Suite and Commit Model Files

**Feature Branch**: `008-add-harvetta-benchmark`

**Created**: 2026-08-04

**Status**: Draft

**Input**: User description: "I've added the harveta model to the model cache. Also add the
Harvetta to the benchmarks run the same gurobi and cuOpt with both options. Keep the models in
this folder and remove the folder from gitignore so that we store the models as benchmarks and way
to reproduce the results at the repository"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Get correctness-gated cuOpt vs Gurobi results for Harvetta (Priority: P1)

A researcher who has added the Harvetta whole-body model (the female counterpart to the
already-benchmarked Harvey male whole-body model) to the project's model cache wants it solved
with both cuOpt (this project's shipped defaults) and Gurobi on the identical LP, checked against
the same correctness gate already trusted for every other model in the cross-scale comparison.

**Why this priority**: This is the foundational step — without a correctness-gated result for
Harvetta, there is nothing to add to either existing comparison, and no basis for trusting any
number that might be shown for it.

**Independent Test**: Can be fully tested by running the existing cross-scale benchmark tooling
against Harvetta and confirming a result (solve time, objective, solver status, feasibility
residual, pass/fail against the correctness gate) is produced for both cuOpt and Gurobi, in the
same form already used for every other model.

**Acceptance Scenarios**:

1. **Given** the Harvetta model file already present in the project's model cache, **when** the
   existing cross-scale benchmark tooling is run against it, **then** both cuOpt and Gurobi solve
   the identical LP and a result is recorded for each, gated by the same feasibility-residual
   tolerance, solver-status check, and cross-solver objective-agreement check already used for
   every other model.
2. **Given** Harvetta's result has been produced, **when** every other model's already-recorded
   result is checked afterward, **then** it is unchanged from before this feature — no existing
   result was re-solved or altered as a side effect.

---

### User Story 2 - See Harvetta's per_constraint_residual=0 trade-off alongside every other model (Priority: P1)

Having a baseline cuOpt-vs-Gurobi result, the researcher wants Harvetta covered by the project's
existing three-configuration trade-off comparison (cuOpt shipped default, cuOpt with
`per_constraint_residual=0`, Gurobi) and the two violation-distribution figures, exactly the way
every other whole-body/microbiome model already is.

**Why this priority**: Equal priority to User Story 1 — the user's request explicitly asks for
"both options" (both `per_constraint_residual` configurations), and this is the comparison that
makes a new whole-body model's correctness/speed trade-off legible, not just its baseline numbers.

**Independent Test**: Can be fully tested by running the existing trade-off benchmark tooling for
Harvetta and confirming its result includes all three configurations plus full per-row violation
histograms (mass-balance equations and, if Harvetta has a coupling block, coupling constraints),
and that regenerating the existing figures includes Harvetta.

**Acceptance Scenarios**:

1. **Given** Harvetta's baseline cuOpt/Gurobi result exists, **when** the existing trade-off
   benchmark tooling is run for Harvetta, **then** a result is produced with all three
   configurations and full per-row violation histogram data, in the same form already used for
   every other model.
2. **Given** Harvetta's trade-off result exists, **when** the runtime-comparison and
   violation-distribution figures are regenerated, **then** Harvetta appears in all of them,
   correctly positioned by model size, without disturbing any other model's appearance.

---

### User Story 3 - Reproduce every benchmarked model directly from the repository (Priority: P2)

A researcher who clones this repository wants every model file the benchmark suite depends on —
not only Harvetta's — available directly from the checkout, with no separate download, external
path configuration, or manual copy step, so the full suite (code, results, and the models that
produced them) is reproducible from the repository alone.

**Why this priority**: Lower priority than getting Harvetta's own numbers right, but it is an
explicit, deliberate part of the request and changes this project's reproducibility posture for
every model already in `benchmarks/model_cache/`, not only the new one.

**Independent Test**: Can be fully tested by cloning the repository fresh and confirming every
`.mat`/`.xml` model file the benchmark suite's registry references is present in the checkout
without any additional download or environment-variable-configured external path.

**Acceptance Scenarios**:

1. **Given** a fresh checkout of the repository, **when** the benchmark suite's model cache
   directory is inspected, **then** every model file currently in it — Harvetta's and every
   previously-added model's — is present, not excluded by version control.
2. **Given** the model cache directory's files are now tracked, **when** the repository's ignore
   rules are inspected, **then** they no longer exclude this directory's model files.

---

### Edge Cases

- What happens if Harvetta's solve fails the correctness gate (non-optimal status, feasibility
  residual beyond tolerance, or cross-solver objective disagreement)? It MUST be recorded and
  clearly marked as failed, exactly like any other model — not silently included in either
  comparison as if it had passed.
- What happens if Harvetta's `.mat` file structure (e.g. which reaction is the objective) differs
  from what the existing whole-body model (Harvey) uses? The system MUST fail with a clear,
  specific error rather than silently defaulting to the wrong objective or a wrong dimension.
- What happens to the already-committed small BiGG model files (`e_coli_core.xml`, `iML1515.xml`),
  which are already tracked by version control today? They are unaffected — this feature extends
  tracking to the remaining, currently-untracked model files in the same directory.
- What happens to models that are not yet, and still won't be, part of the registered benchmark
  suite (if any other files happen to sit in the model cache directory)? Only files the benchmark
  suite's registry actually references are in scope for this feature's tracking change; an
  incidental, unreferenced file being present is not this feature's concern.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST register Harvetta as a model in the benchmark suite, sourced from
  its already-present location in the project's model cache directory.
- **FR-002**: The system MUST solve Harvetta with both cuOpt (shipped defaults) and Gurobi on the
  identical LP, using the existing cross-scale benchmark tooling, gated by the same correctness
  checks (solver status, feasibility-residual tolerance, cross-solver objective agreement) already
  applied to every other model.
- **FR-003**: The system MUST solve Harvetta under the existing three-configuration trade-off
  comparison (cuOpt shipped default, cuOpt with `per_constraint_residual=0`, Gurobi), using the
  existing trade-off benchmark tooling, producing full per-row violation histogram data exactly as
  already produced for every other model.
- **FR-004**: A Harvetta solve that fails either benchmark's correctness gate MUST be recorded and
  clearly marked as failed; it MUST NOT be silently included in any comparison or figure as if it
  had passed.
- **FR-005**: The system MUST regenerate every existing comparison figure this project produces
  (the cross-scale runtime comparison, the three-configuration trade-off comparison, and both
  violation-distribution figures) so each includes Harvetta, correctly positioned by model size
  alongside every other model.
- **FR-006**: Adding Harvetta MUST NOT alter any other model's already-recorded results, in either
  benchmark, unless that model is explicitly re-run.
- **FR-007**: The project's version-control ignore rules MUST no longer exclude the benchmark
  suite's model cache directory's model files — every model file currently in that directory
  (Harvetta's and every previously-added, currently-untracked model) MUST become trackable and be
  committed to the repository.
- **FR-008**: This feature MUST NOT modify any of this project's shipped default solver settings,
  regardless of how Harvetta performs under either benchmark.

### Key Entities *(include if feature involves data)*

- **BenchmarkModel** (extended): Harvetta, represented the same way every other model already is —
  name, scale class, loader kind, source path, checksum, and dimensions (rows, columns, non-zeros).
- **SolveResult** / **ModelComparison**: unchanged in shape from the existing benchmarks — now
  populated for Harvetta across both the cross-scale and trade-off comparisons.
- **TrackedModelFile**: a model file under the benchmark suite's model cache directory that
  transitions from ignored (untracked, locally-present-only) to committed (tracked, present in
  every clone) as a result of this feature.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reader can see Harvetta's cuOpt-vs-Gurobi solve-time and correctness numbers
  alongside every other model in the existing cross-scale comparison.
- **SC-002**: A reader can see Harvetta's `per_constraint_residual=0` speed/correctness trade-off,
  including its violation distribution, alongside every other model in the existing trade-off
  comparison and both violation-distribution figures.
- **SC-003**: No previously-recorded result for any other model changes as an unintended side
  effect of onboarding Harvetta.
- **SC-004**: A fresh clone of the repository contains every model file the benchmark suite's
  registry references, with no separate download or external path configuration required to
  reproduce any of this project's benchmark results.
- **SC-005**: This project's shipped default solver behavior is unchanged after this work is
  applied.

## Assumptions

- "Harveta" in the user's request refers to Harvetta, the female whole-body counterpart to the
  already-benchmarked Harvey (male) model, already placed by the user at
  `benchmarks/model_cache/Harvetta_1_03d.mat`.
- Harvetta is classified as a whole-body model (the same scale class as Harvey), not a microbiome
  model, since it is generated by the same whole-body reconstruction family as Harvey rather than
  the per-individual microbiome (mWBM) models.
- "Run the same Gurobi and cuOpt with both options" means: run Harvetta through both of this
  project's existing comparisons — the baseline cross-scale cuOpt-vs-Gurobi comparison, and the
  three-configuration trade-off comparison covering both `per_constraint_residual` settings — not
  a request to re-run or re-solve any already-benchmarked model.
- "Remove the folder from gitignore" refers to the version-control ignore rule that currently
  excludes `.mat` files under the benchmark suite's model cache directory. Removing it affects
  every currently-untracked model file in that directory, not only Harvetta's — the four
  microbiome models added in the prior feature (S9, S15, S23, S83; both their plain and "_lifted"
  variants) are currently untracked specifically because of their size (their combined size is in
  the hundreds of megabytes) and would become committed alongside Harvetta. This is a deliberate,
  explicit reversal of that prior size-driven exclusion, made because the user now prioritizes
  full reproducibility from the repository over repository size — not an oversight, and it is
  called out explicitly here because of its significant, hard-to-reverse effect on repository size
  and clone time.
- Only Harvetta's plain `.mat` file is in scope for the benchmark registry (matching the existing
  convention of not using "_lifted" variants); a "_lifted" variant becoming trackable as a side
  effect of the broader ignore-rule change (if one exists or is later added) does not itself make
  it part of the registered benchmark suite.
- The small BiGG model files already tracked today (`e_coli_core.xml`, `iML1515.xml`) are
  unaffected; this feature's tracking change is additive for the remaining files.
- Harvetta is solved with the same repeat count and per-model time-limit convention already used
  by both existing benchmarks, for consistency with every other model's results.
