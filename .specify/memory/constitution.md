<!--
Sync Impact Report
- Version change: [TEMPLATE] → 1.0.0 (initial ratification)
- Modified principles: n/a (first adoption, no prior versioned principles)
- Added sections: Core Principles (5), Quality Standards, Development Workflow, Governance
- Removed sections: none
- Templates requiring updates:
  - .specify/templates/plan-template.md ✅ no change needed (Constitution Check gate is generic, reads this file at plan time)
  - .specify/templates/spec-template.md ✅ no change needed (no constitution-specific references)
  - .specify/templates/tasks-template.md ✅ no change needed (no constitution-specific references)
  - .claude/skills/*/SKILL.md ✅ no change needed (generic, agent-agnostic)
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

**Version**: 1.0.0 | **Ratified**: 2026-07-06 | **Last Amended**: 2026-07-06
