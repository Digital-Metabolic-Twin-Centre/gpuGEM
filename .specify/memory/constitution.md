<!--
Sync Impact Report
- Version change: 1.2.0 → 1.3.0
- Added sections:
  - VII. Evidence-Gated Algorithmic Change — an algorithmic change may only be proposed on
    numerical evidence gathered from the CURRENT implementation; where that evidence does not
    exist the required deliverable is an instrumentation change to the existing algorithm's
    diagnostic output, not a speculative algorithmic change. Includes the three sub-rules that
    the specs/013-cobra-model-lifting post-mortem showed were missing: evidence about outputs
    (not only inputs), post-conditions measured over the whole object and able to fail, and
    every transform reporting what it did NOT do.
  - VIII. Cross-Language Translation Parity (NON-NEGOTIABLE) — a MATLAB↔Python translation MUST
    be validated by executing BOTH implementations and diffing their outputs field-by-field /
    element-by-element (models) or elementwise within tolerance (solutions). Traceability review
    and same-language before/after comparison are explicitly NOT substitutes. If the machine
    cannot run both toolchains the task FAILS; the feature MUST NOT be merged or pushed.
- Modified principles: III. Test Coverage for Numerical Behavior — `gpugem/lifting.py` added to
  the covered-file list (the module was created 2026-08-21, after this constitution's previous
  amendment, and was therefore never brought under the rule).
- Modified sections: Development Workflow — two new gates (Principle VII evidence/instrumentation
  gate; Principle VIII parity gate, which explicitly overrides any spec-level Assumption that
  proposes an unavailable-toolchain substitution).
- Removed sections: none
- Templates requiring updates:
  - .specify/templates/plan-template.md ✅ no change needed (Constitution Check gate is generic, reads this file at plan time)
  - .specify/templates/spec-template.md ⚠ pending — an "Evidence" subsection (measured-before /
    predicted-after) should become a required part of Phase 0 research output
  - .specify/templates/tasks-template.md ⚠ pending — add an instrumentation ([DIAG]) task type,
    and a parity-check task type that cannot be marked complete on an unequipped machine
  - .claude/skills/*/SKILL.md ✅ no change needed (generic, agent-agnostic)
  - CLAUDE.md ✅ added at repo root — carries Principles VII/VIII outside the /speckit-plan gate,
    which previously left ad-hoc (non-speckit) work unbound by this file
  - README.md / benchmarks/README.md ✅ no change needed (no principle-specific references found)
- Follow-up TODOs:
  - gpugem/lifting.py: LiftingMapping to record rows that met the badly-scaled criterion but were
    left unchanged, with reason (Principle VII, third bullet)
  - benchmarks/run_model_lifting_validation.py: scale_report to measure max|coef| over the whole
    matrix (skipped rows and auxiliary rows included) and gate the exit code on it
    (Principle VII, second bullet)
-->

# gpuGEM Constitution

## Core Principles

### I. Correctness-Validated Defaults (NON-NEGOTIABLE)
Every default solver setting shipped in `gpugem/_defaults.py` MUST be backed by a documented
benchmark showing it produces a feasible, correct solution (bounded stoichiometric residual),
not merely a fast one. A setting MUST NOT be promoted to a default based on speed alone. Any
change to a default MUST update the settings table and residual numbers in `README.md` in the
same change. Rationale: this project exists because out-of-the-box GPU LP solver settings have
been shown to silently produce wrong results (false-infeasible presolve, postsolve tolerance
bugs) — gpuGEM's entire value proposition is that its defaults are trustworthy where the
underlying solver's are not.

### II. Honest Status and Feasibility Reporting
`result.status` MUST faithfully reflect the underlying solver's actual status; gpuGEM MUST NOT
map a degenerate, tolerance-violating, or partially-reconstructed solution to `"Optimal"`.
`result.feasibility` diagnostics (e.g. `stoich_max_residual`) MUST be computed and attached to
every result, not gated behind opt-in logging. Rationale: this directly counters the failure mode
this project was built to work around — a solver returning `"Optimal"` while its own internal
postsolve check reported failure, with nothing surfaced to a default caller.

### III. Test Coverage for Numerical Behavior
Changes to `gpugem/solver.py`, `gpugem/scaling.py`, `gpugem/lifting.py`, or
`gpugem/_defaults.py` MUST be accompanied
by tests in `tests/` that cover both the size-based default-selection logic and the numerical
correctness of the result (feasibility/residual bounds), not just that the code runs without
raising. `pytest` (with `pytest-cov`) is the test runner of record; new solver-facing behavior
without a corresponding test MUST NOT be merged.

### IV. Minimal, COBRA-Compatible Surface
gpuGEM's public API (`solve`, `solve_cobra`, `FBASolver`, `FBAResult`) MUST stay small and mirror
COBRApy conventions (reaction ordering, sparse matrix inputs, familiar result fields) so existing
modelling workflows can adopt it with a one-line change. New public surface area MUST be justified
by an actual modelling use case (e.g. whole-body coupling constraints), not speculative
generality. Solver-internal complexity (presolve routing, precision-mode selection) MUST stay
behind the thin wrapper, not leak into the public API.

### V. Documented Known Limitations
Any solver bug, accuracy bound, or unsupported use case discovered during development (e.g. the
cuOpt PaPILO hardcoded `feastol`, the broken warm-start API, the QP/min-norm gap) MUST be recorded
in the README's "Known limitations" section rather than silently worked around or left
undocumented. A workaround MUST NOT ship without the limitation it works around being visible to
users.

### VI. Publication-Ready Figure Standards
Every figure generated under `benchmarks/figures/` MUST be suitable for direct use in a journal
submission, not only for browsing this repository. Concretely:

- **Journal compliance, verified not assumed.** Sizing, resolution, and file format MUST match
  the target journal's actual, current instructions for authors — checked directly against that
  journal's published guidelines (e.g. Oxford Academic's *Bioinformatics*: 350 dpi minimum for
  combination color+line art, sized to fit a single 86 mm or double 178 mm print column), never
  copied from a different journal's conventions or guessed from general habit.
- **Colorblind-safe by computation.** Categorical or ordinal color assignments MUST be validated
  for color-vision-deficiency distinguishability via a computable check (e.g. CVD-simulated color
  distance), never chosen or approved by eye.
- **Professional, print-legible text.** All labels, legends, and axis titles MUST remain legible
  at the figure's *final print size*, not only at its working/screen size, and MUST use
  professional, publication-appropriate phrasing — no baked-in debug captions, internal setting
  names, or project-jargon a reader outside the project wouldn't recognize.
- **Captions live in the manuscript, not the image.** Figure titles, descriptive subtitles, and
  caveats belong in the manuscript's external figure caption, per standard journal convention —
  they MUST NOT be rendered into the image itself for a publication-track figure.
- **PDF is the required vector copy for publication.** PDF, not EPS, is this project's vector
  format of choice: PDF has supported transparency groups natively since PDF 1.4 (2001), so it
  correctly preserves this project's alpha-compositing-dependent figure designs (e.g. overlapping
  semi-transparent series), whereas EPS/PostScript has no native transparency support and silently
  renders partially-transparent artists fully opaque, changing what the figure shows. This does
  not relax the journal-compliance bullet above — the target journal's actual, current guidelines
  are still checked first, and if that journal explicitly accepts (or requires) PDF, ship it
  directly. If a specific target journal explicitly requires EPS instead of PDF, do not export a
  plain EPS and let the transparency silently flatten wrong; instead either (a) rasterize only the
  alpha-dependent artists (matplotlib `rasterized=True` per-artist), keeping text, axes, and the
  legend as true vector paths within the EPS, or (b) ship a high-resolution raster alternative
  (e.g. TIFF at that journal's required DPI) with the limitation documented next to the figure.

Rationale: a figure that is only readable, accessible, or correctly composited on a screen during
development is not the same deliverable as one that survives being printed, photocopied in
grayscale, or viewed by a colorblind reader. This project holds figure correctness to the same
standard as solver correctness (Principle I) — a wrong or inaccessible figure misrepresents the
same underlying science a wrong solver default would.

### VII. Evidence-Gated Algorithmic Change
An algorithmic change MUST NOT be proposed, planned, or implemented without numerical evidence —
gathered by running the *current* implementation on this project's real data — that the change is
warranted. Where that evidence does not yet exist, the required deliverable is an
**instrumentation change to the existing algorithm's diagnostic output**, sufficient to decide
which change would be most beneficial, NOT a speculative algorithmic change. Concretely:

- **Evidence about outputs, not only inputs.** Measuring what an algorithm *will* act on (e.g.
  how many rows exceed a threshold) is necessary but NOT sufficient evidence. Every transform
  MUST also be measured on what it actually *produced*. A design decision justified only by
  input statistics is unsupported.
- **Post-conditions MUST be measured over the whole object, and MUST be able to fail.** A
  post-condition check MUST be computed over every element of the transformed object — including
  elements the transform deliberately skipped and any auxiliary structure the transform itself
  created — never only over the elements the transform touched. A check whose scope makes failure
  impossible is not a check. A post-condition failure MUST produce a non-zero exit code or a
  failing test, never a recorded boolean that no caller gates on.
- **Every transform MUST report what it did NOT do.** A transform's returned mapping/metadata
  MUST record the elements that met its in-scope ("badly-scaled", "candidate", …) criterion but
  were nonetheless left unchanged, together with the reason, so coverage gaps are visible from
  the transform's own output rather than needing to be re-derived by a reader.

Rationale: this principle exists because it was violated. `specs/013-cobra-model-lifting`
gathered genuine input-side evidence (research.md R2 counted exactly which S85 rows the transform
would select) but never measured the result, and its `scale_report` inspected only the rows it had
lifted — so it reported `coupling_fully_corrected: true` on a model where 37,772 coefficients
above the threshold survived untouched, and the specified hard-failure gate (tasks.md T022)
shipped as a boolean nothing gated on. Evidence about inputs plus a check that cannot fail is
indistinguishable from no validation at all.

### VIII. Cross-Language Translation Parity (NON-NEGOTIABLE)
When code is translated between MATLAB and Python (in either direction), the translation MUST be
validated by **executing both implementations and comparing their actual outputs**. Traceable
line-by-line correspondence to the source, algebraic self-consistency tests, and same-language
before/after comparisons are all valuable, but they are explicitly NOT substitutes for, and MUST
NOT be recorded as satisfying, this requirement.

- **If the output is a genome-scale model**, the two implementations' models MUST be compared
  field by field and element by element: every matrix (`S`, `C`, `E`, `D`, …) compared on shape,
  sparsity pattern, and every stored value; every vector (`b`, `c`, `lb`, `ub`, `d`, `csense`,
  `dsense`, `rxns`, `mets`, …) compared elementwise; and any field present in one model but
  absent from the other reported as a difference. Aggregate summaries (nnz counts, min/max
  coefficient ranges, row counts) are reporting aids only — they MUST NOT stand in for the
  elementwise comparison.
- **If the output is a solution**, the two implementations' solutions MUST be compared against
  each other: solver status, objective value, and the full flux/variable vector elementwise,
  within this project's established correctness tolerance. Matching objectives alone are NOT
  sufficient.
- **No environment, no pass.** If the machine running the check cannot execute one of the two
  languages or toolchains, the comparison task MUST be recorded as **FAILED** — never skipped,
  waived, marked complete, or substituted with a different form of validation. The feature MUST
  NOT be merged or pushed until the comparison has actually been run on a machine where both are
  available. A spec-level Assumption asserting that a toolchain is unavailable does NOT relax
  this requirement; it only identifies work that is not yet done.

Rationale: `specs/013-cobra-model-lifting` recorded, as an Assumption, that no MATLAB/Octave
installation was available, and substituted traceability review plus Python-vs-Python
solve comparison. That substitution was accepted and the feature shipped. It was later found by
direct comparison against the MATLAB pipeline's own exported models that the two implementations
lift substantially different parts of the problem — the MATLAB side lifting 103,571 coupling rows
(including 33,591 that `reformulate.m`'s own pattern excludes) and leaving the `S` block
untouched, while the Python port lifted 68,259 coupling rows plus 242 mass-balance rows. No layer
of the accepted validation strategy could have detected this, because no layer ever looked at the
MATLAB output. A translation is only proven equivalent by comparing what the two implementations
actually produce.

## Quality Standards

- Code style and line length are enforced via `ruff` (`line-length = 100`, configured in
  `pyproject.toml`); `ruff` MUST pass before merge.
- Python compatibility floor is 3.10, matching `requires-python` in `pyproject.toml`; new code
  MUST NOT use syntax or stdlib features beyond that floor.
- Optional dependencies (`cobra`, `dev`) MUST stay optional — the core `solve`/`FBASolver` path
  MUST work with only `numpy`, `scipy`, and `cuopt-cu12` installed.

## Development Workflow

- Spec-Driven Development (this toolkit) is used for new features: `/speckit-specify` →
  `/speckit-plan` → `/speckit-tasks` → `/speckit-implement`, with `/speckit-clarify` and
  `/speckit-analyze` used for any feature touching solver defaults or the public API.
- Benchmark evidence (timing, residuals) for any new or changed default MUST be captured in the
  feature's spec or plan artifacts before `/speckit-implement`, not reconstructed after the fact.
- **Evidence/instrumentation gate (Principle VII).** A feature's Phase 0 research MUST record
  both what was *measured before* (the current implementation's behavior on real data) and a
  falsifiable *predicted after* (the post-condition the change is expected to establish), which
  a later task MUST then verify over the whole object. Where the evidence needed to choose
  between algorithmic options does not exist, the correct next task is an instrumentation task
  against the existing algorithm — not a chosen algorithmic change.
- **Parity gate (Principle VIII).** Any feature that translates code between MATLAB and Python
  MUST include a task that executes both implementations and diffs their outputs, and that task
  MUST NOT be marked complete on a machine lacking either toolchain. This gate overrides any
  spec-level Assumption proposing a substitute form of validation.
- Ad-hoc (non-`/speckit`) work is bound by this constitution too; `CLAUDE.md` at the repo root
  carries the operative rules for sessions that never reach the `/speckit-plan` gate.

## Governance

This constitution supersedes ad hoc practice for gpuGEM development. Amendments are made by
editing this file directly, incrementing `CONSTITUTION_VERSION` per semantic versioning (MAJOR:
backward-incompatible principle removal/redefinition; MINOR: new principle or materially expanded
guidance; PATCH: wording/clarification only), and updating `Last Amended`. Any plan produced by
`/speckit-plan` MUST verify its "Constitution Check" gate against the current version of this
file; unresolved violations MUST be justified in the plan's Complexity Tracking section or the
plan MUST be revised.

**Version**: 1.3.0 | **Ratified**: 2026-07-06 | **Last Amended**: 2026-09-10
