# CLI Contract: Version x Lifting Runtime Comparison

## `python -m benchmarks._version_lifting_worker`

Subprocess entry point, never invoked directly by a user (research.md R5).

```text
--model NAME          one of the six in-scope models
--lift / --no-lift     whether to solve with gpugem.solve(lift=True)
--time-limit SECONDS   default 900.0
```

Prints one JSON `RuntimeConfiguration`-shaped object to stdout (last line).

## `python -m benchmarks.run_version_lifting_comparison`

```text
--model NAME             one of the six in-scope models; repeatable, default: all six
--upgrade-venv PATH      default /tmp/cuopt-26.8-venv; provisioned automatically if missing
                          (research.md R4) using the exact command already established in
                          specs/012-cuopt-native-tuning/
--force                  re-run a combination whose result already exists
--time-limit SECONDS     default 900.0
```

For each requested model, determines (research.md R3) which of the three additional
configurations are missing, launches `_version_lifting_worker` under the appropriate interpreter
for each, and writes `benchmarks/results/version_lifting/<model>.json`. Skips a combination whose
result already exists (in either this feature's own output or an already-published prior
artifact) unless `--force`. Calls `aggregate_version_lifting_comparison.main()` at the end.

## `python -m benchmarks.aggregate_version_lifting_comparison`

No arguments. Reads `benchmark.csv` (unchanged) + `results/version_lifting/*.json` +
`specs/013-.../results/model_lifting/{e_coli_core,S85}.json`, writes
`benchmarks/results/version_lifting_comparison.csv`. No GPU/solver required — regenerable from
committed results alone, matching this project's established convention.

## `python -m benchmarks.make_extended_solvetime_figure`

No arguments. Reads `version_lifting_comparison.csv`, writes
`benchmarks/figures/benchmark_solvetime.png` (research.md R6 — same output filename as the
original `make_figure.py`, which remains independently runnable and unmodified). No GPU/solver
required.
