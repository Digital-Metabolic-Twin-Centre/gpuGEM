# Quickstart: Colorblind-Friendly, Clearly-Layered Violation Distribution Figures

## Prerequisites

None beyond what's already committed — this is a rendering-only change reading existing
`benchmarks/results/residual_tradeoff/*.json`. No GPU, no solver.

## Regenerate the figures

```bash
cd ~/projects/gpuGEM && conda activate base
python -m benchmarks.make_violation_distribution_figures
```

## Validate

1. Run the new unit test(s) for `_ordinal_ramp` (`pytest tests/test_violation_histogram.py -k ramp`
   or wherever they land) — confirms monotone lightness, adjacent ΔL >= 0.06, light-end contrast,
   and single-hue for `n` in `{8, 9, 10}` (spec SC-001).
2. Open both regenerated PNGs and visually confirm:
   - Every model's band is a distinguishable shade of the same blue family, light (smallest) to
     dark (largest) (SC-001, SC-003).
   - In a region where a small model's band overlaps a large one, the small model's color and
     outline are visible on top, not covered (SC-002).
   - No band — including the now-backmost, largest models — reads as blank/washed out at the
     increased opacity (SC-002, FR-004).
3. `git diff --stat gpugem/ benchmarks/results/` is empty — no solver defaults or result data
   changed, only figure-generation code and the regenerated PNGs themselves (SC-005).
