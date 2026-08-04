# Quickstart: Add Harvetta to the Benchmark Suite and Commit Model Files

## Prerequisites

- `benchmarks/model_cache/Harvetta_1_03d.mat` already present (done by the user).
- GPU + cuOpt + Gurobi available for the solve steps; figure regeneration needs neither.

## Solve Harvetta under both existing benchmarks (GPU required)

```bash
cd ~/projects/gpuGEM && conda activate base

python -m benchmarks.run_benchmark --model Harvetta --reps 3
python -m benchmarks.run_residual_tradeoff --model Harvetta
```

Expected: both commands print `[Harvetta] ...` progress lines ending in `status=Optimal` for both
solvers (or a clearly-marked failure per FR-004 — this is not assumed in advance). If the second
command is instead run via `--all`, expect `[skip]`/`[backfill]` for every already-covered model
and a fresh solve only for `Harvetta`.

## Regenerate every figure (no GPU/solver needed)

```bash
python -m benchmarks.make_figure
python -m benchmarks.make_residual_tradeoff_figures
python -m benchmarks.make_violation_distribution_figures
```

## Commit the model files

```bash
git rm --cached benchmarks/model_cache/*.mat 2>/dev/null  # no-op if nothing was tracked yet
# edit .gitignore per contracts/gitignore-and-tracking.md
git add benchmarks/model_cache/Harvetta_1_03d.mat \
        benchmarks/model_cache/mWBM_S9_male.mat \
        benchmarks/model_cache/mWBM_S15_male.mat \
        benchmarks/model_cache/mWBM_S23_male.mat \
        benchmarks/model_cache/mWBM_S83_male.mat \
        .gitignore
```

## Validate

1. `benchmarks/results/Harvetta.json` and `benchmarks/results/residual_tradeoff/Harvetta.json`
   both exist and show `status=Optimal` (or a clearly-recorded failure) for every configuration
   (SC-001, SC-002).
2. `benchmarks/results/benchmark.csv` has 10 models; `.../residual_tradeoff/comparison.csv` has 30
   rows (10 models x 3 configurations).
3. All four regenerated figures (`benchmark_solvetime.png`, `residual_tradeoff_solvetime.png`,
   `residual_tradeoff_violations.png`, `violation_distribution_equations.png`,
   `violation_distribution_constraints.png`) show Harvetta positioned by size alongside every other
   model (SC-002).
4. `git diff --stat benchmarks/results/{S9,S15,S23,S83,Harvey,S84,S85,e_coli_core,iML1515}.json
   benchmarks/results/residual_tradeoff/` shows no unintended changes to any other model's numbers
   (SC-003).
5. `git check-ignore benchmarks/model_cache/mWBM_S9_male_lifted.mat` still exits 0 (still ignored);
   `git ls-files benchmarks/model_cache/` lists exactly 7 files (2 XML + 5 plain `.mat`) (SC-004).
6. `git diff --stat gpugem/` is empty (SC-005).
