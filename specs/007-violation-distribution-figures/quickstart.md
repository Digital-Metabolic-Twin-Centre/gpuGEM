# Quickstart: Violation Distribution Figures

## Prerequisites

- All nine models' `benchmarks/results/<model>.json` (feature 002/006) already committed.
- GPU + cuOpt + Gurobi available only for the solve step; figure regeneration needs neither.

## Produce/backfill the `per_constraint_residual=0` results (GPU required)

```bash
cd ~/projects/gpuGEM && conda activate base
python -m benchmarks.run_residual_tradeoff --all
```

Expected: `[skip]` for any of the nine already up-to-date, `[backfill]` for the original five (one
time only, adds the new histogram fields), fresh solves for S9/S15/S23/S83. Ends by calling
`aggregate_residual_tradeoff` automatically (existing `--all` behavior), producing
`results/residual_tradeoff/comparison.csv` with 27 rows (9 models x 3 configurations).

## Regenerate all figures (no GPU/solver needed)

```bash
python -m benchmarks.make_residual_tradeoff_figures        # runtime comparison, now 9 models
python -m benchmarks.make_violation_distribution_figures    # the two new population-pyramid figures
```

## Validate

1. `results/residual_tradeoff/comparison.csv` has 27 rows; every model appears with all three
   configurations (SC-001).
2. `figures/violation_distribution_equations.png` shows all nine models' distributions overlaid,
   each individually visible and labeled by name (SC-002).
3. `figures/violation_distribution_constraints.png` shows exactly the seven models with a coupling
   block (`e_coli_core`/`iML1515` absent) (SC-003).
4. Deleting `figures/*.png` and rerunning only the two `make_*` commands above (no solver installed)
   regenerates both new figures byte-for-byte from the committed JSON (SC-004).
5. `git diff gpugem/` is empty — no shipped default changed (SC-005).
