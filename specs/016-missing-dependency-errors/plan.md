# Implementation Plan: Missing-Dependency Error Handling

**Branch**: `016-missing-dependency-errors` | **Date**: 2026-10-05 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/016-missing-dependency-errors/spec.md`

## Summary

Add one small internal registry of external dependencies and one public error class,
`gpugem.DependencyError`. Every place that today does a bare `import cuopt` / `import cobra` /
`import gurobipy` / `import highspy` / `nvidia-smi` / `matlab` call goes through the registry, so a
missing, broken, too-old or GPU-less environment yields a message that says what is wrong, why it is
needed and the exact remedy (spec FR-001–FR-004). `import gpugem` stays solver-free (FR-005). A
whole-repo AST scan test fails if any external import is not in the registry (SC-002), so coverage
is measured over the whole codebase and can go red (Constitution VII rule 2). No solver behaviour,
default, or numerical result changes.

## Technical Context

**Language/Version**: Python ≥ 3.10 (dev machine: 3.12.3)

**Primary Dependencies**: `numpy`, `scipy`, `cuopt-cu12>=26.6.0` (hard); `cobra` (optional extra);
benchmark-only: `gurobipy`, `highspy`, `pandas`, `matplotlib`; tools: `nvidia-smi`. (`matlab` was dropped: no Python code invokes it, see inventory.md.)
No dependency added or promoted.

**Storage**: N/A (benchmark JSON gains `*_unavailable_reason` fields, see data-model.md)

**Testing**: `python -m pytest tests/ -q`; `ruff check` (line-length 100). Missing-dependency paths
are simulated by blocking imports (`sys.modules[name] = None` via monkeypatch), so they run with no GPU.

**Target Platform**: Linux, pip-based environments

**Project Type**: Python library + benchmark scripts

**Performance Goals**: Dependency check adds no measurable cost per solve (result cached after first
successful check; SC-005 requires identical results on an equipped machine).

**Constraints**: `import gpugem` must work without cuOpt; original exception chained (`__cause__`);
message ASCII-only and terminal-printable.

**Scale/Scope**: ~50 benchmark scripts, 8 package modules, 15 test files; 22 `except Exception`
sites in `gpugem/` + `benchmarks/`, most of them silent (see research.md R1).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design — unchanged.*

| Principle | Status | Note |
|-----------|--------|------|
| I Correctness-validated defaults | N/A | No default changed. |
| II Honest status | PASS | Dependency failure raises; never returned as a result status. Successful path untouched. |
| III Test coverage | PASS | `solver.py` is modified → tests required: error-path tests plus the existing numerical tests must still pass (equipped machine). |
| IV Minimal surface | PASS, justified | One new public name, `DependencyError`, exported because callers must be able to catch it (FR-001). Registry/helpers stay private (`gpugem._deps`). |
| V Known limitations | PASS | README gets dependency/troubleshooting section; unverified GPU-error classification recorded as a limitation (R3). |
| VI Figures | N/A | No figure changes. Figure scripts only get an import guard. |
| VII Evidence-gated change | PASS | Not algorithmic. Inventory in R1 was measured on the repo and this machine. The inventory test scans the whole repo, including files it does not touch, and fails the suite. It reports exemptions explicitly. |
| VIII Translation parity | N/A | No MATLAB↔Python translation altered. The MATLAB tool check only detects absence. |

No violations; Complexity Tracking not needed.

## Project Structure

### Documentation (this feature)

```text
specs/016-missing-dependency-errors/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── dependency-errors.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
gpugem/
├── _deps.py             # NEW: registry, require(), check_gpu(), DependencyError
├── __init__.py          # export DependencyError
├── solver.py            # route cuopt import through require()
├── loaders.py           # route cobra / scipy.io through require(); .mat read errors guided
└── solve_cobra.py       # inherits via loaders

benchmarks/
├── _deps.py             # NEW: require_or_exit() for scripts, optional_info() for metadata
├── solve.py, run_highs_baseline.py, run_objective_sweep.py, run_benchmark.py,
│   run_objective_panel.py, models.py, solver_mode_variants.py, _*_worker.py,
│   run_*_comparison.py, make_*.py          # guard at top of main()
└── (subprocess runners surface child stderr guidance)

tests/
├── test_dependency_errors.py    # NEW: per-dependency simulated absent/broken/old/no-GPU
└── test_dependency_inventory.py # NEW: repo-wide AST scan vs registry; pyproject sync

README.md                # Dependencies + Troubleshooting; Known limitations entry
```

**Structure Decision**: single existing project layout; two small new modules (package-private
registry, benchmark-side wrapper) rather than a new package, to keep the public surface minimal
(Principle IV).
