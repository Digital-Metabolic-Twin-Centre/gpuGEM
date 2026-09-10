# CLI Contract: MATLAB vs Python Lifted-Model Runtime & Fidelity Comparison

## (untracked, outside both repos) the temporary MATLAB comparison script

Not part of this contract's tracked surface (research.md R8, spec FR-007) -- exists only long
enough to produce one `matlab_<model>.json` per in-scope model, matching the `PipelineRun` schema
(data-model.md), which is then copied into `benchmarks/results/matlab_python_lifting/` and
committed. Its own invocation shape (a MATLAB `.m` script or function taking a model name) is not
specified here since it is never invoked by any of this feature's own tracked tooling.

## `python -m benchmarks._matlab_python_lifting_worker`

Subprocess entry point for one model's Python-side pipeline: lift with `gpugem.lift_mass_balance`
/ `gpugem.lift_coupling`, solve with `benchmarks.solve.solve_gurobi`, map back with
`gpugem.map_back` (research.md R4). Never invoked directly by a user.

```text
--model NAME           one of the six in-scope models (required)
--lift-big FLOAT        default 1000.0 (spec 013's established default)
--time-limit SECONDS    default 900.0 (this project's established convention)
```

Prints one JSON `PipelineRun`-shaped (`pipeline="python"`) object to stdout (last line -- same
convention as `_version_lifting_worker.py`, in case any underlying library logs directly to the
stdout file descriptor).

## `python -m benchmarks.run_matlab_python_lifting_comparison`

```text
--model NAME             one of the six in-scope models; repeatable, default: all six
--matlab-results DIR     default benchmarks/results/matlab_python_lifting/matlab/
                          -- where already-produced matlab_<model>.json files are read from
--force                  re-run a model's Python-side pipeline even if its result already exists
--lift-big FLOAT         default 1000.0
--time-limit SECONDS     default 900.0
```

For each requested model: runs (or reuses an existing) `python_<model>.json` via
`_matlab_python_lifting_worker`, reads the corresponding already-produced `matlab_<model>.json`
(erroring clearly, per FR-009, if that model's MATLAB-side result is missing -- this command never
runs MATLAB itself), builds that model's `CrossLanguageComparisonRow` (data-model.md), and writes
`benchmarks/results/matlab_python_lifting/comparison.csv`. Calls
`make_matlab_python_lifting_figure.main()` at the end.

## `python -m benchmarks.make_matlab_python_lifting_figure`

No arguments. Reads `comparison.csv`, writes
`benchmarks/figures/matlab_python_lifting_comparison.png` and `.pdf` (Constitution Principle VI).
No GPU/solver/MATLAB required -- regenerable from committed results alone, matching this project's
established `make_*_figure.py` convention.
