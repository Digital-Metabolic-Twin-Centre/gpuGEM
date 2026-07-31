# Contract: `results/residual_tradeoff/<model>.json` schema extension

Extends feature 005's existing `ModelComparison` JSON (see that feature's
`contracts/result-json.schema.json`) — no existing field is removed, renamed, or reinterpreted.

## New fields, under `residual_0`

```json
{
  "residual_0": {
    "configuration": "residual_0",
    "source": "fresh",
    "solve_s": 7.2,
    "iterations": 1234,
    "status": "Optimal",
    "objective": 42.0,
    "residual_inf": 156.4,
    "rows_violated": 372156,
    "time_limit": 900,

    "violation_histogram_equations": {
      "bin_edges": [1e-09, "...", 1000.0],
      "shortfall_counts": [0, "...", 0],
      "excess_counts": [0, "...", 3],
      "n_rows": 734457,
      "n_satisfied": 734454
    },
    "violation_histogram_constraints": null
  }
}
```

- `violation_histogram_equations` is always present.
- `violation_histogram_constraints` is `null` for models with no coupling block (`e_coli_core`,
  `iML1515`); an object with the same shape as `violation_histogram_equations` otherwise.
- `bin_edges` has 25 entries (24 bins); `shortfall_counts`/`excess_counts` each have 24 entries;
  `bin_edges` is identical across every model and both fields (shared, module-level constant —
  research R5), so it is safe (though redundant) to persist per-model rather than factored out to a
  companion file — this keeps each model's file self-describing and independently readable.
- Invariant: `n_satisfied + sum(shortfall_counts) + sum(excess_counts) == n_rows`.

## Compatibility / migration

A `results/residual_tradeoff/<model>.json` written before this feature (the original five models)
lacks both new fields. `run_residual_tradeoff.py::run_model()` treats such a file as needing a
one-time backfill solve (prints `[backfill]`, not `[skip]`) rather than skipping it — see
research.md R4. After that backfill runs once, the file has the same shape as a freshly-produced
one and behaves identically to `--force`'s output for every subsequent run (skip, since both new
fields are now present).

## CLI contract (unchanged from 005, reiterated for this feature's scope)

```
python -m benchmarks.run_residual_tradeoff --model NAME   # one model; NAME in ALL_MODELS (now 9)
python -m benchmarks.run_residual_tradeoff --all          # all 9; skips up-to-date files, backfills stale ones
python -m benchmarks.run_residual_tradeoff --all --force  # re-solve everything unconditionally
python -m benchmarks.aggregate_residual_tradeoff           # comparison.csv from committed JSON, no GPU
python -m benchmarks.make_residual_tradeoff_figures         # existing runtime-comparison figures, no solver
python -m benchmarks.make_violation_distribution_figures    # NEW: the two population-pyramid figures, no solver
```

No existing CLI flag changes meaning; `make_violation_distribution_figures` is a new entry point.
