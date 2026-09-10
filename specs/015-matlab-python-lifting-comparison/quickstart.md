# Quickstart: MATLAB vs Python Lifted-Model Runtime & Fidelity Comparison

## Prerequisites

- This machine (confirmed, not assumed): MATLAB R2025a on `PATH`, `cobratoolbox-f-develop`
  checked out with `initCobraToolbox` runnable, Gurobi 11.0.3 installed and licensed
  (`GUROBI_HOME`, `GRB_LICENSE_FILE` already set in this environment).
- `benchmarks/model_cache/` already has all six in-scope models' files committed (no download
  step -- same convention as every prior benchmark feature).
- gpuGEM's Python environment already resolves `gurobipy` (the same environment
  `benchmarks/solve.py::solve_gurobi` already uses successfully in specs 002/010).

## 1. Produce the MATLAB-side results (once, by hand, outside this repo -- research.md R8)

From a scratch location (not inside `gpuGEM/` or `cobratoolbox-f-develop/`), for each of the six
in-scope models: load the same `benchmarks/model_cache/<model>.{xml,mat}` file COBRA-natively,
stack its mass-balance and coupling blocks into one `LPproblem`, call
`reformulate(LPproblem, 1000, 1)`, solve with `changeCobraSolver('gurobi','LP')` +
`solveCobraLP(LPproblem, 'method', 2)`, and write one `matlab_<model>.json` matching the
`PipelineRun` schema (data-model.md). Copy the six resulting files into
`benchmarks/results/matlab_python_lifting/matlab/` and commit them -- this is the only MATLAB-side
artifact that becomes part of the repo; the script that produced them does not (FR-007).

Expected: six `matlab_<model>.json` files, one per in-scope model, each with `status="Optimal"`
(or an honestly-reported non-optimal status) and a recorded `solve_s`.

## 2. Run the Python-side pipeline and build the comparison

```bash
python -m benchmarks.run_matlab_python_lifting_comparison        # all six in-scope models
python -m benchmarks.run_matlab_python_lifting_comparison --model S85 --force   # one model, re-solved
```

Expected: for each model, lifts with `gpugem.lift_mass_balance`/`lift_coupling`, solves with
`benchmarks.solve.solve_gurobi(method=2)`, maps back with `gpugem.map_back`, writes
`python_<model>.json`, then reads the matching `matlab_<model>.json` from step 1 (erroring clearly
if that model's MATLAB-side result is missing) and writes
`benchmarks/results/matlab_python_lifting/comparison.csv` -- one row per in-scope model
(data-model.md `CrossLanguageComparisonRow`).

## 3. Regenerate the figure (no GPU/solver/MATLAB needed -- from committed results alone)

```bash
python -m benchmarks.make_matlab_python_lifting_figure
```

Expected: `benchmarks/figures/matlab_python_lifting_comparison.png` (+ `.pdf`) showing, for each of
the six in-scope models, a MATLAB bar beside a Python bar, with any `verified_correct=False` model
visibly flagged -- matching `make_gurobi_default_figure.py`'s existing "FAILED correctness gate"
annotation convention.

## 4. Confirm cross-language agreement is actually being checked, not assumed

```bash
python -c "
import pandas as pd
df = pd.read_csv('benchmarks/results/matlab_python_lifting/comparison.csv')
print(df[['model', 'matlab_solve_s', 'python_solve_s', 'status_agrees',
          'objective_agrees', 'flux_agrees', 'verified_correct']])
assert df['verified_correct'].all(), 'a model disagreed between MATLAB and Python -- see comparison.csv'
print('OK: all six in-scope models agree between the MATLAB and Python lifted-and-solved pipelines')
"
```

Expected: `True` for every in-scope model's `verified_correct` (or a clear, non-silent failure
naming exactly which model and which check disagreed, per FR-004/FR-005 -- never an averaged-away
mismatch).
