# Quickstart: Constraint-Residual Speed/Correctness Trade-off Benchmark

## Prerequisites

- `002`'s existing results present: `benchmarks/results/{e_coli_core,iML1515,Harvey,S84,S85}.json`
  (this feature reads these, never regenerates them — if any is missing, run `002`'s
  `run_benchmark.py --all` first).
- GPU host with cuOpt for the fresh `residual_0` solves. Gurobi is **not** required — its results
  are reused, never re-solved.

## 1. Sanity-check one model before running all five

```bash
python -m benchmarks.run_residual_tradeoff --model S85
```

Expected: prints the `shipped_default`/`gurobi` figures pulled straight from `002`'s existing
`S85.json` (should read `~511s` / `~55s` respectively, matching the already-trusted numbers), then
solves `residual_0` fresh and prints something close to the investigation's original finding
(`~6.5s`, `residual_inf` in the hundreds — a large number is *expected and correct* here, not a
bug). Writes `results/residual_tradeoff/S85.json`.

## 2. Run the registry/comparison-math tests (no GPU required)

```bash
pytest tests/test_residual_tradeoff.py -v
```

Expected: passes — confirms the comparison-assembly logic correctly merges reused `002` data with
a fresh result, and that `rows_violated` is `null` for reused configurations (never fabricated),
per data-model.md's validation rules.

## 3. Run the remaining four models

```bash
python -m benchmarks.run_residual_tradeoff --all
```

Expected: `[skip] S85` (already done in step 1) plus fresh `residual_0` solves for the other four
— all small/fast except S84 (microbiome scale, expect this to take at least as long as its
`002`-recorded shipped-default time).

## 4. Regenerate the comparison table and figures

```bash
python -m benchmarks.aggregate_residual_tradeoff
python -m benchmarks.make_residual_tradeoff_figures
```

Expected: `results/residual_tradeoff/comparison.csv` (15 rows: 5 models x 3 configurations) and
both PNGs under `benchmarks/figures/`. Open `residual_tradeoff_violations.png` and confirm: (a)
log-scale y-axis, (b) `residual_0` bars visually distinct (hatched) from the other two, (c) the
non-recommendation caption is present and legible on the figure itself, (d) S85's three violation
values are visibly different by orders of magnitude, matching the original investigation
(`~8.9e-05` shipped-default vs `~156` for `residual_0`).

## 5. Confirm no shipped default changed

```bash
git diff --stat gpugem/_defaults.py
```

Expected: no output — this feature never touches shipped defaults, regardless of what the
comparison shows (spec FR-009, SC-002).
