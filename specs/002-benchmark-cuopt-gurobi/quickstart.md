# Quickstart: run the benchmark

Host: GPU machine with cuOpt + Gurobi in the base conda env.

```bash
cd ~/projects/gpuGEM
conda activate base

# one model
python -m benchmarks.run_benchmark --model iML1515 --reps 3

# everything (resumable; skips models already in results/ unless --force)
python -m benchmarks.run_benchmark --all --reps 3

# regenerate the figure from the committed CSV (no GPU / no solver needed)
python -m benchmarks.make_figure
```

Outputs:
- `benchmarks/results/<model>_<solver>.json` — per solve, all repeats + provenance
- `benchmarks/results/benchmark.csv` — aggregated medians
- `benchmarks/figures/benchmark_solvetime.png` — the comparison figure

A cell FAILS (non-zero exit) if a solver is non-optimal, residual > 1e-6, or the two
solvers' objectives disagree by > 1e-6 relative. No time is reported for a failed cell.
