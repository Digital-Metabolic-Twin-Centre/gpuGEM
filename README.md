<div align="center">

# gpuGEM

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
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
pip install cuopt-cu12          # NVIDIA cuOpt (requires CUDA 12)
pip install gpugem
```

COBRApy support (optional):

```bash
pip install "gpugem[cobra]"
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
# tolerances left at default 1e-4 — accuracy bottleneck is PaPILO's internal feastol, not PDLP
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

- Requires an NVIDIA GPU with CUDA 12+ and the `cuopt-cu12` package (NVIDIA Developer licence).
- The min-norm QP step (used in some FBA variants to select a unique flux vector) cannot currently be solved by cuOpt — Gurobi or another QP solver is needed for that step.
- Postsolve accuracy on models > 100K reactions is bounded at ~1e-5 due to a hardcoded tolerance in cuOpt's PaPILO integration ([open issue](https://github.com/rapidsai/cuopt/issues)).
- On the mWBM S85 microbiome model (coefficient range spanning `[1e-6, 2e5]`), cuOpt's PDLP is
  structurally ~9-10x slower than Gurobi across every biologically distinct objective tested, not
  just one (`benchmarks/run_objective_sweep.py`). None of `pdlp_solver_mode=Methodical1`,
  `method=Concurrent`, or a cold (no warm-start) `method=Barrier` close that gap on this model:
  Methodical1 did not converge within a 900s+60s budget (worse than baseline's ~505s); Concurrent
  raced PDLP/DualSimplex/Barrier and PDLP won again (~513s, effectively tied with baseline); cold
  Barrier failed almost immediately with `status=NumericalError` (~7s, no usable solution) —
  plausibly cuDSS's sparse factorization failing on this matrix's ill-conditioning without a warm
  start to help it, consistent with `26.6.0`'s separately-confirmed broken warm-start path
  (`benchmarks/run_solver_mode_experiment.py`, see `specs/004-s85-solver-mode-experiment/`).

---

## Citation

If you use gpuGEM in your research, please cite:

> *gpuGEM: GPU-accelerated Flux Balance Analysis for genome-scale metabolic models.*  
> Digital Metabolic Twin Centre, 2026. https://github.com/Digital-Metabolic-Twin-Centre/gpuGEM

---

## License

MIT © 2026 Digital Metabolic Twin Centre
