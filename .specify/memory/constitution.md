<!--
Sync Impact Report
- Version change: 1.1.0 → 1.2.0
- Modified principles: VI. Publication-Ready Figure Standards — the vector-copy bullet now
  specifies PDF (not generic "EPS, or another vector format") as the required format, with the
  EPS fallback narrowed to two documented techniques (per-artist rasterization or a raster
  alternative) for the rare case a target journal explicitly requires EPS instead of PDF.
- Added sections: none (1.1.0's new Principle VI itself already recorded)
- Removed sections: none
- Templates requiring updates:
  - .specify/templates/plan-template.md ✅ no change needed (Constitution Check gate is generic, reads this file at plan time)
  - .specify/templates/spec-template.md ✅ no change needed (no principle-specific references)
  - .specify/templates/tasks-template.md ✅ no change needed (no principle-specific references)
  - .claude/skills/*/SKILL.md ✅ no change needed (generic, agent-agnostic)
  - README.md / benchmarks/README.md ✅ no change needed (no principle-specific references found)
- Follow-up TODOs: none
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
Changes to `gpugem/solver.py`, `gpugem/scaling.py`, or `gpugem/_defaults.py` MUST be accompanied
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

## Governance

This constitution supersedes ad hoc practice for gpuGEM development. Amendments are made by
editing this file directly, incrementing `CONSTITUTION_VERSION` per semantic versioning (MAJOR:
backward-incompatible principle removal/redefinition; MINOR: new principle or materially expanded
guidance; PATCH: wording/clarification only), and updating `Last Amended`. Any plan produced by
`/speckit-plan` MUST verify its "Constitution Check" gate against the current version of this
file; unresolved violations MUST be justified in the plan's Complexity Tracking section or the
plan MUST be revised.

**Version**: 1.2.0 | **Ratified**: 2026-07-06 | **Last Amended**: 2026-08-11
