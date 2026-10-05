# Research: Missing-Dependency Error Handling

## R1 — Evidence: current state of the repo and this machine

Measured on this machine (Python 3.12.3) by `python -c "import X"` and a repo-wide import grep:

| Dependency | Present here | Role | Used in |
|---|---|---|---|
| numpy, scipy | yes | hard | everywhere |
| cuopt | **NO** | hard | `gpugem/solver.py:118` (bare import inside `solve`), `benchmarks/{run_benchmark,run_objective_panel,run_objective_sweep,solver_mode_variants,_cuopt_tuning_worker,_version_lifting_worker}.py`, `tests/test_cuopt_tuning.py` |
| cobra | yes | optional | `gpugem/loaders.py:31`, `gpugem/solver.py` docs, `benchmarks/models.py:76`, `tests/test_lifting.py` |
| gurobipy | **NO** | benchmark | `benchmarks/{solve,run_benchmark,run_objective_panel,run_objective_sweep}.py` |
| highspy | **NO** | benchmark | `benchmarks/run_highs_baseline.py` (4 separate function-local imports) |
| pandas, matplotlib | yes | benchmark | `make_*.py`, `aggregate_*`, `run_*_comparison.py` |
| pytest | **NO** | dev | all tests |
| h5py | NO | not imported anywhere | — (no entry needed) |
| nvidia-smi | not on PATH | tool | `run_objective_sweep.py` (inside blanket `except Exception`) |
| matlab | `/usr/local/bin/matlab` | tool | `run_matlab_python_lifting_comparison.py` (subprocess) |

Consequences:
- This machine has no cuOpt, so **GPU-path behaviour cannot be observed here**. Everything about
  real cuOpt failure modes (R3) is therefore unmeasured on this machine.
- Even the test runner (`pytest`) is absent: the quickstart must install the dev extra first.
- `import cuopt` appears at call time in `solver.py`, so `import gpugem` already works without
  cuOpt (FR-005 is a "preserve" requirement, and a test must pin it).
- 22 `except Exception` sites in `gpugem/`+`benchmarks/`; a crude grep finds ~17 followed by `pass`.
  Examples: `run_objective_sweep._versions()` and `_version_lifting_worker.py:63` swallow a
  missing cuOpt and record `None` with no reason. These are the SC-006 targets. The task list must
  re-audit each site individually (the grep is a lower bound, not a catalogue).

## R2 — Error type

**Decision**: one public class `gpugem.DependencyError(RuntimeError)` with attributes `dependency`,
`kind` (`not_installed | broken | version | no_gpu | license | tool_missing | network`),
`detected`, `required`, `remedy`; `__cause__` chained.

**Rationale**: callers need one thing to catch (FR-001). `RuntimeError` base because `no_gpu` and
`license` are not import problems.

**Alternatives**: subclass `ImportError` (wrong for GPU/licence kinds; also hides that the package
is installed); one class per kind (more public surface, violates Principle IV); plain `RuntimeError`
with text only (not testable, not distinguishable).

## R3 — Classifying cuOpt failures

**Decision**: classify by *where* the failure occurs, not by message text:
`ModuleNotFoundError` for `cuopt` → `not_installed`; any other exception during import (e.g.
`ImportError`, `OSError` for a shared library) → `broken` with cause chained; installed version
below minimum → `version`; failure of a cheap CUDA/device probe before solving → `no_gpu`.

**Implementation note (differs from the first draft of this section)**: instead of probing the
device before every solve (a subprocess per call), the code diagnoses *after* a failure:
`gpu_evidence()` runs only when cuOpt's import or `Solve` raises, reports `no_gpu` only on positive
evidence (`nvidia-smi` fails / lists no GPU, or is absent with no `/dev/nvidia*`), and otherwise
re-raises the original exception unchanged. This adds zero cost to successful solves (SC-005) and
cannot relabel a genuine solver error on a machine whose GPU works.

**Open item (unmeasured)**: the exact exception cuOpt raises with no GPU/driver, and whether it
raises at import or at first solve, is **not known** and cannot be measured here. Plan: the probe
treats *any* failure of the device query as `no_gpu` only if the import itself succeeded, preserves
the cause, and the message says "GPU or driver problem suspected" and includes the cause text.
A task is added to run this on a GPU-less machine that has cuOpt installed; until it is run, that
classification is recorded in README Known limitations as unverified (Principle V). It is not
reported as passed.

**Alternatives**: parse exception messages (brittle across cuOpt releases); `nvidia-smi` as the only
probe (tool may be missing on a machine with a working GPU in a container).

## R4 — Version source of truth (FR-010)

**Decision**: minimum versions live as constants in `gpugem/_deps.py`; a test asserts they equal the
specifiers in `pyproject.toml`. Installed version read via `importlib.metadata` with the
distribution name (`cuopt-cu12`), falling back to `module.__version__`.

**Rationale**: pyproject cannot import from the package at build time; a sync test is cheaper and
cannot silently drift. **Alternative**: dynamic pyproject version from the module (adds build
complexity).

## R5 — Remedy text for CUDA variants

**Decision**: remedy uses the project's pinned distribution (`pip install "cuopt-cu12>=26.6.0"`) and
adds a pointer to NVIDIA's cuOpt install documentation for other CUDA majors. Remedy wording is
checked against the `cuopt-install` skill during implementation; tests assert the dependency name
and the substring `pip install`, not exact prose.

## R6 — Benchmark scripts

**Decision**: `benchmarks/_deps.py` exposes `require_or_exit(*names)` (prints the guided message to
stderr, exit code 3 -- 2 is already used by the benchmarks for a failed correctness gate) called at the start of each script's `main()`, before any work; and
`optional_info(name)` returning `(value, unavailable_reason)` for metadata-only probes, so skipped
metadata is recorded as `{"cuopt_version": null, "cuopt_version_unavailable_reason": "..."}`.
Import at module top level stays lazy so `pytest` can import script modules without the dependency.

**Alternatives**: top-of-file try/except in each script (50 copies); raising `DependencyError`
directly from `main` (traceback instead of a clean exit).

## R7 — Subprocess workers

**Decision**: workers run `require_or_exit` themselves; runners that already capture child output
(`run_version_lifting_comparison`, `run_matlab_python_lifting_comparison`, `run_cuopt_tuning`,
`run_solver_mode_experiment`) propagate the child's final stderr line into the run record and the
parent's exit message. The `run_version_lifting_comparison` auto-`pip install cobra` into a venv is
kept; its failure (no network, no venv module) gets a guided message.

## R8 — Coverage that can fail (Constitution VII rule 2)

**Decision**: `tests/test_dependency_inventory.py` parses every `.py` under `gpugem/`, `benchmarks/`,
`examples/`, `tests/` with `ast`, collects all top-level module names imported (including
function-local imports and `importlib.import_module` string literals), subtracts stdlib
(`sys.stdlib_module_names`) and first-party, and asserts the remainder ⊆ registry names ∪ an explicit,
justified exemption list (`pytest` for tests, `numpy`/`scipy` which are hard deps verified at
import). It also scans for `subprocess` first-arguments and `shutil.which` literals against the tool
registry. A new unregistered import therefore fails the suite. A second test fails if any
`except Exception: pass` remains in code that touches a registered dependency, unless the line carries
an `# optional-dep:` marker naming the recorded reason field.

**Limits stated up front**: AST scan cannot see dynamically constructed import names or tool names;
those are reported in the test output as "not analysable" rather than ignored.
