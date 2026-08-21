# Implementation Plan: Opt-In Model Lifting for Badly-Scaled LPs

**Branch**: `013-cobra-model-lifting` | **Date**: 2026-08-21 | **Spec**: ./spec.md

**Input**: Feature specification from `/specs/013-cobra-model-lifting/spec.md`

## Summary

Add `gpugem/lifting.py`, a faithful Python translation of COBRA Toolbox's `reformulate.m`
(re-read in full for this feature, research.md R1-R2 document its exact mechanics including a
MATLAB-`mode()` tie-breaking subtlety that would be easy to mistranslate): badly-scaled
mass-balance rows and, separately, badly-scaled two-nonzero-opposite-sign coupling rows are
decomposed into chains of well-scaled auxiliary reactions/variables, with original variables left
untouched and always first, so mapping a lifted solution back is a literal prefix slice (research
R5) — no inverse arithmetic, unlike the external-scaling approach `specs/012-cuopt-native-tuning/`
already showed can lose accuracy through its inverse transform. Two new keyword-only parameters,
`lift: bool = False` and `lift_big: float = 1000.0`, are added to `gpugem.solve()`'s existing
signature; because `solve_cobra()` and `FBASolver` already transparently forward arbitrary
keyword arguments down to `solve()` (research R4, confirmed by direct code reading, not assumed),
every gpuGEM entry point gains lifting support from that one change. `gpugem/scaling.py` — a
different, pre-existing, already-shipped coefficient-decomposition utility — is explicitly left
untouched; research.md R3 documents exactly how and why it diverges from `reformulate.m`, so the
two are never conflated. Validated against `e_coli_core` (safe no-op case) and S85 (both
mass-balance and coupling lifting genuinely exercised, confirmed empirically in research R8).

## Technical Context

**Language/Version**: Python 3.13 (matches every other `gpugem`/`benchmarks` module in this
project)

**Primary Dependencies**: `numpy`, `scipy` (sparse matrix construction) — no new third-party
dependency. Reuses `gpugem.solver.solve`'s existing DataModel/SolverSettings/Solve wiring
unchanged apart from the new opt-in pre/post-processing step.

**Storage**: N/A — this is a pure in-memory LP transform, no new file format or persisted state.
Validation artifacts (small hand-verifiable example, e_coli_core/S85 solve-and-compare results)
follow this project's existing `tests/` and `benchmarks/results/` conventions respectively.

**Testing**: `pytest`, mandatory per Constitution Principle III (this feature touches
`gpugem/solver.py`, adding `gpugem/lifting.py`) — unit tests for the mass-balance transform, the
coupling transform, and the map-back slice (small, hand-constructed examples with known-correct
expected output, mirroring `tests/test_scaling.py`'s existing precedent for this class of
transform) plus an integration test exercising `gpugem.solve(..., lift=True)` end-to-end on
`e_coli_core`. Large-model (S85) validation runs on the GPU host per `quickstart.md`, output
committed under `benchmarks/results/model_lifting/`.

**Target Platform**: Linux GPU host with cuOpt for the S85 large-model validation run; the unit
tests themselves need no GPU (pure NumPy/SciPy transform logic).

**Project Type**: single project — this is the second feature (after
`specs/004-s85-solver-mode-experiment/`) to add a new module inside `gpugem/` itself, alongside a
`benchmarks/` validation script.

**Performance Goals**: N/A for this feature — FR-009 explicitly excludes runtime/performance
comparison from this feature's scope (deferred to future work per the user's own request).

**Constraints**: `gpugem/scaling.py` MUST NOT be modified (research R3) — it is a different,
already-shipped feature with its own tests and callers; this feature adds a parallel, separately-
named module rather than touching it. Every existing `gpugem.solve()` caller MUST see identical
behavior when `lift` is left at its default (spec FR-001/SC-003).

**Scale/Scope**: two validation models (`e_coli_core`, small/no-op case; `S85`, large/both-blocks
case, per research R8) — not the full ten-model benchmark suite, since this feature's own success
criteria are about correctness-faithfulness, not a cross-model performance survey (that's the
explicitly deferred future work).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Correctness-Validated Defaults**: PASS — `lift` defaults to `False`; lifting is never
  applied unless explicitly requested, so no shipped default's behavior changes (spec FR-001).
  Promoting `lift=True` to a shipped default for any model class is explicitly out of this
  feature's scope (would need its own separate, future benchmark-backed justification, mirroring
  how `specs/012-cuopt-native-tuning/`'s upgrade finding was scoped).
- **II. Honest Status/Feasibility Reporting**: APPLIES, addressed — `FBAResult.feasibility` under
  `lift=True` is recomputed against the *original* (unlifted) system, not the lifted one cuOpt
  actually solved (research R6) — a caller sees honest diagnostics about the model they asked to
  solve, not a different, internal one they never see.
- **III. Test Coverage for Numerical Behavior**: APPLIES — this feature adds a new `gpugem/`
  module and touches `gpugem/solver.py`'s `solve()` signature. Dedicated unit tests cover both the
  size-independent transform correctness (hand-verifiable linear-algebra checks, research R7) and
  numerical correctness end-to-end (solve-and-compare against the unlifted solve).
- **IV. Minimal, COBRA-Compatible Surface**: APPLIES, justified — two new keyword-only parameters
  on `gpugem.solve()` (`lift`, `lift_big`). Justified by this feature's own concrete need (spec
  FR-001) and kept minimal: no new parameters needed on `solve_cobra`/`FBASolver` at all (research
  R4 — they inherit it via existing keyword forwarding), and `FBAResult`'s schema is completely
  unchanged (no new field — see Phase 1 data-model.md for why the "scale is corrected" diagnostic,
  FR-007, lives in the lifting module's own return value instead, consumed by tests/benchmarks,
  not bolted onto every caller's result object).
- **V. Documented Known Limitations**: APPLIES CONDITIONALLY — if lifting is found to behave
  unexpectedly on any validated model (e.g. an S85 coupling row pattern this research didn't
  anticipate), that MUST be recorded in the README's "Known limitations" section, matching every
  prior feature's precedent.
- **VI. Publication-Ready Figure Standards**: N/A — this feature's deliverable is a correctness
  validation, not a runtime comparison; no figure is required by its own success criteria (FR-009
  explicitly excludes the performance study a figure would visualize).

No unjustified violations. One Complexity Tracking entry: two new parameters on `gpugem.solve()`
(same category of change as `specs/004-.../`'s `FBAResult.solved_by` addition — the second, not
first, precedent for touching this file).

## Project Structure

### Documentation (this feature)

```text
specs/013-cobra-model-lifting/
├── plan.md              # This file (/speckit-plan command output)
├── research.md           # Phase 0 output (/speckit-plan command) — R1-R9
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md         # Phase 1 output (/speckit-plan command)
├── contracts/            # Phase 1 output (/speckit-plan command)
└── tasks.md              # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
gpugem/
├── lifting.py                     # NEW: faithful reformulate.m port -- lift_mass_balance(),
│                                   #   lift_coupling(), LiftingMapping dataclass, map_back()
│                                   #   (prefix slice, research R5); NEVER touches
│                                   #   gpugem/scaling.py (research R3)
├── solver.py                      # MODIFIED (additive only): solve() gains lift/lift_big
│                                   #   keyword-only params, consumed before **cuopt_kwargs merge
│                                   #   (research R4); when lift=True, calls gpugem.lifting before
│                                   #   building DataModel and truncates + recomputes feasibility
│                                   #   against the ORIGINAL system after solving (research R6)
├── result.py                      # UNCHANGED -- FBAResult's existing "original variable space"
│                                   #   contract for `fluxes` already covers this feature's needs
├── scaling.py                     # UNCHANGED -- explicitly left alone (research R3)
└── __init__.py                    # MODIFIED (additive only): export lifting.py's public names,
                                     #   mirroring how scale_model/remap_fluxes are already exported

benchmarks/
├── run_model_lifting_validation.py  # NEW: solves e_coli_core and S85 both lifted and unlifted,
│                                     #   confirms verified-correct parity (spec FR-006/SC-001) and
│                                     #   reports before/after coefficient-range per model
│                                     #   (spec FR-007/SC-002)
├── results/
│   └── model_lifting/
│       └── <model>.json             # one per validated model
└── README.md                        # existing -- append a short section for this validation

tests/
└── test_lifting.py                # NEW: hand-verifiable mass-balance and coupling transform
                                     #   correctness (research R7 layer 2), map-back slice
                                     #   correctness, e_coli_core no-op case, and an integration
                                     #   test exercising gpugem.solve(..., lift=True) end-to-end
                                     #   (no GPU required except the integration test)
```

**Structure Decision**: Single project. This is the second feature to add a new `gpugem/` module
(after `specs/004-.../`'s additive `FBAResult.solved_by`) — kept strictly additive here too: one
new module, one additive parameter pair on one existing function, zero changes to
`gpugem/scaling.py` or `FBAResult`'s schema. `benchmarks/results/model_lifting/` is a new
namespace, not colliding with any prior feature's results directory.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|---------------------------------------|
| New `lift`/`lift_big` parameters on `gpugem.solve()` | Spec FR-001 requires an opt-in lifting setting on gpuGEM's LP-solving entry points; only `solve()` needs the actual change since the other two entry points already forward arbitrary kwargs (research R4) | A separate `gpugem.lift_and_solve(...)` wrapper would duplicate `solve()`'s existing DataModel/SolverSettings/Solve wiring and would not automatically extend to `solve_cobra`/`FBASolver` the way an in-`solve()` parameter does |

**Post-Phase-1 re-check**: data-model.md and contracts/ confirm the only `gpugem/`-internal
changes are the new `lifting.py` module and the additive `lift`/`lift_big` parameters — no default
value changes, no new required parameters, `FBAResult`'s schema untouched, `scaling.py` untouched.
Gate still PASSES.
