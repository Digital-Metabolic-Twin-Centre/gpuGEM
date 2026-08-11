# CLI contract: `run_gurobi_default_benchmark.py` / `aggregate_gurobi_default.py` / `make_gurobi_default_figure.py`

## `python -m benchmarks.run_gurobi_default_benchmark`

| Flag | Default | Behavior |
|---|---|---|
| `--model NAME` | — | Run just one model (any key in `benchmarks.models.REGISTRY`). Mutually exclusive with `--all`. |
| `--all` | — | Run every model already covered by the main cuOpt-vs-Gurobi comparison. |
| `--force` | off | Re-run a model's default-settings solve even if its result JSON already exists. |

**Behavior contract**:
- For each requested model: load `benchmarks/results/<model>.json` (the existing cuOpt +
  deliberately-configured-Gurobi result) and error out clearly if it's missing — this feature has
  nothing to compare against without it, and does not solve on the model's behalf.
- Never re-solve or modify the reused cuOpt/Gurobi entries from that file (spec FR-004).
- Skip the fresh solve (print `[skip] <model>`) if `results/gurobi_default/<model>.json` already
  exists and `--force` wasn't given; otherwise solve via
  `benchmarks.models.build_lp(model)` + `benchmarks.solve.solve_gurobi(lp, time_limit=<from the
  existing JSON>, method=-1)` (research R1) — Gurobi's own untouched factory default, no other
  performance-tuning parameter set.
- Apply the same correctness gate already used for every other recorded result (solver status,
  feasibility-residual tolerance via `benchmarks.residual.feasibility_residual`, cross-solver
  objective agreement against the model's already-recorded cuOpt objective) — spec FR-002/003.
  A failed gate is still written to disk with `feasible: false` / `obj_agree_with_cuopt: false`,
  never silently dropped.
- Derive `solved_by` from `bar_iters`/`simplex_iters` (research R2): `"barrier"` if
  `bar_iters > 0` else `"simplex"`.
- Write `results/gurobi_default/<model>.json` per `data-model.md`'s `GurobiDefaultResult`.
- After all requested models are handled, regenerate `comparison.csv` via
  `aggregate_gurobi_default`.

## `python -m benchmarks.aggregate_gurobi_default`

No flags. Reads whichever `results/gurobi_default/*.json` files exist, joins each against its
model's existing `results/<model>.json` for the reused `cuopt_*`/`gurobi_barrier_*` columns,
writes `comparison.csv` per `contracts/csv-columns.md`. Standalone, no solver import (spec FR-007).

## `python -m benchmarks.make_gurobi_default_figure`

No flags. Reads `results/gurobi_default/comparison.csv`, writes
`benchmarks/figures/gurobi_default_comparison.png` per `contracts/figure-contract.md`. Standalone,
no solver import — the one command a reviewer without cuOpt/Gurobi installed needs to reproduce
the figure from the committed CSV.
