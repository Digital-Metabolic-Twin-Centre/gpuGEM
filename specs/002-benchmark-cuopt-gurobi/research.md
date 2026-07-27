# Research: Cross-scale cuOpt vs Gurobi benchmark

## D1. Loader per model class
- **Decision**: BiGG models via `cobra.io.load_model` + `gpugem.loaders.from_cobra`; WBM .mat
  via repo `mwbm_loader.load_mwbm` + `build_full_lp`; Harvey via the reduced .mat.
- **Rationale**: uses the repository's own conversion code (single source of truth, already
  validated bit-identical to MATLAB export), so the benchmark measures gpuGEM's real path.
- **Alternatives**: hand-rolling S/bounds from raw .mat (rejected -- would not test the shipped
  loader and risks a different LP than users get).

## D2. cuOpt settings provenance
- **Decision**: copy the large-model default dict from `gpugem/_defaults.py` at runtime
  (import it), do not inline literals.
- **Rationale**: CR-002 -- the benchmark must track the shipped default even if it changes.

## D3. Objective for .mat models
- **Decision**: model registry stores the biomass objective (reaction id / column index) per
  .mat model, set explicitly; verified `modelReduced.c` is all-zero for Harvey.
- **Rationale**: an all-zero objective silently makes any feasible point "optimal" with obj 0 --
  exactly the false-optimal trap Principle II warns about.

## D4. Feasibility residual + tolerances
- **Decision**: residual = ||S v - b||_inf on the ORIGINAL (pre-presolve) system; fail cell if
  > 1e-6. Objective agreement: relative diff > 1e-6 fails.
- **Rationale**: presolve/postsolve tolerance bugs are the documented failure mode this project
  exists to catch; checking on the original system is the honest test.

## D5. Reproducibility mechanics
- **Decision**: figure regenerates from committed CSV via a solver-free script; inputs pinned by
  sha256 (.mat) and cobra model name (BiGG); solver+GPU versions embedded in every JSON and the
  CSV, surfaced in the figure caption.
- **Rationale**: FR-006 + reproducibility contract; a reviewer can rebuild the figure without a GPU.
