# Implementation Plan: Cross-scale cuOpt vs Gurobi LP Benchmark

**Branch**: `002-benchmark-cuopt-gurobi` | **Date**: 2026-07-27 | **Spec**: ./spec.md

## Summary

Build a reproducible `benchmarks/` package that solves the max-biomass FBA LP of five
genome-scale models (e_coli_core, iML1515, Harvey, S84, S85) with cuOpt (gpuGEM default:
PDLP + PaPILO presolve) and Gurobi standalone on the identical LP, capturing time /
objective / status / residual over N=3 repeats, then emits a combined CSV, a
CSV-regenerable figure, and a results note. Runs on the GPU host base env.

## Technical Context

**Language/Version**: Python 3.13 (host base conda env)
**Primary Dependencies**: cuopt-cu12 26.6.0, gurobipy 13.0.2, cobra 0.31.1, scipy, numpy,
matplotlib; the in-repo `gpugem` package (loaders, solver, _defaults) — imported, not modified.
**Hardware**: NVIDIA RTX A4500 (20 GB); host `msp-precision`.
**LP builder (shared, single source of truth)**:
  - BiGG models (core, iML1515): `cobra.io.load_model(name)` -> `gpugem.loaders.from_cobra(model)`.
  - WBM `.mat` models (Harvey, S84, S85): repo `mwbm_loader.load_mwbm` + `build_full_lp`
    (the same builder validated bit-identical to MATLAB's problem export in prior work).
**Storage**: `benchmarks/results/*.json` (per model+solver), `benchmarks/results/benchmark.csv`
  (aggregated), `benchmarks/figures/*.png`.
**Scale**: 95 -> ~978K variables (four orders of magnitude).
**cuOpt settings**: taken verbatim from `gpugem/_defaults.py` large-model default
  (method=PDLP, presolve=PaPILO, per_constraint_residual). NOT retuned (CR-002).

## Constitution Check

- **I. Correctness-Validated Defaults**: PASS by construction — benchmark consumes shipped
  defaults, never edits `_defaults.py`; and it reports the feasibility residual next to every
  time so a "fast but wrong" result cannot masquerade as a win (CR-001).
- **II. Honest Status/Feasibility Reporting**: PASS — runner records the solver's raw status
  and fails the cell on non-optimal / residual-over-tol / objective-disagreement rather than
  coercing to "Optimal".
- **III–V**: no new defaults introduced; no change to public result semantics. No violations.

## Project Structure

```
benchmarks/
  __init__.py
  models.py            # BenchmarkModel registry: name, kind, source, objective setter
  run_benchmark.py     # CLI: --model NAME | --all, --reps 3, --force; writes JSON + CSV
  solve.py             # solve_gurobi(lp), solve_cuopt_papilo(lp); returns SolveResult
  residual.py          # ||S v - b||_inf feasibility check + objective-agreement check
  make_figure.py       # standalone: reads benchmark.csv -> figures/*.png (NO solver import)
  results/             # committed JSON + CSV outputs
  figures/             # committed figure(s)
  README.md            # one-command regen instructions
```

## Design decisions

1. **One LP, two solvers.** `run_benchmark` builds the LP once per model, asserts dims/nnz,
   hands the *same* CSC matrices + bounds + sense to both solve functions. Guarantees FR-001.
2. **Objective for .mat models.** Harvey/S84/S85 `.mat` `c` may be all-zero; the model
   registry supplies the biomass objective index/reaction following the existing
   `harvey_cuopt_benchmark.py` / `mwbm_loader` convention. BiGG models keep cobrapy's objective.
3. **Timing region.** Only the solver call is inside the timed block; load and LP-build timed
   separately. `time.perf_counter`. N=3, median reported, min/max retained (FR-003).
4. **Correctness gate (FR-004/005, CR-001).** After each solve compute residual_inf from the
   returned primal on the ORIGINAL S (pre-presolve). Fail if status != optimal, residual >
   1e-6 (documented), or |obj_cuopt - obj_gurobi|/max(1,|obj|) > 1e-6.
5. **Reproducible figure.** `make_figure.py` imports only pandas+matplotlib, reads the
   committed CSV, applies a fixed style, writes PNG. No RNG, no wall-clock in the plot. Caption
   pulls solver/GPU versions from the CSV metadata columns.
6. **Resumable --all (FR-007).** Skip a (model,solver) whose JSON exists unless --force.
7. **Provenance (FR-002).** Each JSON records source path/id, sha256 for .mat files, cobra
   model name+version, dims, nnz, solver versions, GPU name.

## Phase 0 output
research.md — resolves loader choices, cuOpt-setting provenance, residual tolerance rationale.

## Phase 1 output
data-model.md (BenchmarkModel / SolveResult / BenchmarkTable schemas),
contracts/ (result-json.schema.json, csv-columns.md), quickstart.md.

## Complexity / risks
- S85 cuOpt is expected slow (~510 s, ~984k PDLP iters — established last session). time_limit
  guards each solve; a hit-limit cell is recorded as such, not as optimal.
- SSH channel to host can hang; long `--all` run dispatched as a background job and harvested,
  not run inside one call_command.

## Progress
- [x] Constitution Check (initial) — PASS
- [ ] Phase 0 research.md
- [ ] Phase 1 data-model + contracts + quickstart
- [ ] Constitution Check (post-design)
