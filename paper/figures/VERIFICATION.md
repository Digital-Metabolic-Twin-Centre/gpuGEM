# Verification against the published figures

Each script in this directory was run and its PDF compared against the
figure file currently shipped with the manuscript. Two things were checked:
the numbers (every plotted value re-derived from `benchmarks/results/` and
compared against the figure-level intermediates) and the rendered page (all
text extracted from both PDFs and compared token by token, plus page
geometry).

| Figure | Page, published → regenerated (pt) | Text | Difference |
| --- | --- | --- | --- |
| Fig. 1 | 790.2 × 626.5 → 790.2 × 626.5 | identical | none, see note 1 |
| Fig. S1 | 514.2 × 195.6 → 514.1 × 195.8 | identical | none |
| Fig. S2 | 497.5 × 468.5 → 496.4 × 468.4 | identical | none |
| Fig. S3 | 519.6 × 222.9 → 519.6 × 222.9 | one extra tick label, `1.4` | see note 2 |
| Fig. S4 | 454.2 × 382.0 → 453.0 × 381.9 | same tokens, different draw order | none |

Sub-point page differences are the normal variation in a tight bounding box
across matplotlib and font versions.

## Numerical check

Every value reproduces from the committed primary results, column by
column, with one exception.

- Fig. 1a/b, Fig. S1, Fig. S2, Fig. S4 — reproduce exactly from
  `benchmark.csv` and `highs_baseline/highs_baseline.json`.
- Fig. 1c — reproduces exactly from `residual_tradeoff/comparison.csv`.
- Fig. 1d, Fig. S3 — reproduce exactly from
  `objective_panel/objective_runtime.csv` joined to
  `objective_panel/benchmark_details.csv`. The dispersion annotations
  recomputed as 3.79 % and 8.99 %, matching the published `CV = 3.8%` and
  `CV = 9.0%`.
- **Exception:** the HiGHS interior-point series in Fig. 1a/b is not derivable
  from anything committed. See note 3.

The bar ordering in Fig. S3a was recovered rather than assumed: the 50 bar
rectangles were extracted from the published PDF, classified by fill colour,
and the resulting class sequence matched — exactly — the committed runtimes
sorted by gpuGEM solve time descending. Bar lengths are proportional to the
committed values at 0.4031 pt/s.

## Note 1 — Figure 1 reproduces the embedded render, not a later revision

A more compact 7.01 × 5.20 in typesetting of this figure exists. The
version the manuscript embeds is the 10.975 × 8.701 in render, included at
`scale 50`, and that is what `make_fig1.py` reproduces: page size, the four
axes rectangles (within 0.3 pt), extracted text and the font-size census of
the whole page all match the published PDF. Page geometry and type sizes in
the script were measured off that PDF, so editing them will move the figure
away from what the manuscript shows.

## Note 2 — the published Fig. S3b clips its highest point

The published panel b has y limits of roughly (0.780, 1.380), but the
normalised solve times reach 1.4229. The slowest objective therefore falls
outside the axes and is not visible in the published figure.
`make_figS3.py` lets the axis autoscale, so all 50 points are drawn and a
`1.4` tick appears. This is the only content difference between the
published figure and the regenerated one.

## Note 3 — the HiGHS interior-point series is carried, not derived

Only the method comparison for the four public models was committed
(`highs_baseline/highs_method_blocks.csv`); the six personalised-model
interior-point runs were never written to the repository. Their values live
in `data/highs_ipm_fig1.csv` with provenance in the file header, and
`README.md` records the command that regenerates them.

## Reconstructed scripts

`make_figS1.py` and `make_figS3.py` had no surviving generator. Their
layout, palette, annotation placement and panel geometry were measured off
the published PDFs: page size and axes rectangles from the content streams,
colours from the fill and stroke operators, legend and annotation positions
from text bounding boxes, and the Fig. S1b shaded span from its path
coordinates mapped back through the fitted log axis (8.0 × 10⁴ to
6.9 × 10⁵ variables). Cosmetic details may still differ marginally.
