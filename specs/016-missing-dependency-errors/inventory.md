# Dependency inventory (FR-012)

Source of truth: `gpugem/_deps.py::REGISTRY`. Completeness is enforced by
`tests/test_dependency_inventory.py` (AST scan of gpugem/, benchmarks/, examples/, tests/).

| Dependency | Role | Min version | Failure modes handled | Guided outcome | Covering tests |
|---|---|---|---|---|---|
| numpy, scipy | required | 1.24 / 1.10 | absent (checked at `import gpugem`) | `DependencyError` at import | `test_import_gpugem_reports_missing_numpy`, `test_min_versions_match_pyproject` |
| cuopt | required | 26.6.0 | absent; fails to load; too old; GPU/driver problem (heuristic, **unverified on real cuOpt**) | `DependencyError` from `solve` / `FBASolver.solve` / `solve_cobra`; `import gpugem` unaffected | `test_solve_without_cuopt_is_guided`, `test_fbasolver_without_cuopt_is_guided`, `test_require_broken_import_keeps_cause`, `test_require_version_too_old`, `test_solve_with_old_cuopt_is_guided`, `test_cuopt_import_failure_with_no_gpu_evidence_is_no_gpu`, `test_solve_failure_inside_cuopt_with_no_gpu_evidence`, `test_solve_failure_with_working_gpu_reraises_original`, `test_import_gpugem_does_not_need_cuopt` |
| cobra | optional (`gpugem[cobra]`) | 0.29 | absent | `DependencyError`, names the extra | `test_from_cobra_without_cobra_is_guided`, `test_solve_cobra_without_cobra_is_guided` |
| scipy.io `.mat` reader | required | - | corrupt file; MATLAB v7.3 file | `DependencyError(kind=broken)` with file name + fix; missing file stays `FileNotFoundError` | `test_from_mat_corrupt_file_is_guided`, `test_from_mat_v73_file_is_guided`, `test_from_mat_missing_file_stays_file_not_found` |
| BiGG download | benchmark | - | no network | `DependencyError(kind=network)` with manual-placement path | `test_model_download_failure_is_network_error` |
| gurobipy | benchmark | - | absent; no / size-limited licence | up-front exit 3; `kind=license` distinct from `not_installed` (errno values unverified) | `test_require_or_exit_exits_3_with_guidance`, `test_gurobi_licence_error_is_distinct_from_not_installed`, `test_gurobi_unrelated_error_is_not_relabelled`, `test_scripts_exit_with_guidance_when_dependency_blocked[run_benchmark]` |
| highspy | benchmark | - | absent | exit 3 before any work | `test_scripts_exit_with_guidance_when_dependency_blocked[run_highs_baseline]` |
| pandas, matplotlib | benchmark | - | absent | exit 3 at script start | `test_scripts_exit_with_guidance_when_dependency_blocked[make_figure]` |
| pytest | dev | - | absent | not guarded in code (the tests cannot run without it); installed via `pip install -e ".[dev]"`, listed in README | `test_registry_install_commands_are_documented_in_readme` |
| nvidia-smi | tool | - | absent; non-zero exit | recorded as `gpu_name: null` + `gpu_name_unavailable_reason`; used as GPU evidence | `test_environment_info_records_reason_when_probes_fail`, `test_gpu_name_nonzero_exit_has_reason`, `test_gpu_evidence_*` |
| venv / pip provisioning (version-lifting runner) | benchmark | - | venv module missing; pip/network failure | `DependencyError` with remedy | `test_venv_provisioning_failure_is_guided` |
| worker subprocess | benchmark | - | child exits 3 | parent aborts with the child's message instead of recording "crashed" | `test_propagate_dependency_exit` |

## Exemptions (with reasons)

- `_pytest`, `setuptools`: only reachable when pytest / the build backend is present.
- `pip`: invoked as `sys.executable -m pip`, i.e. through the interpreter.
- First-party sibling-module imports made after a script puts its own directory on `sys.path` are
  excluded by stem-matching against repo `.py` files (a repo file named like a third-party package
  would mask it; none does today).

## Not analysable by the static scan

Dynamic `import_module(<non-literal>)` and non-literal `subprocess` commands are printed by the
tests, not ignored. At the time of writing the scan reports exactly one: `gpugem/_deps.py:222`, the
registry's own `import_module(name)`. It reports no non-literal subprocess commands (commands built
from `sys.executable` / a venv python are recognised as interpreter-based).

## Dropped from the plan

`matlab` was in the plan's registry. No Python code in this repo invokes MATLAB (the MATLAB-vs-Python
comparison reads an already-produced `matlab_<model>.json` and says so when it is missing), so a
registry entry would have been dead; it was removed and `test_every_registered_python_dependency_is_used_somewhere`
guards against such entries.
