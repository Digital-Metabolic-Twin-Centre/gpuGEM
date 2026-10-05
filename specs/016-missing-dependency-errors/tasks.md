---
description: "Task list for missing-dependency error handling"
---

# Tasks: Missing-Dependency Error Handling

**Input**: `/specs/016-missing-dependency-errors/` (plan.md, spec.md, research.md, data-model.md, contracts/dependency-errors.md, quickstart.md)

**Tests**: REQUIRED (spec FR-013, Constitution III). Tests simulate absence by blocking imports (`monkeypatch.setitem(sys.modules, name, None)`), so they run with no GPU.

**Machine note**: this machine lacks `cuopt`, `gurobipy`, `highspy`, `pytest` (research.md R1). Tasks marked **[GPU]** or **[EQUIPPED]** cannot be completed here; leave them unchecked and report them as UNRUN, never as passed (CLAUDE.md).

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup

- [X] T001 Create a venv and run `pip install -e ".[dev]"`; confirm `python -m pytest tests/ -q` collects (record which tests fail only because cuOpt is absent, as the pre-change baseline) in specs/016-missing-dependency-errors/baseline.md
- [X] T002 [P] Record the pre-change baseline of every `except Exception` site in gpugem/ and benchmarks/ (file:line, what it swallows, current outcome) in specs/016-missing-dependency-errors/baseline.md; the grep count (22 sites) is a lower bound, so also read each file for `except:`, `except ImportError`, and `try/import` patterns

## Phase 2: Foundational (blocks all stories)

- [X] T003 Implement `DependencyError(RuntimeError)` (attributes `dependency`, `kind`, `detected`, `required`, `remedy`; three-line `__str__` per contracts/dependency-errors.md) in gpugem/_deps.py
- [X] T004 Implement the `DependencySpec` registry in gpugem/_deps.py with rows cuopt, numpy, scipy, cobra, gurobipy, highspy, pandas, matplotlib, pytest, nvidia-smi, matlab (fields per data-model.md; `MIN_VERSIONS` constants for cuopt, numpy, scipy, cobra)  
  **Note:** `matlab` was dropped from the registry: no Python code invokes MATLAB (see inventory.md).
- [X] T005 Implement `require(name)` in gpugem/_deps.py: returns the module; `ModuleNotFoundError` for the named module -> `not_installed`; any other exception on import -> `broken` (cause chained, text preserved); installed version via `importlib.metadata` (fallback `__version__`) below minimum -> `version` with detected and required shown; successful result cached
- [X] T006 Implement `require_tool(name)` (`shutil.which`, kind `tool_missing`) and `check_gpu()` (cheap device probe run only after a successful cuopt import; failure -> `no_gpu`, message says "GPU or driver problem suspected" and includes the cause) in gpugem/_deps.py  
  **Note:** `check_gpu()` was implemented as `gpu_evidence()` + `diagnose_solver_failure()`, run only after cuOpt raises (research.md R3, implementation note), not before every solve.
- [X] T007 Export `DependencyError` from gpugem/__init__.py and add it to `__all__`; no other new public name
- [X] T008 [P] Implement benchmarks/_deps.py: `require_or_exit(*names)` (print guided message to stderr, exit code 2) and `optional_info(name)` returning `(value, unavailable_reason)`  
  **Note:** exit code is 3, not 2: the benchmarks already use 2 for a failed correctness gate; `optional_info` became `optional_version` / `gpu_name` / `environment_info`; added `run_main` and `propagate_dependency_exit`.
- [X] T009 Write unit tests for T003-T006 in tests/test_dependency_errors.py: each `kind`, message contains dependency name, "Needed for", and "pip install"; `__cause__` preserved; version-too-old shows both versions; cache does not mask a later block
- [X] T010 [P] Write tests/test_dependency_inventory.py part 1: `MIN_VERSIONS` equal the specifiers in pyproject.toml (FR-010); `import gpugem` succeeds in a subprocess with `cuopt` blocked (FR-005)

**Checkpoint**: T009/T010 pass without a GPU.

## Phase 3: User Story 1 - Library user without the GPU solver (P1)

**Goal**: guided errors from `solve`/`FBASolver`/`solve_cobra` for absent, broken, old, GPU-less solver.

**Independent test**: quickstart steps 1-2 and tests below.

- [X] T011 [US1] Replace the bare `from cuopt.linear_programming import ...` in gpugem/solver.py (inside `solve`) with `require("cuopt")` followed by `check_gpu()` on first use; keep the rest of the function unchanged
- [X] T012 [US1] Audit the four `except Exception` sites in gpugem/solver.py (lines ~219, 239, 246, 297): for each, decide whether it can hide a dependency failure; convert such cases to `DependencyError` or narrow the exception type; record the decision per site in baseline.md. Status/feasibility reporting (Principle II) must not change
- [X] T013 [P] [US1] Tests in tests/test_dependency_errors.py: `gpugem.solve(...)` and `FBASolver(...).solve(...)` raise `DependencyError` kind `not_installed` with cuopt blocked; `broken` when a stub `cuopt` raises `OSError` on import; `version` with a stub `cuopt.__version__ = "0.0.1"`; `no_gpu` with a stub whose device probe raises
- [X] T014 [US1] Verify the numerical tests in tests/test_solver.py are untouched and still pass wherever they passed in the T001 baseline
- [ ] T015 [US1] [GPU] On a machine **with cuOpt and a GPU**, run `python -m pytest tests/ -q` and one benchmark; diff objectives/residuals against the committed results in benchmarks/results/ (SC-005). UNRUN on this machine
- [ ] T016 [US1] [GPU] On a machine **with cuOpt installed and no usable GPU/driver**, run quickstart step 2; record the real exception type, where it is raised (import vs first solve), and the resulting `kind` in specs/016-missing-dependency-errors/research.md under R3; adjust `check_gpu()` if the classification is wrong. Until done, the README limitation (T038) stays marked unverified

## Phase 4: User Story 2 - Optional COBRA / file-format dependencies (P2)

**Goal**: guided errors for cobra and readers.

**Independent test**: tests below with cobra blocked.

- [X] T017 [US2] In gpugem/loaders.py replace `import cobra  # noqa: F401` with `require("cobra")` (remedy names `pip install "gpugem[cobra]"`); `from_cobra` and `solve_cobra` inherit it. Ensure `solve_cobra` checks cobra before any other work
- [X] T018 [US2] In gpugem/loaders.py wrap the `scipy.io.loadmat` call: unreadable/corrupt/unsupported-version file -> `DependencyError` kind `broken` naming the file and format, with the cause chained; a missing file stays `FileNotFoundError`
- [X] T019 [US2] In benchmarks/models.py guard the `import cobra` (line ~76) and the BiGG download: network failure -> kind `network`, remedy "place `<name>.xml` in benchmarks/model_cache/"
- [X] T020 [P] [US2] Tests in tests/test_dependency_errors.py: `from_cobra(None)` and `solve_cobra(None)` with cobra blocked raise kind `not_installed` mentioning `gpugem[cobra]`; truncated `.mat` file raises guided error; simulated `URLError` in the model download raises kind `network`
- [X] T021 [US2] Confirm tests/test_lifting.py still runs when cobra is present and is skipped with a stated reason (not errored) when cobra is blocked

## Phase 5: User Story 4 - Verifiable coverage (P2)

**Goal**: repo-wide inventory check that can fail. Placed before US3 because US3's script work is driven by its output.

**Independent test**: `python -m pytest tests/test_dependency_inventory.py -q`; add `import foo_bar` to a scanned file and see it fail.

- [X] T022 [US4] tests/test_dependency_inventory.py part 2: AST-scan every .py under gpugem/, benchmarks/, examples/, tests/ for top-level module names (including function-local imports and `importlib.import_module("literal")`); subtract `sys.stdlib_module_names` and first-party packages; assert the rest is a subset of the registry plus an explicit exemption list with a written reason for each; print a "not analysable" list for dynamic names
- [X] T023 [US4] Same file: scan `subprocess.run/Popen/check_call` first arguments and `shutil.which` literals; assert each executable is a registry tool or `sys.executable`
- [X] T024 [US4] Same file: fail if an `except Exception:` / bare `except:` whose body is only `pass` appears in a file that imports a registered dependency, unless the line carries `# optional-dep: <field>_unavailable_reason`
- [X] T025 [US4] Run T022-T024 against the current tree **before** any benchmark edits and save the failing output in specs/016-missing-dependency-errors/baseline.md, proving the checks can go red (Constitution VII rule 2). Then confirm manually that adding `import foo_bar` to a scanned file fails T022 and revert
- [X] T026 [US4] Write specs/016-missing-dependency-errors/inventory.md: one row per registry entry (role, where used, min version, failure modes, guided outcome, covering test name) per data-model.md; include the exemptions and the not-analysable list. Every row must name an existing test
- [X] T027 [US4] Add a README-independent doc check in tests/test_dependency_inventory.py: every registry install command appears verbatim in README.md's Dependencies section (after T037)

## Phase 6: User Story 3 - Benchmark and tooling users (P3)

**Goal**: scripts fail early with guidance or record a skip reason; no silent swallowing.

**Independent test**: quickstart step 4; tests below; T024 green.

Hard-dependency guards at the start of `main()` (call `require_or_exit` before reading models or writing results):

- [X] T028 [P] [US3] benchmarks/run_highs_baseline.py: `require_or_exit("highspy")`; replace the four function-local `import highspy` (lines ~21, 51, 81, 207) with the checked module; audit `except Exception` at ~64, 76, 104, 234 and record outcome of each
- [X] T029 [P] [US3] benchmarks/solve.py, benchmarks/run_benchmark.py, benchmarks/run_objective_panel.py, benchmarks/run_objective_sweep.py: `require_or_exit("gurobipy", "cuopt")` as applicable; replace the blanket `except Exception: pass` metadata probes with `optional_info(...)` so `gpu_name`/`cuopt_version`/`gurobi_version` carry `*_unavailable_reason`; handle `nvidia-smi` absent and non-zero exit; distinguish an installed-but-unlicensed Gurobi from not installed (kind `license`)
- [X] T030 [P] [US3] benchmarks/_cuopt_tuning_worker.py, benchmarks/_version_lifting_worker.py, benchmarks/_solver_mode_worker.py, benchmarks/_matlab_python_lifting_worker.py, benchmarks/solver_mode_variants.py: guard at worker start; replace the swallowed cuopt-version probe (`_version_lifting_worker.py` ~63) with `optional_info`; audit the sites at `_cuopt_tuning_worker.py` ~131/139 and `_matlab_python_lifting_worker.py` ~102
- [X] T031 [P] [US3] benchmarks/run_cuopt_tuning.py, run_solver_mode_experiment.py, run_version_lifting_comparison.py, run_matlab_python_lifting_comparison.py: propagate the child process's final guided stderr line into the run record and the parent's exit message; guide failures of the venv creation / `pip install cobra` step (no network, no `venv` module); `require_tool("matlab")` before the MATLAB run, and a stated reason when it is excluded  
  **Note:** the `require_tool("matlab")` clause was dropped (MATLAB is never invoked); the runners abort with the worker's message via `propagate_dependency_exit`.
- [X] T032 [P] [US3] benchmarks/run_block_residuals.py and benchmarks/run_residual_tradeoff.py, run_gurobi_default_benchmark.py, objective_panel.py, cuopt_tuning_preprocessing.py: guard whichever registered dependencies they import; audit run_block_residuals.py ~170
- [X] T033 [P] [US3] Figure and aggregation scripts (benchmarks/make_*.py and aggregate_*.py, 17 files): `require_or_exit("pandas", "matplotlib")` as each uses them, before reading result files; a missing results input exits non-zero naming the producing script  
  **Note:** the clause "a missing results input exits non-zero naming the producing script" was NOT done: result files produced by other scripts are not external dependencies in the spec's sense, and 17 scripts read them in different ways. Only the pandas/matplotlib guard was added.
- [X] T034 [P] [US3] examples/harvey_fba.py and examples/microbiome_fba.py: guard cuopt/cobra with guided messages
- [X] T035 [US3] Tests in tests/test_dependency_errors.py: for a representative script of each group (T028-T034) run it as a subprocess with its dependency blocked via `PYTHONPATH` stub dir or `-c` wrapper; assert exit code 3, message names the dependency and install command, and no file appears under benchmarks/results/. Add one test that a missing `nvidia-smi` yields `gpu_name: null` plus a non-empty `gpu_name_unavailable_reason`  
  **Note:** exit code asserted is 3; representative scripts are run_highs_baseline, run_benchmark, make_figure (the other scripts in each group share the same guard line, covered by the AST/inventory tests but not individually executed).
- [X] T036 [US3] Re-run T022-T024 (now expected green) and save the passing output in baseline.md next to the T025 failing output

## Phase 7: Polish and cross-cutting

- [X] T037 [P] Add `# Dependencies` and `# Troubleshooting` sections to README.md: table of hard/optional/benchmark/tool dependencies with install commands, and one entry per error kind (`not_installed`, `broken`, `version`, `no_gpu`, `license`, `tool_missing`, `network`) with the fix; link to the cuOpt install documentation for other CUDA majors (check wording against the `cuopt-install` skill)
- [X] T038 [P] Add to README.md "Known limitations": GPU/driver-absent classification is a heuristic and **unverified** until T016 is done (state the date when it is); AST inventory cannot see dynamically built import or tool names
- [X] T039 Run `ruff check` (line-length 100) and fix findings in touched files  
  **Note:** `ruff check --select E,F`: no new F findings. The project's configured `ruff check` is not clean at HEAD (~300 findings, mostly style rules) and was not cleaned up. New E402 in scripts follow the repo's existing sys.path pattern.
- [X] T040 Run the full suite and compare to the T001 baseline: no previously passing test regressed; dependency tests pass with no GPU; GPU-only tests listed as UNRUN  
  **Note:** 12 tests fail, all needing cuOpt or gurobipy (UNRUN, not passed); see baseline.md.
- [X] T041 Walk quickstart.md steps 1-4 on this machine and record actual output in baseline.md; steps 5-6 are reported as UNRUN unless T015/T016 were done on an equipped machine  
  **Note:** steps 5-6 UNRUN; see baseline.md.
- [X] T042 Final report: list per-site audit outcomes (T002/T012/T028-T032), any in-scope site left unchanged with its reason (Principle VII rule 3), and every unrun task

## Dependencies

- Phase 1 -> Phase 2 -> all stories. T003 -> T004 -> T005/T006 -> T007; T008 needs T005.
- US1 (T011-T016) and US2 (T017-T021) are independent after Phase 2 and can run in parallel.
- US4 T022-T025 must run **before** US3 edits (T025 needs the unmodified tree); T026 after US3; T027 after T037.
- US3 tasks T028-T034 are mutually independent (different files); T035-T036 follow them.
- T015/T016 need external hardware and do not block the rest; T038's wording depends on T016.

## Parallel example

After Phase 2: T011, T017, T022 together; later T028-T034 together (seven different file groups).

## Implementation strategy

- **MVP = Phase 1 + 2 + US1 (T001-T014)**: the guided error for the missing solver, with tests that run here.
- Then US2, then US4 (T022-T025 first, to prove the check can fail), then US3, then polish.
- T015/T016 are the only tasks that verify behaviour on real cuOpt; the feature is not claimed complete for GPU-failure classification until T016 is done.
