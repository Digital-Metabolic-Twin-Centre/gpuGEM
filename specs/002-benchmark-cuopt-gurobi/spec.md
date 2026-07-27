# Feature Specification: Cross-scale cuOpt vs Gurobi LP Benchmark

**Feature Branch**: `002-benchmark-cuopt-gurobi`
**Status**: Draft
**Created**: 2026-07-27

## Summary

Add a reproducible benchmark suite that compares the GPU LP solver (NVIDIA cuOpt,
via gpuGEM's library defaults) against Gurobi standalone on the FBA (max-biomass)
linear program of five genome-scale metabolic models spanning four orders of
magnitude in problem size: **e_coli_core**, **iML1515**, **Harvey**, **mWBM S84**,
and **mWBM S85**. The suite lives in the repository under `benchmarks/`, produces a
machine-readable results table and a publication figure, and every artifact is
regenerable from a single command with pinned inputs.

## Motivation

The project's headline claim is that a GPU solver with gpuGEM's validated defaults
is a practical alternative to a commercial solver for genome-scale FBA. That claim
is only credible if it is tested honestly across the full size range users actually
solve — from a 95-reaction teaching model to a ~10^6-variable whole-body model — on
the *same* LP handed to both solvers, with correctness verified, not just wall time.

## User Scenarios & Testing

### Primary scenario
A researcher runs `python benchmarks/run_benchmark.py --all` on a GPU host and
obtains: (a) a CSV with per-model, per-solver load/build/solve times (N repeats,
median + spread), objective values, solver status, and stoichiometric residual;
(b) a regenerable figure comparing solve time across models; (c) a short results
note. Re-running reproduces the numbers within run-to-run variance.

### Acceptance scenarios
1. **Given** a clean checkout on a host with cuOpt + Gurobi, **when** the runner is
   invoked for any single model, **then** it emits a JSON result with both solvers'
   times, objectives, status, and residual — and exits non-zero if either solver
   fails or the two objectives disagree beyond tolerance.
2. **Given** the five models, **when** `--all` runs, **then** one CSV and one figure
   are produced covering every (model, solver) cell present.
3. **Given** the produced figure, **when** the figure script is re-run against the
   committed CSV, **then** the figure is byte-reproducible (fixed style, no wall-clock
   or random elements in the plot).

## Requirements

### Functional
- **FR-001**: The suite MUST solve the max-biomass FBA LP of each of the five models
  with both cuOpt (gpuGEM large-model defaults: PDLP, PaPILO presolve, per-constraint
  residual convergence) and Gurobi standalone (barrier+crossover) on the identical LP
  produced by the repository's own LP builder (`gpugem.loaders` / repo `build_full_lp`).
- **FR-002**: Small/medium BiGG models (e_coli_core, iML1515) MUST be loaded through
  cobrapy (`cobra.io.load_model`) and converted with `gpugem.loaders.from_cobra`;
  whole-body models (Harvey, S84, S85) MUST be loaded from their `.mat` files.
  Model provenance (source, version/date, checksum) MUST be recorded.
- **FR-003**: Each solve MUST be repeated N times (default N=3); the runner MUST record
  every repeat and report the median and min/max. Times MUST be read from the timed
  region, not inferred.
- **FR-004**: For every solve the runner MUST record: objective value, solver status,
  wall time split into load / LP-build / solve, iteration count (PDLP iters for cuOpt),
  and the stoichiometric feasibility residual ||S v - b||_inf of the returned solution.
- **FR-005**: The runner MUST flag a model as FAILED (non-zero exit for that cell) if a
  solver reports non-optimal status, if the residual exceeds a documented tolerance, or
  if the two solvers' objectives disagree by more than a documented relative tolerance.
- **FR-006**: Outputs MUST be written under `benchmarks/results/` (per-model JSON + a
  combined CSV) and `benchmarks/figures/` (the comparison figure). The figure MUST be
  regenerable from the committed CSV by a standalone script with no solver dependency.
- **FR-007**: The suite MUST be runnable per-model and for `--all`, and MUST be
  resumable — an interrupted `--all` re-run skips models whose JSON already exists
  unless `--force`.

### Correctness (Constitution Principle I & II)
- **CR-001**: A speed number MUST NOT be reported for a solve that did not reach a
  verified-feasible optimal solution. Every reported time is paired with its residual
  and objective. (Honest reporting — the whole point of the project.)
- **CR-002**: The benchmark MUST NOT alter `gpugem/_defaults.py`. It consumes the
  shipped defaults; it does not tune them for the comparison.

### Key entities
- **BenchmarkModel**: name, scale class, loader kind (cobra|mat), source path/id,
  checksum, dimensions (rows, cols, nnz).
- **SolveResult**: model, solver, repeat index, load_s, build_s, solve_s, objective,
  status, iters, residual_inf.
- **BenchmarkTable**: the aggregated per-(model,solver) medians written to CSV.

## Scope
**In scope**: the five named models; the max-biomass FBA LP; cuOpt-default vs Gurobi-
standalone on the same LP; timing/objective/residual capture; one CSV + one figure +
a results note committed to the repo.
**Out of scope**: MILP/QP, knockout/FVA sweeps, the Gurobi-presolve hybrid path (may be
added as an additional column later), multi-GPU, and any change to solver defaults.

## Reproducibility contract
- Inputs pinned: model files by checksum; BiGG models by name+version through cobrapy.
- Environment pinned: solver versions (cuOpt, Gurobi) and GPU name recorded in every
  result JSON and in the figure caption.
- One-command regen for the figure from the committed CSV.

## Review & Acceptance Checklist
- [ ] Same LP handed to both solvers (builder shared, verified identical dims/nnz).
- [ ] Correctness gate (residual + objective agreement) enforced before any timing is reported.
- [ ] All five models load and solve, or the missing cell is explicitly marked, not silently dropped.
- [ ] Figure regenerates from committed CSV alone.
- [ ] No edit to `gpugem/_defaults.py`.

## Clarifications (resolved 2026-07-27)
- **C-1 → RESOLVED**: cuOpt column = **PaPILO-presolve default only** vs Gurobi standalone.
  Gurobi-presolve hybrid remains out of scope (may be a later column).
- **C-2 → RESOLVED**: **N=3** repeats per solve; report median + min/max.
- **C-3 → RESOLVED**: Harvey = `Harvey_1_03c_reduced.mat` (confirmed 81,094 vars / 56,452 mets,
  with S+C coupling; matches the historical 81K figure). NOTE: `modelReduced.c` is all-zero,
  so the runner MUST set the biomass objective explicitly for the .mat models (follow the
  existing harvey_cuopt_benchmark.py convention); cobrapy sets it automatically for BiGG models.
