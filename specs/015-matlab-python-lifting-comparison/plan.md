# Implementation Plan: MATLAB vs Python Lifted-Model Runtime & Fidelity Comparison

**Branch**: `015-matlab-python-lifting-comparison` | **Date**: 2026-09-09 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/015-matlab-python-lifting-comparison/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Compare, for the six models already in scope for this project's lifted-model runtime work
(`e_coli_core`, `iML1515`, `Harvey`, `Harvetta`, `S84`, `S85`), the runtime and correctness of two
lift-then-solve pipelines running on this local machine: (1) lift with COBRA Toolbox's
`reformulate.m` in MATLAB, solve with Gurobi in MATLAB; (2) lift with gpuGEM's existing,
already-validated Python port (`gpugem.lift_mass_balance`/`lift_coupling`, spec 013), solve with
Gurobi in Python (`benchmarks.solve.solve_gurobi`, unchanged). The MATLAB-side lift+solve runs via
a temporary script kept entirely outside both repos' tracked trees (research.md R8); only its
per-model JSON output is committed. The Python-side pipeline is new, tracked glue assembled from
existing primitives (research.md R4) -- no changes to `gpugem`'s public API or its
numerically-sensitive modules. Results are compared model-by-model (solve status, objective, and
mapped-back flux, within this project's already-established tolerances) and published as a new
publication-quality figure (Constitution Principle VI) plus its backing CSV.

## Technical Context

**Language/Version**: Python 3.10+ (this project's existing `gpugem`/`benchmarks` stack) for every
permanently-tracked artifact; MATLAB R2025a (confirmed installed on this machine) for the
temporary, untracked comparison script only (research.md R8).

**Primary Dependencies**: `numpy`, `scipy`, `pandas`, `matplotlib` (already project dependencies,
used by every `benchmarks/make_*_figure.py`); `gurobipy` (already used by
`benchmarks/solve.py::solve_gurobi`); `gpugem.lifting` (`lift_mass_balance`, `lift_coupling`,
`map_back` -- spec 013, unchanged). No new permanent Python dependency. MATLAB-side (untracked):
COBRA Toolbox's `reformulate.m` + `changeCobraSolver`/`solveCobraLP`, and Gurobi's MATLAB
interface -- both already installed and licensed on this machine (research.md R1-R3).

**Storage**: Flat files only, matching every existing benchmark feature -- per-model JSON under
`benchmarks/results/matlab_python_lifting/`, a derived `comparison.csv`, and the figure under
`benchmarks/figures/`. No database.

**Testing**: `pytest` (`tests/test_matlab_python_lifting_comparison.py`), covering the new
Python-side lift+Gurobi glue and the pure comparison/gating logic (`CrossLanguageComparisonRow`
construction) without requiring a live Gurobi or MATLAB run -- same shape as
`test_model_lifting_validation.py`/`test_version_lifting_comparison.py`. Constitution Principle
III's literal file list (`solver.py`/`scaling.py`/`_defaults.py`) is not touched by this feature
(research.md R4), but the project's established practice of testing every benchmark's numerical
glue is still honored.

**Target Platform**: Linux, this local machine specifically -- confirmed MATLAB R2025a and Gurobi
11.0.3 both installed and licensed here (not CI, not a remote host), per the user's clarification
that runtime comparability requires matched hardware.

**Project Type**: Single project -- research benchmark suite, extending the existing
`benchmarks/` layout (not a web/mobile/service app; no contracts beyond the CLI scripts
documented in `contracts/cli-contract.md`).

**Performance Goals**: N/A as a target to hit -- this feature measures runtime, it does not
optimize it. Each Gurobi solve is bounded by this project's existing 900s time-limit convention
(research.md R5/R6).

**Constraints**: The MATLAB-side script must never become a permanent artifact of either repo
(spec FR-007, research.md R8); the two pipelines' Gurobi configuration must be matched (barrier,
`method=2`, research.md R3); the comparison figure must satisfy Constitution Principle VI in full
(FR-011/SC-006); both pipelines run on this one local machine only.

**Scale/Scope**: 6 models x 2 pipelines = 12 lift-and-solve runs (each measured per this project's
repeated-run/median convention), one derived comparison CSV, one publication-quality figure (PNG +
PDF).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies? | Assessment |
|---|---|---|
| I. Correctness-Validated Defaults | No | No change to `gpugem/_defaults.py` or any shipped default setting -- this feature only measures, it doesn't ship a new default. |
| II. Honest Status and Feasibility Reporting | Yes | `PipelineRun.status` is Gurobi's own normalized status, never remapped to a nicer-looking value (data-model.md); FR-004 requires any MATLAB/Python status disagreement to be surfaced explicitly, matching `solve_gurobi`'s existing honest-status convention. |
| III. Test Coverage for Numerical Behavior | Not triggered (file list) / honored (practice) | `gpugem/solver.py`, `scaling.py`, `_defaults.py` are unchanged (research.md R4), so the principle's literal trigger doesn't fire; this feature still adds `tests/` coverage for its new numerical glue, matching the project's actual practice on every sibling benchmark feature. |
| IV. Minimal, COBRA-Compatible Surface | Yes | No new `gpugem` public API -- only new `benchmarks/`-layer scripts reusing `lift_mass_balance`/`lift_coupling`/`map_back` exactly as already exposed. |
| V. Documented Known Limitations | Deferred to tasks | If the comparison surfaces a genuine limitation (e.g. a MATLAB/Gurobi configuration quirk), it gets recorded in `README.md`'s Known Limitations as a task-level follow-up, not a planning blocker. |
| VI. Publication-Ready Figure Standards | Yes | Directly governs FR-011/SC-006 -- the new figure must pass CVD-safe color validation, correct DPI/sizing/vector (PDF) export for this project's target journal, print-legible labels, and carry no baked-in caption (research.md R7). |

**Result**: PASS -- no violations requiring `Complexity Tracking` justification.

## Project Structure

### Documentation (this feature)

```text
specs/015-matlab-python-lifting-comparison/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md         # Phase 1 output (/speckit-plan command)
├── contracts/
│   └── cli-contract.md   # Phase 1 output (/speckit-plan command)
└── tasks.md              # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

Single project -- this feature extends gpuGEM's existing `benchmarks/` layout exactly as every
prior benchmark feature (010, 013, 014) has, with no new top-level directories:

```text
benchmarks/
├── _matlab_python_lifting_worker.py           # NEW -- Python-side: lift + solve_gurobi + map_back, one model
├── run_matlab_python_lifting_comparison.py    # NEW -- orchestrator: runs Python worker, ingests committed
│                                               #        matlab_<model>.json, builds comparison.csv
├── make_matlab_python_lifting_figure.py       # NEW -- Phase 1 figure (Constitution VI), from comparison.csv
├── solve.py                                   # UNCHANGED -- solve_gurobi reused as-is (research.md R4)
├── models.py                                  # UNCHANGED -- build_lp reused as-is (research.md R1)
├── results/
│   └── matlab_python_lifting/
│       ├── matlab/<model>.json                # committed; produced by the untracked MATLAB script (R8)
│       ├── python_<model>.json                # committed; produced by _matlab_python_lifting_worker.py
│       └── comparison.csv                     # committed; derived, regenerable from the JSON above
└── figures/
    ├── matlab_python_lifting_comparison.png   # NEW
    └── matlab_python_lifting_comparison.pdf   # NEW -- vector copy, Constitution VI

gpugem/
├── lifting.py                                 # UNCHANGED -- lift_mass_balance/lift_coupling/map_back reused
└── (solver.py, scaling.py, _defaults.py unchanged -- research.md R4)

tests/
└── test_matlab_python_lifting_comparison.py   # NEW -- pure-function comparison/gating tests, no live solver
```

(Outside both repos' tracked trees, per research.md R8: the temporary MATLAB script itself --
never committed, never part of this project structure.)

**Structure Decision**: Single project, extending `benchmarks/` in place. This mirrors spec 014's
own structure (`_version_lifting_worker.py` + `run_version_lifting_comparison.py` +
`aggregate_version_lifting_comparison.py` + `make_extended_solvetime_figure.py`) closely enough
that no new architectural pattern is introduced -- the only structural novelty is that one input
side (`matlab/<model>.json`) is produced by a process this repository never runs itself.

## Complexity Tracking

*No Constitution Check violations -- this section intentionally left empty.*
