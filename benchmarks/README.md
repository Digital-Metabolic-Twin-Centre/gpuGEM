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

## S85 multi-objective sweep

S85 was the one outlier in the table above (cuOpt ~10x *slower* than Gurobi on
the single whole-body objective, unlike every other model). `run_objective_sweep.py`
re-solves S85 with both solvers across ~20 additional biologically distinct
objectives (`s85_objectives.py`: organ/tissue biomass, immune-cell biomass,
individual gut-microbiome taxa) to check whether that gap holds on average or
was specific to the whole-body objective. Same correctness gate, same LP
builder pattern as above; unlike the cross-scale benchmark it defaults to 1
repeat per (objective, solver) since the statistical signal here comes from
averaging across ~20 objectives rather than repeating one (see
`specs/003-s85-multi-objective-benchmark/`).

```bash
python -m benchmarks.run_objective_sweep --objective whole_body   # one objective
python -m benchmarks.run_objective_sweep --all                    # all ~20 (resumable, hours)
python -m benchmarks.aggregate_sweep                               # summary from committed JSON, no GPU
```

Because a full `--all` run can take hours, it prints a start/finish line per
(objective, solver) plus a heartbeat line every `--heartbeat-s` (default 30s)
while a solve is in progress, and skips objectives whose result already exists
unless `--force` — so it is safe to interrupt and restart.

Outputs (committed) under `results/s85_objectives/`: `objectives.json` (the
objective registry with each one's biological rationale), one `<id>.json` per
objective, and `summary.json`/`summary.csv` (per-solver average/median/min/max
runtime, the cuOpt/Gurobi runtime ratio, and any objective whose ratio is an
outlier relative to the rest).
