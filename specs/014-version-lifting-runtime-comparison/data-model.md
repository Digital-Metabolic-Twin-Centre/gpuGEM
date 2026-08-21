# Phase 1 Data Model: Version x Lifting Runtime Comparison

## RuntimeConfiguration

One (model, cuOpt version, lifted/unlifted) combination's result. Two already exist per model
today (Gurobi, current-version-unlifted-cuOpt, both already in `benchmark.csv`); this feature adds
up to three more per in-scope model.

| Field | Type | Notes |
|---|---|---|
| `model` | `str` | |
| `cuopt_version` | `str` | e.g. `26.06.00` or `26.08.00` |
| `lifted` | `bool` | |
| `solve_s_median` | `float` | Reused verbatim where an existing result covers this combination (research.md R3) |
| `status` | `str` | |
| `objective` | `float \| None` | |
| `residual_inf` | `float \| None` | Against the model's *original* system, even when `lifted=True` (matches `gpugem.solve`'s own existing `lift=True` feasibility contract from `specs/013-cobra-model-lifting/`) |
| `verified_correct` | `bool` | Same gate definition as every other benchmark in this project (research.md R7) — never a looser or different one for this feature's new numbers |
| `source` | `"benchmark.csv" \| "model_lifting" \| "version_lifting"` | Which existing or newly-produced artifact this row's data came from — kept for traceability, not just convenience |

## ExtendedComparisonRow (one row of the derived CSV)

| Column | Type | Notes |
|---|---|---|
| `model` | `str` | Every model already in `benchmark.csv` (10 total) |
| `n_cols` | `int` | Carried through unchanged, for consistent sort order with the original figure |
| `gurobi_solve_s_median` | `float` | Unchanged, from `benchmark.csv` |
| `cuopt_old_unlifted_solve_s_median` | `float` | Renamed copy of `benchmark.csv`'s existing `cuopt_solve_s_median` — same number, clearer name now that there are four cuOpt columns |
| `cuopt_old_unlifted_verified_correct` | `bool` | Renamed copy of `benchmark.csv`'s existing `both_feasible` |
| `cuopt_new_unlifted_solve_s_median` | `float \| NaN` | New; `NaN` for the four out-of-scope models |
| `cuopt_new_unlifted_verified_correct` | `bool \| NaN` | New |
| `cuopt_old_lifted_solve_s_median` | `float \| NaN` | New; reused from `specs/013-.../results/model_lifting/*.json` for `e_coli_core`/`S85` |
| `cuopt_old_lifted_verified_correct` | `bool \| NaN` | New; **`False`** for `S85` — an already-known, honestly-carried-through failure (research.md R3), not a fresh finding |
| `cuopt_new_lifted_solve_s_median` | `float \| NaN` | New |
| `cuopt_new_lifted_verified_correct` | `bool \| NaN` | New |

A model absent from the six in-scope models has every `*_new_*`/`*_old_lifted_*` column `NaN` —
the figure script's fallback (research.md R6) renders exactly today's 2-bar view for that row.

## VersionLiftingResult (one `results/version_lifting/<model>.json`)

Only written for the six in-scope models; only contains whichever of the three "must be freshly
solved" configurations (research.md R3) that model actually needed (e.g. `e_coli_core` only needs
`new_unlifted` and `new_lifted` fresh, since its `old_lifted` already exists from `specs/013-...`).

| Field | Type | Notes |
|---|---|---|
| `model` | `str` | |
| `new_unlifted` | `RuntimeConfiguration \| null` | |
| `old_lifted` | `RuntimeConfiguration \| null` | |
| `new_lifted` | `RuntimeConfiguration \| null` | |
