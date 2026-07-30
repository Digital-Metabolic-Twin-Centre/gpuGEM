# Contract: `.gitignore` addition and `make_figure.py` ordering change

## `.gitignore`

Add one line:

```gitignore
benchmarks/model_cache/*.mat
```

- Scoped to `.mat` only — `benchmarks/model_cache/*.xml` (the existing, intentionally-tracked
  `e_coli_core.xml`/`iML1515.xml` BiGG caches) are unaffected (research R2).
- Applies to all 8 files currently in `benchmarks/model_cache/` (4 new plain `.mat` + their
  `_lifted` siblings, out of scope per spec Assumptions but still covered so they can't be
  accidentally committed either) and any future `.mat` added there.

## `make_figure.py` ordering

Before:
```python
SCALE_ORDER = ["small", "medium", "whole-body", "microbiome"]
df["_sc"] = df["scale"].map({s: i for i, s in enumerate(SCALE_ORDER)})
df = df.sort_values(["_sc", "n_cols"]).reset_index(drop=True)
```

After:
```python
df = df.sort_values("n_cols").reset_index(drop=True)
```

- `SCALE_ORDER` and the `_sc` column are removed entirely — nothing else in `make_figure.py`
  references them (verified: `_sc` is used only for this sort).
- For the 5 models already benchmarked, this produces byte-identical bar ordering to today
  (research R5 — size already increases monotonically with scale class in the existing set), so
  the visual change is additive (4 new bars appended in size order) rather than a reshuffle of
  familiar bars.
