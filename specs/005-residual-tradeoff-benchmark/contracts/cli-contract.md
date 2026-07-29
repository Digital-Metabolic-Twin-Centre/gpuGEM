# CLI contract: `run_residual_tradeoff.py` / `aggregate_residual_tradeoff.py` / `make_residual_tradeoff_figures.py`

## `python -m benchmarks.run_residual_tradeoff`

| Flag | Default | Behavior |
|---|---|---|
| `--model NAME` | — | Run just one model (`e_coli_core`\|`iML1515`\|`Harvey`\|`S84`\|`S85`). Mutually exclusive with `--all`. |
| `--all` | — | Run every model already covered by `002`. |
| `--force` | off | Re-run a model's `residual_0` solve even if its result JSON already exists. |

**Behavior contract**:
- For each requested model: load `benchmarks/results/<model>.json` (the existing `002` result)
  and error out clearly if it's missing (this feature has nothing to compare against without it —
  it does not run `002` on the model's behalf).
- Build `shipped_default` and `gurobi` `ResidualModeResult`s directly from that existing JSON
  (research R1) — no solving.
- Skip the fresh solve (print `[skip] <model>`) if `results/residual_tradeoff/<model>.json`
  already exists and `--force` wasn't given; otherwise solve `residual_0` via
  `benchmarks.models.build_lp(model)` + `gpugem.solve(..., time_limit=<from 002's JSON>,
  per_constraint_residual=0, check_feasibility=True)`, compute `residual_inf` and `rows_violated`.
- Write `results/residual_tradeoff/<model>.json` per `contracts/result-json.schema.json`.
- After all requested models are handled, regenerate `comparison.csv` via
  `aggregate_residual_tradeoff`.

## `python -m benchmarks.aggregate_residual_tradeoff`

No flags. Reads whichever `results/residual_tradeoff/*.json` files exist, writes
`comparison.csv` per `contracts/csv-columns.md`. Standalone, no solver import.

## `python -m benchmarks.make_residual_tradeoff_figures`

No flags. Reads `results/residual_tradeoff/comparison.csv`, writes both PNGs per
`contracts/figure-contract.md`. Standalone, no solver import — the one command a reviewer without
cuOpt/Gurobi installed needs to reproduce the figures from the committed CSV.
