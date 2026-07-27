# Tasks: Cross-scale cuOpt vs Gurobi LP Benchmark

**Feature**: 002-benchmark-cuopt-gurobi | **Input**: plan.md, spec.md, data-model.md, contracts/

## Phase 1 — Setup
- [ ] T001 Create `benchmarks/` package skeleton (`__init__.py`, `results/`, `figures/`) at repo root.
- [ ] T002 Add `benchmarks/README.md` with the one-command regen instructions from quickstart.md.

## Phase 2 — Foundational (blocking)
- [ ] T003 `benchmarks/models.py`: BenchmarkModel registry for the five models
      (name, scale, kind, source, sha256 for .mat, biomass objective). Include a
      `load_lp(model)` that returns (S, b, sense, lb, ub, c, dims) using
      `gpugem.loaders.from_cobra` (BiGG) or repo `mwbm_loader.load_mwbm`+`build_full_lp` (.mat),
      setting the biomass objective explicitly for .mat models.
- [ ] T004 `benchmarks/residual.py`: `feasibility_residual(S,b,v)` -> ||S v - b||_inf and
      `objectives_agree(o1,o2,tol)` helpers.
- [ ] T005 `benchmarks/solve.py`: `solve_gurobi(lp)` (barrier+crossover) and
      `solve_cuopt_papilo(lp)` (settings imported from `gpugem._defaults`), each returning a
      SolveResult dict (solve_s, objective, status, iters, primal v).

## Phase 3 — Runner (US1: single-model result with correctness gate)
- [ ] T006 `benchmarks/run_benchmark.py`: build LP once, assert dims/nnz, run both solvers N reps,
      compute residual per solve, enforce correctness gate (status/residual/obj-agreement),
      write per-cell JSON per the schema. `--model NAME --reps 3`.
- [ ] T007 Add provenance capture (sha256 for .mat, cobra name, solver+GPU versions, timestamp) to JSON.
- [ ] T008 Non-zero exit + explicit FAILED marker when a cell fails the gate (no time reported).

## Phase 4 — Aggregate + figure (US2/US3)
- [ ] T009 `--all` mode: iterate the registry, resumable (skip existing JSON unless `--force`),
      then aggregate all JSON into `results/benchmark.csv` per the csv-columns contract.
- [ ] T010 `benchmarks/make_figure.py`: solver-free; read committed CSV, fixed style, grouped-bar
      (or log-scale) solve-time comparison across models, caption with solver/GPU versions ->
      `figures/benchmark_solvetime.png`.

## Phase 5 — Execute + validate
- [ ] T011 Smoke test on e_coli_core + iML1515 (fast): confirm both solvers optimal, residual < 1e-6,
      objectives agree, JSON well-formed.
- [ ] T012 Full `--all --reps 3` run on the GPU host (background job); harvest results/ + figures/.
- [ ] T013 Verify figure regenerates from committed CSV alone (no solver import).
- [ ] T014 Commit `benchmarks/` (code + results + figure) to the feature branch.

## Dependencies
T003,T004,T005 block T006. T006 blocks T009. T009 (CSV) blocks T010. T011 gates T012.
T012 (CSV+JSON) blocks T013. All block T014.

## Parallelizable [P]
T004 and T005 are independent of each other (both after T003's LP interface is fixed).
