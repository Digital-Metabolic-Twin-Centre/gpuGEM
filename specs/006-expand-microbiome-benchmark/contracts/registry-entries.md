# Contract: new `benchmarks/models.py` `REGISTRY` entries

Reuses `002`'s existing `contracts/result-json.schema.json` and `contracts/csv-columns.md`
unchanged (no new result schema) — this contract covers only the 4 new input entries.

Inserted into `REGISTRY` after the existing `"S85"` entry, same dict shape as every other entry:

```python
"S9":  {"scale": "microbiome", "order": 5, "kind": "mat",
        "source": str(CACHE / "mWBM_S9_male.mat"), "model_key": None, "objective": None},
"S15": {"scale": "microbiome", "order": 6, "kind": "mat",
        "source": str(CACHE / "mWBM_S15_male.mat"), "model_key": None, "objective": None},
"S23": {"scale": "microbiome", "order": 7, "kind": "mat",
        "source": str(CACHE / "mWBM_S23_male.mat"), "model_key": None, "objective": None},
"S83": {"scale": "microbiome", "order": 8, "kind": "mat",
        "source": str(CACHE / "mWBM_S83_male.mat"), "model_key": None, "objective": None},
```

- `CACHE` is `benchmarks/models.py`'s existing module-level `HERE / "model_cache"` constant
  (research R1) — no new path variable introduced.
- `ALL_MODELS = list(REGISTRY.keys())` (existing code, unmodified) automatically picks up all 4,
  which automatically extends `run_benchmark.py --model {choices}` and `--all` with zero further
  changes (both already iterate `REGISTRY`/`ALL_MODELS` generically).
- `order` continues the existing sequence (S84=3, S85=4) purely for readability of the dict
  literal; it has no effect on figure ordering after research R5's change (that now comes from
  `n_cols`).
