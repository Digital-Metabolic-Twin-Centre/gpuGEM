# Quickstart: Gurobi Default-Settings Benchmark Across All Models

## Prerequisites

- This project's existing `benchmarks/` environment, with every model's `results/<model>.json`
  already present (the existing cuOpt-vs-Gurobi comparison must have already been run).
- Gurobi installed and licensed, only if producing fresh results (`run_gurobi_default_benchmark`).
  Regenerating the CSV or figure from committed results needs neither Gurobi nor cuOpt.

## Produce results for every model

```sh
python -m benchmarks.run_gurobi_default_benchmark --all
```

Expected: one `benchmarks/results/gurobi_default/<model>.json` per model in the suite. A model
already having a result is skipped (printed as `[skip] <model>`) unless `--force` is passed.
Re-running does not alter any model's existing `results/<model>.json` (spec FR-004/SC-002) —
verify with `git diff --stat benchmarks/results/*.json` showing no changes to those files.

## Produce results for a single model

```sh
python -m benchmarks.run_gurobi_default_benchmark --model e_coli_core
```

Expected: `benchmarks/results/gurobi_default/e_coli_core.json` written/updated; no other model's
files touched.

## Regenerate the comparison view

```sh
python -m benchmarks.aggregate_gurobi_default
```

Expected: `benchmarks/results/gurobi_default/comparison.csv` with one row per model, all three
configurations' solve times/statuses side by side (spec FR-005, User Story 2 acceptance scenario
1). Runs without Gurobi or cuOpt installed (spec FR-007/SC-003) — verify by running in an
environment with neither importable.

## Regenerate the figure

```sh
python -m benchmarks.make_gurobi_default_figure
```

Expected: `benchmarks/figures/gurobi_default_comparison.png` regenerated from the committed CSV
alone. Byte-for-byte reproducible across runs with the same CSV.

## Validate the correctness gate is enforced, not bypassed

Inspect any model's `results/gurobi_default/<model>.json`: it MUST include `feasible` and
`obj_agree_with_cuopt` booleans (spec FR-002/003). To exercise the failure path deliberately,
temporarily lower a model's `time_limit` far enough that the default-settings solve can't reach
optimality, re-run with `--force`, and confirm the model still appears in `comparison.csv` with
`gurobi_default_feasible=False` rather than being dropped — then revert the temporary change.

## Validate no shipped-default solver behavior changed

```sh
git diff gpugem/_defaults.py
```

Expected: no output (spec FR-008/SC-004) — this feature only reads Gurobi's own factory default
via an argument value, it never touches this project's shipped defaults.
