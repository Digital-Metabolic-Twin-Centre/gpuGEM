# CLI contract: `run_objective_sweep.py` / `aggregate_sweep.py`

Mirrors `benchmarks/run_benchmark.py`'s existing CLI conventions (spec FR-009 resumability).

## `python benchmarks/run_objective_sweep.py`

| Flag | Default | Behavior |
|---|---|---|
| `--objective ID` | — | Run exactly one objective from `objectives.json`. Mutually exclusive with `--all`. |
| `--all` | — | Run every objective in `objectives.json`, in file order. |
| `--reps N` | `1` | Repeats per solver per objective (spec Assumptions default). |
| `--time-limit SECONDS` | `900.0` | Per-solve cap, unchanged from `002`. |
| `--res-tol` / `--obj-tol` | `1e-4` / `1e-6` | Correctness-gate tolerances, unchanged from `002`. |
| `--force` | off | Re-solve and overwrite an objective whose result JSON already exists. |
| `--heartbeat-s` | `30` | Seconds between "...still solving" progress lines during a blocking solve (research R2). |

**Behavior contract**:
- Requires `--objective` or `--all` (error otherwise), same as `run_benchmark.py`'s `--model`/`--all`.
- For each objective to run: print a start line (`[n/total] <id> (<reaction>) — gurobi ...`),
  run Gurobi then cuOpt (heartbeat thread active during each blocking call), print a finish line
  with solve time/status per solver, write `results/s85_objectives/<id>.json`, then continue.
- Skips (prints `[skip]`, does not re-solve) any objective whose JSON already exists, unless
  `--force` — identical semantics to `run_benchmark.py`.
- After an `--all` run (or standalone via `aggregate_sweep.py`), regenerates
  `results/s85_objectives/summary.json` and `summary.csv` from whatever per-objective JSON files
  are present, so a partial/resumed run always has an up-to-date summary.
- Exit code non-zero if any *attempted* objective in this invocation failed the correctness gate
  (`both_feasible = false`), matching `run_benchmark.py`'s `any_failed` behavior — pre-existing
  failed results from a prior run are reported but don't fail a `--force`-less resume.

## `python benchmarks/aggregate_sweep.py`

No flags. Reads every `results/s85_objectives/*.json` (excluding `objectives.json` and
`summary.json` itself), writes `summary.json` + `summary.csv` per data-model.md's SweepSummary.
Runnable standalone (no solver import), same "regenerable from committed results" property as
`002`'s `make_figure.py`.
