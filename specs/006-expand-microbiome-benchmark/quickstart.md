# Quickstart: Expand Cross-Scale Benchmark to Additional Microbiome Models

## Prerequisites

- Same GPU host and environment as `002`-`005`.
- The 4 new model files already present at `benchmarks/model_cache/mWBM_{S9,S15,S23,S83}_male.mat`
  (confirmed present, ~637MB total across all 8 plain+lifted files).
- Existing 5 models' results already committed: `benchmarks/results/{e_coli_core,iML1515,Harvey,
  S84,S85}.json` (this feature must not alter these).

## 1. Confirm the new models are protected from accidental commit

```bash
git status --short benchmarks/model_cache/
```

Expected: no output for the `.mat` files (gitignored) — only ever shows something if a genuinely
new, not-yet-ignored file type appears there.

## 2. Confirm the existing 5 models are untouched before starting

```bash
git diff --stat benchmarks/results/e_coli_core.json benchmarks/results/iML1515.json \
  benchmarks/results/Harvey.json benchmarks/results/S84.json benchmarks/results/S85.json
```

Expected: no output (these files aren't even modified yet at this point — this is the "before"
baseline to compare against after step 3).

## 3. Run one new model first as a sanity check

```bash
python -m benchmarks.run_benchmark --model S9 --reps 3
```

Expected: `[OK] S9  gurobi=...s (Optimal)  cuopt=...s (Optimal)  ...` (or `[FAILED]` with a clear
reason if the correctness gate isn't met — either outcome is a valid, informative result per spec
FR-003). Writes `benchmarks/results/S9.json`.

## 4. Run the remaining three

```bash
python -m benchmarks.run_benchmark --model S15 --reps 3
python -m benchmarks.run_benchmark --model S23 --reps 3
python -m benchmarks.run_benchmark --model S83 --reps 3
```

Or equivalently, once all 4 are ready to run unattended: `python -m benchmarks.run_benchmark --all`
(the existing skip-if-exists behavior means any of S9/S15/S23/S83 already done in step 3 won't be
re-solved, and none of the 5 existing models will be touched since their result files already
exist).

## 5. Confirm the 5 existing models are still untouched

```bash
git diff --stat benchmarks/results/e_coli_core.json benchmarks/results/iML1515.json \
  benchmarks/results/Harvey.json benchmarks/results/S84.json benchmarks/results/S85.json
```

Expected: still no output (spec FR-007/SC-003).

## 6. Regenerate the CSV and figure

```bash
python -m benchmarks.run_benchmark --all   # also regenerates benchmark.csv via aggregate_csv()
python -m benchmarks.make_figure           # no GPU/solver needed
```

Expected: `benchmarks/results/benchmark.csv` has 9 rows; `benchmarks/figures/benchmark_solvetime.png`
shows all 9 models, ordered strictly by variable count (e_coli_core, iML1515, Harvey, S84, S85,
then S9/S15/S23/S83 in ascending size order among themselves), each model's true dimensions in its
axis label as before.

## 7. Confirm no shipped default changed

```bash
git diff --stat gpugem/_defaults.py
```

Expected: no output (spec FR-008).
