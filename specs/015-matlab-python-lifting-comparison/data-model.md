# Phase 1 Data Model: MATLAB vs Python Lifted-Model Runtime & Fidelity Comparison

## PipelineRun (one model, one pipeline)

Shared shape for both `benchmarks/results/matlab_python_lifting/matlab_<model>.json` (produced by
the temporary, untracked MATLAB script -- research.md R8) and
`.../python_<model>.json` (produced by this feature's own, tracked `_matlab_python_lifting_worker.py`).
Using one shared schema for both sides is what makes FR-003/FR-004/FR-005's model-by-model
comparison a straightforward field-by-field diff rather than two different shapes needing
translation.

| Field | Type | Notes |
|---|---|---|
| `model` | `str` | One of the six in-scope models (research.md, spec Assumptions) |
| `pipeline` | `"matlab"` \| `"python"` | |
| `lift_big` | `float` | `reformulate.m`'s `BIG` / `gpugem`'s `lift_big` -- same value both sides (default 1000.0, spec 013's established default) |
| `solve_s` | `float` | Wall-clock lift+solve time, median of this project's established repeat count (research.md R5) |
| `status` | `str` | Gurobi's own status string, normalized the same way `benchmarks/solve.py::solve_gurobi`'s `status_map` already normalizes it (e.g. `"Optimal"`, `"TimeLimit"`) -- never silently remapped (Constitution II) |
| `objective` | `float \| None` | `None` only when `status` carries no solution |
| `fluxes_available` | `bool` | Whether a mapped-back flux vector was recorded (large whole-body flux vectors are not embedded in the committed JSON itself -- see `flux_summary` below) |
| `flux_summary` | `object \| None` | Small, comparison-sufficient summary (e.g. L2 norm, max abs value) of the mapped-back flux vector, not the full vector -- keeps committed JSON small for whole-body/microbiome models while still supporting SC-003's agreement check via `residual.py`-style comparison |
| `n_aux_vars` | `int` | Auxiliary variables added by lifting -- reported per edge case ("different aux-variable counts... reported as a data point") |
| `n_mass_balance_rows_lifted` | `int` | |
| `n_coupling_rows_lifted` | `int` | |
| `excluded` | `bool` | `true` only if this model could not be run on this pipeline at all (FR-009) |
| `excluded_reason` | `str \| None` | Required, human-readable, when `excluded` is `true` |

## CrossLanguageComparisonRow (one row of the derived CSV)

One row per in-scope model, in `benchmarks/results/matlab_python_lifting/comparison.csv` --
pairs that model's `matlab_<model>.json` and `python_<model>.json`.

| Column | Type | Notes |
|---|---|---|
| `model` | `str` | |
| `n_cols` | `int` | Original (unlifted) variable count, for consistent sort order with this project's other benchmark figures |
| `matlab_solve_s` | `float \| NaN` | `NaN` only if `excluded` on the MATLAB side |
| `python_solve_s` | `float \| NaN` | `NaN` only if `excluded` on the Python side |
| `matlab_status` | `str` | |
| `python_status` | `str` | |
| `status_agrees` | `bool` | `matlab_status == python_status` (FR-004) |
| `objective_agrees` | `bool` | Within `OBJ_TOL` (research.md R5) -- `False`, never omitted, when either side lacks a solution |
| `flux_agrees` | `bool` | Within `RES_TOL`-equivalent flux comparison (FR-005) |
| `n_aux_vars_matlab` | `int` | |
| `n_aux_vars_python` | `int` | |
| `aux_vars_match` | `bool` | Informational only (edge case: a mismatch here is a data point, not by itself a failure) |
| `verified_correct` | `bool` | `status_agrees and objective_agrees and flux_agrees` -- the single pass/fail gate SC-002/SC-003 report against |
| `excluded_models` | `str \| None` | Which side(s), if any, excluded this model and why (FR-009) |

A model excluded on either side still gets a row -- `verified_correct=False` with the exclusion
reason carried through, never a silently-missing row (SC-004).

## ComparisonFigure (the persisted artifact)

Not a data record with fields of its own, but the feature's ultimate deliverable
(FR-010/FR-011): `benchmarks/figures/matlab_python_lifting_comparison.png` (+ `.pdf` vector copy),
generated from `comparison.csv` alone (no live solver required to regenerate it, matching this
project's `make_*_figure.py` convention of being re-runnable from committed data). Shows, per
model, a MATLAB bar and a Python bar (grouped, log-scale y-axis for the small-to-whole-body scale
range), annotated with the actual solve time, and a visually distinct marker for any model whose
`verified_correct` is `False` (same "FAILED correctness gate" annotation convention as
`make_gurobi_default_figure.py`).
