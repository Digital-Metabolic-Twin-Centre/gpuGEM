#!/bin/bash
source ~/miniconda3/etc/profile.d/conda.sh
conda activate base
cd ~/projects/gpuGEM
export MWBM_DIR=/home/farid/projects/cuGEM/microbiome_models
python -m benchmarks.run_benchmark --all --reps 3 --time-limit 900
echo "EXIT_CODE=$?"
echo "=== FINAL CSV ==="
cat benchmarks/results/benchmark.csv
