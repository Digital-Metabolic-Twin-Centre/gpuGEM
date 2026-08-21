# Quickstart: Version x Lifting Runtime Comparison

## Prerequisites

- Same GPU host as every prior benchmark feature (NVIDIA GPU + cuOpt 26.6.0 in the shared
  environment, Gurobi license).
- `benchmarks/results/benchmark.csv` and `specs/013-cobra-model-lifting/benchmarks/results/
  model_lifting/{e_coli_core,S85}.json` already present (both already committed from prior
  features).
- No manual venv setup required — `/tmp/cuopt-26.8-venv` is reused if present, otherwise
  provisioned automatically on first run (research.md R4).

## 1. Run the new solves (resumable; only 16 of 24 combinations are actually new — research.md R3)

```bash
python -m benchmarks.run_version_lifting_comparison            # all six in-scope models
python -m benchmarks.run_version_lifting_comparison --model S85 --force   # one model, re-solved
```

Expected: skips the 8 combinations that already exist (6 old-unlifted from `benchmark.csv`,
2 old-lifted from `specs/013-.../`), solves the remaining 16, printing `[OK]`/`[FAILED]` per
combination as it completes — matching this project's established correctness-gate reporting
convention. Given `e_coli_core`/`iML1515`/`Harvey`/`Harvetta`/`S84` are all fast under the
already-published old-version-unlifted baseline (research.md R2), most of this run's wall-clock
time is expected to be the three `S85`-involving combinations.

## 2. Regenerate the derived CSV and figure (no GPU needed — from committed results alone)

```bash
python -m benchmarks.aggregate_version_lifting_comparison
python -m benchmarks.make_extended_solvetime_figure
```

Expected: `benchmarks/results/version_lifting_comparison.csv` (10 rows, six with all five
configurations populated, four with only the original two) and an updated
`benchmarks/figures/benchmark_solvetime.png` showing five bars for each of the six in-scope
models. `benchmarks/results/benchmark.csv` and `benchmarks/make_figure.py` are unmodified by this
process (research.md R6) — running the original `python -m benchmarks.make_figure` still
regenerates today's narrower 2-bar figure unchanged, from the same underlying `benchmark.csv`.

## 3. Confirm the already-known S85 failure is carried through honestly, not hidden

```bash
python -c "
import pandas as pd
df = pd.read_csv('benchmarks/results/version_lifting_comparison.csv')
row = df[df['model'] == 'S85'].iloc[0]
print('old_lifted verified_correct:', row['cuopt_old_lifted_verified_correct'])
assert row['cuopt_old_lifted_verified_correct'] == False
print('OK: the known failure from specs/013-cobra-model-lifting/ is present, not silently dropped')
"
```

Expected: `False`, and the corresponding bar on the figure is visibly marked as a gate failure
(spec FR-004/User Story 2).

## 4. Read the narrative summary

```bash
grep -A 30 "## Version x lifting runtime comparison" benchmarks/README.md
```

Expected: for each of the six in-scope models, a plain-language statement of which configuration
is fastest and whether lifting/the version upgrade changes the answer (spec SC-003/SC-004).
