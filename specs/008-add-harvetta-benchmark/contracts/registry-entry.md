# Contract: `REGISTRY["Harvetta"]`

```python
"Harvetta": {
    "scale": "whole-body", "order": 9, "kind": "mat",
    "source": str(CACHE / "Harvetta_1_03d.mat"),
    "model_key": "female",
    "objective": "Whole_body_objective_rxn",
},
```

Consumed unchanged by `benchmarks/models.py::build_lp`'s existing `kind == "mat"` branch — no new
loader code, no new branch, no signature change (research R1/R2). Placed after `S83` in dict
literal order for readability; position has no effect on any figure (both `make_figure.py` and
`make_residual_tradeoff_figures.py` sort by solved `n_cols`).

## CLI contract (unchanged — reiterated for this feature's scope)

```
python -m benchmarks.run_benchmark --model Harvetta --reps 3       # cross-scale (002)
python -m benchmarks.run_benchmark --all --reps 3                  # all 10, resumable
python -m benchmarks.make_figure                                    # regenerate, no GPU

python -m benchmarks.run_residual_tradeoff --model Harvetta         # trade-off (005/007)
python -m benchmarks.run_residual_tradeoff --all                    # all 10, resumable/backfilling
python -m benchmarks.aggregate_residual_tradeoff                    # comparison.csv, no GPU
python -m benchmarks.make_residual_tradeoff_figures                 # regenerate, no solver
python -m benchmarks.make_violation_distribution_figures            # regenerate, no solver
```

No existing flag changes meaning; `--model Harvetta` is a new valid choice for the two `--model`
flags, following automatically from the `REGISTRY`/`ALL_MODELS` addition (no `argparse` choices
list needs manual updating beyond what already reads from `M.ALL_MODELS`).
