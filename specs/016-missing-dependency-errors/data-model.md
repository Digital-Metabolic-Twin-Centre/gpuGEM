# Data Model

## DependencySpec (internal, `gpugem/_deps.py`)

| Field | Meaning |
|---|---|
| `name` | Import name, e.g. `cuopt` |
| `distribution` | pip name, e.g. `cuopt-cu12` |
| `role` | `required` \| `optional` \| `benchmark` \| `tool` \| `dev` |
| `min_version` | string or `None`; mirrored in `pyproject.toml` (tested) |
| `purpose` | one phrase for the "why needed" part of the message |
| `install` | exact command, e.g. `pip install "cuopt-cu12>=26.6.0"` |
| `extra` | optional-extra name when applicable, e.g. `cobra` |
| `tool` | `True` for executables (checked with `shutil.which`) |

Rows: cuopt, numpy, scipy, cobra, gurobipy, highspy, pandas, matplotlib, pytest, nvidia-smi, matlab.
Validation: every non-stdlib import in the repo has a row or a listed exemption (R8).

## DependencyError (public)

| Field | Type | Notes |
|---|---|---|
| `dependency` | str | spec name |
| `kind` | str | `not_installed`, `broken`, `version`, `no_gpu`, `license`, `tool_missing`, `network` |
| `detected` | str \| None | installed version or probe result |
| `required` | str \| None | minimum version |
| `remedy` | str | install/upgrade command or environment fix |
| `__cause__` | Exception \| None | original exception |

`str(error)` = three labelled lines: problem, why needed, how to fix. No state transitions.

## Benchmark result metadata addition

For each optional metadata field `X` (e.g. `gpu_name`, `cuopt_version`, `gurobi_version`):
`X` stays as today; `X_unavailable_reason` (string) is added only when `X` is null. Existing
readers ignore the extra key.
