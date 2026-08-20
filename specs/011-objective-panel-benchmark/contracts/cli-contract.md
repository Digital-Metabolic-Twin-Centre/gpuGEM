# CLI contract: `run_objective_panel.py` / `aggregate_objective_panel.py` / `make_objective_panel_figures.py`

## `python -m benchmarks.run_objective_panel`

| Flag | Default | Behavior |
|---|---|---|
| `--model NAME` | — | Run just one model (any key in `benchmarks.models.REGISTRY`). Mutually exclusive with `--all`. |
| `--all` | — | Run every model in the registry. |
| `--reps N` | `3` | Repeats per (objective, solver) combination. Matches every model's already-published `reps` (research R1) -- override only for a deliberately smaller/larger check. |
| `--force` | off | Re-run an (model, objective) combination even if its result JSON already exists. |
| `--heartbeat-s S` | `30.0` | Seconds between progress prints during a single long solve (research R4). |

**Behavior contract**:
- For each requested model: read `benchmarks/objective_candidates/<model>.csv` and error out clearly if
  it's missing (this feature has nothing to run without a curated panel -- it never invents objectives).
- For each `reaction_id` row in that panel, in file order: skip (print `[skip] <model>/<objective_id>`) if
  `results/objective_panel/<model>/<objective_id>.json` already exists and `--force` wasn't given (research
  R4/FR-011); otherwise build the LP with that reaction as the sole objective (research R2), solve with both
  Gurobi (this model's already-published deliberately-configured setting) and cuOpt (this model's already
  -published shipped setting), `--reps` times each, exactly as `results/<model>.json` already did for its one
  objective -- never a different setting (FR-002).
- Apply the correctness gate per repeat, `all()`-reduced per solver (research R7) -- never gated on the
  median alone.
- Write `results/objective_panel/<model>/<objective_id>.json` per `data-model.md`'s `ObjectivePanelResult`.
- After all requested (model, objective) combinations for a `--model` run, or after every model for an
  `--all` run, call `aggregate_objective_panel.main()`.

## `python -m benchmarks.aggregate_objective_panel`

No flags. Reads whichever `results/objective_panel/<model>/*.json` files exist, writes both
`objective_runtime.csv` and `benchmark_details.csv` per `contracts/csv-columns.md`. Standalone, no solver
import (spec FR-007 implies this must regenerate without re-solving).

## `python -m benchmarks.make_objective_panel_figures`

No flags. Reads `results/objective_panel/objective_runtime.csv` and `benchmark_details.csv` (for the
failed-gate marking), writes one `benchmarks/figures/objective_panel_<model>.png` per model that has at
least one result. Standalone, no solver import -- the one command a reviewer without cuOpt/Gurobi installed
needs to reproduce every figure from the committed CSVs (FR-008).
