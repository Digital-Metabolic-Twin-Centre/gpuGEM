# Phase 1 Data Model: Expand Cross-Scale Benchmark to Additional Microbiome Models

No new entity types — this feature adds rows to structures `002` already defines. Matches spec.md's
Key Entities.

## BenchmarkModel (4 new REGISTRY entries)

Same shape as every existing entry in `benchmarks/models.py`'s `REGISTRY` dict.

| Field | S9 | S15 | S23 | S83 |
|---|---|---|---|---|
| `scale` | `microbiome` | `microbiome` | `microbiome` | `microbiome` |
| `order` | 5 | 6 | 7 | 8 (order only affects the unused legacy scale-grouping path; figure ordering now comes from `n_cols`, research R5) |
| `kind` | `mat` | `mat` | `mat` | `mat` |
| `source` | `benchmarks/model_cache/mWBM_S9_male.mat` | `.../mWBM_S15_male.mat` | `.../mWBM_S23_male.mat` | `.../mWBM_S83_male.mat` |
| `model_key` | `None` | `None` | `None` | `None` |
| `objective` | `None` | `None` | `None` | `None` (research R3 — confirmed each ships its own single-nonzero `Whole_body_objective_rxn` in `c`) |

**Validation rules** (enforced implicitly by `benchmarks.models.build_lp`'s existing logic, no new
code): `source` path must exist and be loadable via `gpugem.loaders.from_mat`; provenance
(`n_cols`, `n_eq_rows`, `n_total_rows`, `nnz`, `sha256`) is computed automatically the same way as
every other `.mat`-kind entry — no manual entry of dimensions needed or wanted (avoids the two
diverging if the source file ever changes).

## SolveResult (unchanged shape, 4 new instances per solver)

Identical to the existing `results/<model>.json` schema (`gurobi`/`cuopt` blocks, each with
`repeats`, `solve_s_median/min/max`, `objective`, `feasible`) — already documented in `002`'s
`contracts/result-json.schema.json`. This feature produces 4 new files matching that exact schema;
no schema change.

## BenchmarkComparison (regenerated, not new)

`benchmarks/results/benchmark.csv` — same columns as today (`002`'s `contracts/csv-columns.md`),
now with 9 rows instead of 5. The only structural change is the ordering the figure derives from
it (research R5): `n_cols` ascending, no scale-class grouping.

**Validation rule**: `benchmark.csv` MUST have exactly 9 rows after this feature (5 existing +
4 new) whenever regenerated with all 9 having results — a model missing from the CSV is a build
error per spec SC-002, not a silently incomplete comparison.
