# Cross-scale cuOpt vs Gurobi LP benchmark

Compares the GPU LP solver (NVIDIA cuOpt, via gpuGEM's shipped size-selected
defaults) against Gurobi standalone on the max-biomass FBA LP of five models
spanning four orders of magnitude:

| model | scale | source | loader |
|---|---|---|---|
| e_coli_core | small | BiGG (cached) | cobra -> gpugem.loaders.from_cobra |
| iML1515 | medium | BiGG (cached) | cobra -> gpugem.loaders.from_cobra |
| Harvey | whole-body | Harvey_1_03c_reduced.mat | gpugem.loaders.from_mat |
| S84 | microbiome | mWBM_S84_male.mat | gpugem.loaders.from_mat |
| S85 | microbiome | mWBM_S85_male.mat | gpugem.loaders.from_mat |

Both solvers receive the **identical** LP built by `gpugem.loaders`. cuOpt uses
gpuGEM's shipped defaults (`gpugem._defaults.default_settings`, size-selected:
mixed-precision PDLP for <=100K vars, PaPILO presolve above). Gurobi uses barrier
+ crossover. The cuOpt settings are consumed, never retuned for the comparison.

## Correctness gate (before any timing is trusted)

For every solve the runner records the stoichiometric residual `||S v - b||_inf`
and the objective. A model cell is **FAILED** (non-zero exit) if a solver is
non-optimal, the residual exceeds `--res-tol` (default 1e-4), or the two solvers'
objectives disagree by more than `--obj-tol` (default 1e-6 relative). No solve
time is reported for a failed cell.

The 1e-4 absolute residual tolerance accommodates the microbiome whole-body
models, whose stoichiometric coefficients span [1e-6, 2e5]; cuOpt's PaPILO
integration has a hardcoded feastol ~1e-5 (see gpugem/_defaults.py), so an
absolute 1e-6 gate would reject a solution that reaches the identical optimum
as Gurobi (objectives agree to 0 relative difference on all five models).

## Run

```bash
cd ~/projects/gpuGEM && conda activate base

python -m benchmarks.run_benchmark --model iML1515 --reps 3     # one model
python -m benchmarks.run_benchmark --all --reps 3               # all (resumable)
python -m benchmarks.make_figure                                # figure from CSV, no GPU
```

`--all` skips models whose `results/<model>.json` already exists unless `--force`.

Model file locations can be overridden with `MWBM_DIR` and `HARVEY_MAT` env vars.

## Outputs (committed)

- `results/<model>.json` — every repeat, provenance (checksums, dims, versions).
- `results/benchmark.csv` — aggregated medians; the single source for the figure.
- `figures/benchmark_solvetime.png` — regenerable from the CSV alone.

## Reproducibility

- BiGG models cached under `model_cache/` (sha256 recorded); `.mat` files pinned
  by sha256. Solver + GPU versions embedded in every JSON and the figure caption.
- The figure imports only pandas + matplotlib — a reviewer can rebuild it with no
  GPU and no solver license.
