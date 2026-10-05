# Baseline and verification record (feature 016)

All runs on the development machine: Linux, Python 3.12.3, **no cuopt, gurobipy, highspy,
nvidia-smi**; cobra, pandas, matplotlib, scipy, numpy present. pytest 9 + ruff installed in a
`--system-site-packages` venv outside the repo.

## T001 - pre-change test baseline (git HEAD + uncommitted tree at session start)

`python -m pytest tests/` -> **1 collection error + 11 failed, 125 passed** (collection error:
`tests/test_solver_mode_variants.py`, module-level `from cuopt...` import). Every failure is a
bare `ModuleNotFoundError: cuopt` / `gurobipy`:
test_cuopt_tuning (1), test_gurobi_default_benchmark (2), test_lifting (2), test_solver (6).

## T002 / T012 / T028-T032 - every `except Exception` / silent site, before and after

| Site | What it swallowed | Outcome |
|---|---|---|
| `benchmarks/run_benchmark.py:40,45,52` | gurobipy / cuopt / nvidia-smi probes -> `None`, no reason | **fixed**: `environment_info()` records `*_unavailable_reason` |
| `benchmarks/run_objective_sweep.py:42,47,54` | same | **fixed** (same helper) |
| `benchmarks/run_objective_panel.py:51,56` | gurobipy / cuopt probes | **fixed** |
| `benchmarks/_version_lifting_worker.py:65` | cuopt version probe | **fixed**: `optional_version("cuopt")`; cuopt is also required up front |
| `gpugem/solver.py:219` | `settings.set_parameter` rejection | not a dependency failure; already recorded in `rejected` and warned. Unchanged |
| `gpugem/solver.py:239,246` | cuOpt LP-stats / `get_solved_by` accessors | optional diagnostics, `None` on failure. Unchanged |
| `gpugem/solver.py:297` | exception while computing feasibility diagnostics | **in scope but left unchanged**: not a dependency failure; swallowing it means `result.feasibility` can be empty with no explanation, which touches Principle II. Recorded as an open finding, not fixed here (out of this feature's scope) |
| `benchmarks/solve.py:106` | Gurobi iteration-count attributes | optional metric. Unchanged |
| `benchmarks/_cuopt_tuning_worker.py:131,139` | cuOpt stats / solution accessors | optional diagnostics. Unchanged |
| `benchmarks/run_highs_baseline.py:64,104` | HiGHS version / `resetGlobalScheduler` | optional; highspy guaranteed present by the up-front guard. Unchanged |
| `benchmarks/run_highs_baseline.py:76` | `os.getloadavg` unsupported platform | not a dependency. Unchanged |
| `benchmarks/run_highs_baseline.py:234`, `run_block_residuals.py:170`, `_matlab_python_lifting_worker.py:102` | per-model failure recorded as `ERROR` | **changed**: `DependencyError` is now re-raised (aborts the run) instead of being recorded once per model |

## T025 - the checks can go red (Constitution VII rule 2)

New tests copied into a clean `git archive HEAD` tree (original code, nothing else changed) and run:

`test_dependency_errors.py + test_dependency_inventory.py`: **21 failed, 32 passed** on the original
code. Notably `test_no_silent_swallow_of_dependency_failures` flagged exactly these 9 sites:
`_version_lifting_worker.py:65, run_benchmark.py:40/45/52, run_objective_panel.py:51/56,
run_objective_sweep.py:42/47/54`. The same tests pass on the modified tree.
Negative controls in the suite itself: `test_scan_actually_sees_imports`,
`test_swallow_detector_can_fail`.

## T036 / T040 - after the change

`python -m pytest tests/ -q` -> **12 failed, 188 passed** (0 collection errors).
The 12 failures are the baseline's 11 plus `test_solver_mode_variants::test_all_cuopt_kwargs_are_real_parameters`,
which previously could not even be collected. All 12 need cuOpt or gurobipy; each now fails with a
guided `DependencyError` instead of a bare `ModuleNotFoundError`. No previously passing test
regressed. **These 12 are UNRUN, not passed** - they need a GPU machine (T015).
`tests/test_lifting.py`: the two cobra tests now skip with a stated reason when cobra is absent.

Lint: `ruff check --select E,F --line-length 100`: no new F-class findings; the new tests/modules
are clean. The additional E402 findings in `make_*.py` / `aggregate_*` / `run_*` follow the
repo's existing `sys.path.insert` + late-import pattern (HEAD already had E402 in the same kind
of scripts). The project's configured `ruff check` reports ~300 findings at HEAD (e.g. UP031
percent-format) - not cleaned up here.

## T041 - quickstart on this machine

1. `import gpugem` without cuopt: OK (test + manual).
2. `gpugem.solve(...)` -> `DependencyError: cuopt is not installed. Needed for ... Fix: pip install "cuopt-cu12>=26.6.0" ...`.
3. Tests: pass (see above).
4. `run_highs_baseline.py`, `run_benchmark.py`, `run_objective_sweep.py` without their dependency:
   exit code 3, guided message, no result file written (file count under benchmarks/results/
   unchanged at 543; `/tmp/x.json` not created). `examples/harvey_fba.py`: guided message, exit 1.
5. UNRUN (T015): equipped-machine regression.
6. UNRUN (T016): GPU-less machine with cuOpt installed.

## Incident

While walking the quickstart I ran `benchmarks/make_figure.py` with its dependencies present; it
regenerated the tracked `benchmarks/figures/benchmark_solvetime.png`. The change was reverted with
`git checkout -- benchmarks/figures/benchmark_solvetime.png`; `git status` shows no figure changes.
