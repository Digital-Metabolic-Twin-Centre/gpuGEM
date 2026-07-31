# Contract: the two new violation-distribution figures

Both figures follow the visual-encoding requirements as literal functional requirements (FR-005
through FR-009), same precedent as feature 005's figure contracts.

## Shared layout (both figures)

- **Form**: population-pyramid / mirrored back-to-back histogram. One subplot per figure (not
  faceted by model — every model's distribution is overlaid on the same axes, which is the point of
  the comparison).
- **Y-axis**: violation magnitude, log scale, shared `bin_edges` (data-model.md) across every model.
- **X-axis**: row count, mirrored — shortfall (`shortfall_counts`) plotted as negative (left),
  excess (`excess_counts`) plotted as positive (right), around a shared zero at the vertical
  center.
- **Series**: one semi-transparent stepped fill per model (`alpha≈0.4`), so overlapping models
  remain individually visible, not one opaque region hiding another (FR-007).
- **Color**: single ordinal colormap (`Purples`), sampled by model-size rank — lightest = smallest
  model, darkest = largest (FR-008). Deliberately a different hue family from the existing
  `residual_tradeoff` figures' categorical configuration colors (blue/orange/red), since this is a
  different (ordinal, not categorical) encoding.
- **Labeling**: each model's contour carries a direct text label with its model name (FR-007),
  plus a backup legend (color swatch + name, size-ordered) for the >4-series case.
- **Zero handling**: a model with zero (or negligible) violations still appears — its
  `n_satisfied ≈ n_rows` — represented as a (near-)empty contour, not omitted (spec edge case).
- **Caption**: embedded caption stating this reflects `per_constraint_residual=0`, explicitly not a
  recommended configuration (matches every existing figure caption in this benchmark suite).
- **Output**: 300 dpi, `bbox_inches="tight"`, PNG under `benchmarks/figures/`.
- **Reproducibility**: reads only committed `results/residual_tradeoff/*.json`; no cuOpt/Gurobi
  install required to regenerate (FR-010).

## `violation_distribution_equations.png`

Drawn from `violation_histogram_equations` — every model in the suite (every model has an S-block).

## `violation_distribution_constraints.png`

Drawn from `violation_histogram_constraints` — only models where this field is non-null (models
with a C-block). `e_coli_core` and `iML1515` are absent from this figure entirely (User Story 3,
Acceptance Scenario 2) — not shown as empty entries, which would misleadingly imply they have a
coupling block with zero violations rather than no coupling block at all.

## Runtime comparison figures (regenerated, not new)

`residual_tradeoff_solvetime.png` / `residual_tradeoff_violations.png` (from feature 005) are
regenerated to include all nine models (FR-003), applying the same width-scaling fix feature 006
already applied to `make_figure.py` (research R7) so nine models' labels don't overlap.
