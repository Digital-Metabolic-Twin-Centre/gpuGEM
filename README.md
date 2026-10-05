<div align="center">

# gpuGEM

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![CUDA](https://img.shields.io/badge/CUDA-12%2B-green)](https://developer.nvidia.com/cuda-toolkit)
[![cuOpt](https://img.shields.io/badge/NVIDIA%20cuOpt-26.6%2B-76B900)](https://developer.nvidia.com/cuopt)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status: Alpha](https://img.shields.io/badge/status-alpha-orange)]()

GPU-accelerated Flux Balance Analysis (FBA) for genome-scale metabolic models.

</div>

gpuGEM wraps [NVIDIA cuOpt](https://developer.nvidia.com/cuopt) PDLP solver with validated default settings derived from systematic benchmarking on whole-body metabolic models, including the [Harvey](https://www.vmh.life/) model and personalised microbiome whole-body models. It provides a minimal, COBRA-compatible API so existing modelling workflows can switch to GPU solving with one line of code.

---

## Why gpuGEM?

GPU first-order LP solvers (PDLP) offer substantial speedups on genome-scale FBA, but getting correct results requires non-obvious configuration. Out-of-the-box cuOpt settings produce large constraint violations or silently return wrong solutions on whole-body models. gpuGEM ships with settings that have been validated for correctness:

| Model | Reactions | Constraints | Time | Max stoich. residual |
|---|---|---|---|---|
| Harvey whole-body model | 81K | 160K | **0.76 s** | 1.8e-5 |
| Microbiome whole-body model | 789K | 1.66M | **27 s** | 8.4e-5 |

---

## Installation

```bash
pip install cuopt-cu12          # NVIDIA cuOpt (requires CUDA 12; Python 3.11 or later)
pip install gpugem
```

COBRApy support (optional):

```bash
pip install "gpugem[cobra]"
```

### Dependencies

| Package / tool | Role | Needed for | Install |
|---|---|---|---|
| `numpy`, `scipy` | required | every function | `pip install "numpy>=1.24"`, `pip install "scipy>=1.10"` |
| `cuopt` | required | the GPU solver; checked when you solve, not at `import gpugem` | `pip install "cuopt-cu12>=26.6.0"` (other CUDA versions: see the [cuOpt install guide](https://docs.nvidia.com/cuopt/user-guide/latest/introduction.html)) |
| `cobra` | optional | `solve_cobra`, `loaders.from_cobra` | `pip install "gpugem[cobra]"` |
| `gurobipy` | benchmarks | the Gurobi baseline (needs a licence) | `pip install gurobipy` |
| `highspy` | benchmarks | the HiGHS CPU baseline | `pip install highspy` |
| `pandas`, `matplotlib` | benchmarks | result tables and figures | `pip install pandas`, `pip install matplotlib` |
| `pytest` | development | the test suite | `pip install -e ".[dev]"` |
| `nvidia-smi` | tool | GPU name in benchmark metadata; GPU diagnosis | install the NVIDIA driver (https://www.nvidia.com/drivers); nvidia-smi ships with it |

### Troubleshooting

A missing or unusable dependency raises `gpugem.DependencyError` (benchmark and example scripts
print the same message; benchmark scripts exit with status 3). The message always says what is wrong, why gpuGEM
needs it, and how to fix it. The original exception is kept as `__cause__`. `err.kind` is one of:

| `kind` | Meaning | What to do |
|---|---|---|
| `not_installed` | the package is absent | run the `pip install` command in the message |
| `broken` | installed but fails to import, or a model file cannot be read | reinstall; check that Python, the CUDA runtime and the driver match the build. For `.mat` files, re-save with `save(file, 'model', '-v7')` |
| `version` | installed version below the minimum | run the `pip install --upgrade` command in the message |
| `no_gpu` | no usable NVIDIA GPU or driver is detected | run `nvidia-smi`; install or update the driver; in a container, start it with GPU access |
| `license` | Gurobi is installed but has no valid licence for the model | obtain a licence and set `GRB_LICENSE_FILE`; check with `grbprobe` |
| `tool_missing` | an executable is not on `PATH` | install it or add it to `PATH` |
| `network` | a model download failed | download the file manually into `benchmarks/model_cache/` |

```python
try:
    result = gpugem.solve_cobra(model)
except gpugem.DependencyError as err:
    print(err.kind, err.dependency, err.remedy)
```

---

## Quick start

**From a COBRApy model:**

```python
import cobra
import gpugem

model = cobra.io.read_sbml_model("e_coli_core.xml")
result = gpugem.solve_cobra(model)

print(result)                       # FBAResult(status='Optimal', objective=0.8739, time=0.42s)
print(result.objective)
print(result.fluxes)                # numpy array, same order as model.reactions
```

**From a COBRA `.mat` file (MATLAB format):**

```python
import gpugem

arrays = gpugem.loaders.from_mat("Harvey_1_03c_reduced.mat")
result = gpugem.solve(**arrays)
```

**From raw matrices (scipy sparse):**

```python
import gpugem

result = gpugem.solve(
    S=S,           # stoichiometric matrix (sparse)
    b=b,           # RHS equalities
    lb=lb, ub=ub,  # variable bounds
    c=c,           # objective coefficients
    maximize=True,
)
```

**Whole-body models with coupling constraints:**

```python
result = gpugem.solve(S=S, b=b, lb=lb, ub=ub, c=c,
                      C=C, d_lb=d_lb, d_ub=d_ub,
                      maximize=True)
```

---

## Default settings

gpuGEM automatically selects solver settings based on model size:

**Small models (≤ 100K reactions) — e.g. Harvey whole-body model:**

```python
pdlp_precision             = 1      # mixed FP32/FP64 — double precision diverges on these models
absolute_primal_tolerance  = 1e-8   # tight tolerance: 0 stoich violations at 1e-6 max residual
relative_primal_tolerance  = 1e-8
absolute_dual_tolerance    = 1e-8
relative_dual_tolerance    = 1e-8
per_constraint_residual    = 1      # max-norm convergence check → better accuracy
```

**Large models (> 100K reactions) — e.g. personalised microbiome whole-body models:**

```python
presolve                   = 1      # PaPILO — required; default PSLP falsely reports Infeasible
per_constraint_residual    = 1      # max-norm convergence → 44% fewer violations vs default
absolute_primal_tolerance  = 1e-4   # cuOpt's internal default tolerance
relative_primal_tolerance  = 1e-4
absolute_dual_tolerance    = 1e-4
relative_dual_tolerance    = 1e-4
```

Any cuOpt parameter can be overridden:

```python
# Use Stable1 PDLP mode for maximum accuracy (slower)
result = gpugem.solve(**arrays, pdlp_solver_mode=0, time_limit=300)

# Disable presolve explicitly
result = gpugem.solve(**arrays, presolve=0)
```

---

## Stateful solver (repeated solves)

```python
solver = gpugem.FBASolver(S=S, b=b, lb=lb, ub=ub, c=c, maximize=True)

for patient_c in patient_objectives:
    result = solver.solve(c=patient_c)
    print(result.objective)
```

---

## Result object

```python
result.status       # 'Optimal', 'TimeLimit', 'Infeasible', ...
result.objective    # float
result.fluxes       # np.ndarray (n_vars,)
result.wall_time_s  # float
result.solver_settings  # dict of applied cuOpt parameters
result.feasibility  # dict: stoich_max_residual, stoich_rows_violated_1e6, ...
```

---

## Known limitations

- **Lifted, extreme-scale (`S84`/`S85`-class) models are not reliably solvable by every Gurobi
  entry point.** `benchmarks/run_matlab_python_lifting_comparison.py` found that Gurobi solves the
  lifted `S84`/`S85` systems to `Optimal` via COBRA Toolbox's `solveCobraLP` (MATLAB) but reports
  `Infeasible` for the *structurally identical* system (confirmed: identical auxiliary-variable
  and lifted-row counts) via a direct `gurobipy` call (Python). Checked and ruled out as causes:
  a Gurobi solver-settings mismatch (`Method`, `TimeLimit`, `FeasibilityTol`/`OptimalityTol` all
  confirmed identical), a Gurobi *version* mismatch (`pip install gurobipy` initially resolved a
  different major version, `13.0.3`, than MATLAB's licensed `11.0.3`; re-run with the versions
  pinned to match — `Infeasible` persisted), and a borderline numerical-tolerance flip (persisted
  after relaxing `FeasibilityTol` 100x). This reproduces, under a second independent solver
  pathway, the same `S84`/`S85` scale boundary already found for lifted cuOpt solves (see "Version
  x lifting runtime comparison" above) — lifting's mathematical correctness is not in question
  (structural fidelity is exact), but its practical solvability at this scale is
  entry-point-dependent, for a reason not yet isolated. See
  `specs/015-matlab-python-lifting-comparison/`.

- **GPU/driver-absent detection is a heuristic and is unverified against real cuOpt.** gpuGEM
  reports `DependencyError(kind="no_gpu")` only when cuOpt raises *and* there is positive evidence
  of a GPU problem (`nvidia-smi` fails or lists no GPU, or it is absent and no `/dev/nvidia*`
  device exists). The exact exception cuOpt raises on a machine with no GPU, and whether it is raised
  at import or at first solve, has not been observed (the development machine has no cuOpt); until
  it is, such a failure may surface as `kind="broken"` or as cuOpt's own exception. The Gurobi
  licence error numbers (10009, 10010) used for `kind="license"` are likewise unverified here.
  See `specs/016-missing-dependency-errors/` (tasks T016).
- **The dependency inventory is static.** `tests/test_dependency_inventory.py` finds imports and
  `subprocess` / `shutil.which` calls with literal names; a module or executable whose name is built
  at run time is not seen (the test prints those it cannot analyse).

---

## Citation

If you use gpuGEM in your research, please cite:

> *gpuGEM: validated GPU solving of genome-scale metabolic LPs*  
> Digital Metabolic Twin Centre, 2026. https://github.com/Digital-Metabolic-Twin-Centre/gpuGEM

---

## License

MIT © 2026 Digital Metabolic Twin Centre
