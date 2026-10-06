# Manuscript figures

Every figure in the paper and its supplement is regenerated here from the
benchmark results committed under `benchmarks/results/`.

```bash
bash paper/figures/make_all.sh            # -> paper/figures/output/
python paper/figures/make_fig1.py --outdir /tmp/figs
```

Requirements: `pandas` and `matplotlib`. Nothing here solves an LP, so no
GPU, no CUDA toolkit and no commercial solver licence are needed. Each
script writes PNG, PDF and EPS; the manuscript embeds the PDF.

## What each script draws, and from what

| Script | Figure | Inputs |
| --- | --- | --- |
| `make_fig1.py` | Fig. 1 — solve time, speed-up, residual/time trade-off, iteration counts | `benchmarks/results/benchmark.csv`, `highs_baseline/highs_baseline.json`, `residual_tradeoff/comparison.csv`, `data/highs_ipm_fig1.csv` |
| `make_figS1.py` | Fig. S1 — scaling and speed-up | `benchmark.csv`, `highs_baseline/highs_baseline.json` |
| `make_figS2.py` | Fig. S2 — objective agreement and constraint residuals | `benchmark.csv`, `highs_baseline/highs_baseline.json` |
| `make_figS3.py` | Fig. S3 — 50-objective panel on PMM2 | `objective_panel/objective_runtime.csv`, `objective_panel/benchmark_details.csv` |
| `make_figS4.py` | Fig. S4 — solve time against PDLP iteration count | `benchmark.csv` |

`_common.py` holds the loaders, the palette and the save routine.

## Model labelling

The six personalised microbiome models are numbered **PMM1–PMM6 in ascending
size order**, and the sample-ID to label mapping lives in
`data/pmm_model_mapping.csv`. Scripts take labels from
`_common.labels_for()`, which asserts that the numbering is still in
ascending size order, rather than hard-coding them. A renumbering therefore
requires editing one CSV, and no figure can silently fall out of step with
the text. Where a script needs per-model annotation geometry (`PLACE` in
`make_figS4.py`), it is keyed by **sample ID**, not by paper label, for the
same reason.

## Two caveats on provenance

**1. The HiGHS interior-point series in Fig. 1 is not reproducible from
`benchmarks/results/`.** Only the method-comparison subset for the four
public models was committed, in
`highs_baseline/highs_method_blocks.csv`. The six personalised-model runs
were never written to the repository, so the values used by the figure are
carried in `data/highs_ipm_fig1.csv` with their provenance recorded in the
file header. To regenerate them from scratch:

```bash
python benchmarks/run_highs_baseline.py --repo . \
    --models Harvey Harvetta S84 S85 S23 S15 S9 S83 \
    --method ipm --out highs_ipm.json
```

**2. `make_figS1.py` and `make_figS3.py` are reconstructions.** No generator
for those two figures existed in the repository. The plotted *values* come
from the committed results and reproduce the published figures; the layout,
palette, annotation placement and panel geometry were measured off the
published PDFs. Cosmetic details may differ marginally from the originals.
`VERIFICATION.md` records what was compared and what differs.
