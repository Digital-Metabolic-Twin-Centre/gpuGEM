# Phase 0 Research: Violation Distribution Figures for per_constraint_residual=0

## R1: Extending `per_constraint_residual=0` coverage to the four new models requires no new orchestration code

`benchmarks/run_residual_tradeoff.py:main()` already does `names = M.ALL_MODELS if args.all else ...`,
and `M.ALL_MODELS` is generated from `benchmarks/models.py`'s `REGISTRY`, which feature 006 already
extended with S9/S15/S23/S83. `run_model()` already skips a model whose `results/residual_tradeoff/<model>.json`
exists unless `--force`. So `python -m benchmarks.run_residual_tradeoff --all` today would already
attempt all nine models, solving only the four new ones and skipping the five existing ones — the
same self-generalizing pattern already exercised in feature 006 (`run_benchmark.py --all` picked up
the new REGISTRY entries with zero code changes). FR-001/FR-003 need no change to the iteration
logic, only (a) the new histogram-capture logic (R2) added to `_solve_residual_0`, and (b) actually
running `--all`.

**Decision**: no change to `main()`/model selection; extend `_solve_residual_0`'s computation and
`run_model()`'s skip condition (R4), then run `--all`.

## R2: Per-row violation data must be captured at solve time, as binned histograms, not raw vectors

`benchmarks/residual.py::feasibility_residual()` only returns a scalar (`||S v - b||_inf`); no
existing code path in this project retains the full per-row residual vector after a solve, and flux
vectors themselves are never persisted (established in feature 005, research R3, to keep result
files small). For the largest models the raw vector is genuinely too large to commit: S85's
stoichiometric (S-block) has 734,457 rows and its coupling (C-block) has approximately 1.26M rows;
S9/S15/S23/S83 are all larger than S85. Storing per-row data for nine models at that scale is not a
reasonable committed-JSON payload.

**Decision**: compute the full signed per-row violation vector in memory immediately after each
`per_constraint_residual=0` solve (cheap — it's the same `S @ v - b` / `C @ v` computation
`gpugem/solver.py` already does internally, just not discarded), bin it into a small, fixed set of
log-scale magnitude bins split by violation direction, and persist only the binned counts. This is
exactly the data the population-pyramid figure needs, and keeps every result file small regardless
of model size.

**Alternatives considered**: (a) persist the raw vector compressed — rejected, still O(rows) storage
and no benefit over a histogram for this figure's purpose; (b) re-derive the histogram from flux
vectors saved separately — rejected, this project deliberately never persists flux vectors (005 R3),
and doing so here would be a much larger, unjustified storage footprint than the histogram itself.

## R3: The violation formula for both S-block and C-block rows is the same signed range-violation, reusing `gpugem/solver.py`'s own definition

`gpugem/solver.py` (lines ~198-206) already computes, after every solve with `check_feasibility=True`:

```python
con_viol = np.maximum(con_lb - Ax, 0.0) + np.maximum(Ax - con_ub, 0.0)   # unsigned
stoich_viol = con_viol[:n_stoich]                                        # S-block slice
# con_viol[n_stoich:] is the C-block slice
```

`con_lb`/`con_ub` already encode equality rows as `con_lb == con_ub == b` for the S-block and true
ranges for the C-block, so one formula covers both row populations. For the population-pyramid
figure we need the *signed* version (which side of the allowed range a row falls on), not the
unsigned magnitude solver.py already reports:

```python
signed_viol = -np.maximum(con_lb - Ax, 0.0) + np.maximum(Ax - con_ub, 0.0)
# negative => row falls short of its required balance/range ("category A" / shortfall)
# positive => row exceeds its required balance/range ("category B" / excess)
# exactly zero => row satisfied within its range
```

**Decision**: add one new pure function computing this signed vector, applied to the S-block slice
(equations) and, when `C` is present, the C-block slice (coupling constraints) separately. This
mirrors solver.py's own slicing convention rather than inventing a new one, per the constitution's
Principle IV (minimal surface, no speculative generality) and to keep the two computations
provably consistent with what `result.feasibility` already reports.

**`lp` dict fields available** (`benchmarks/models.py::build_lp`, consumed via
`benchmarks/solve.py::_solver_args`): `S`, `b` (S-block), and, only when coupling rows exist, `C`,
`d_lb`, `d_ub` (C-block) — exactly what's needed, already in scope inside `_solve_residual_0`
alongside the freshly solved `res.fluxes`.

## R4: Reconciling FR-002 ("must not alter the original five's results") with FR-004 ("every model needs full per-row data")

FR-004 requires the new histogram data for *every* model's `per_constraint_residual=0` result,
including the original five — but those five's existing `results/residual_tradeoff/*.json` files
predate this feature and don't have it. Since no raw per-row data was ever retained (R2), the only
way to add it is a fresh solve. This is read literally as being in tension with FR-002.

**Decision**: FR-002 protects against *silent, accidental* changes to the original five's *trusted,
already-published* scalar fields (`solve_s`, `residual_inf`, `speedup_residual_0_vs_shipped`,
`violation_ratio_residual_0_vs_shipped` — the numbers already quoted in `README.md`'s trade-off
table) as an unintended side effect of onboarding new models — e.g. a careless `--force` sweep
overwriting them with a different run's noise. It does not forbid a deliberate, visible schema
extension. `run_model()`'s skip condition is changed from "skip if the file exists" to "skip if the
file exists *and already has both histogram fields*" — an old-format file for one of the original
five is treated as needing a one-time backfill solve, run automatically (not silently: the script
prints `[backfill]` instead of `[skip]` for this case), without requiring `--force`. `residual_0`
is inherently reproducible (PDLP on a fixed LP under fixed settings), so the backfilled scalar
fields are expected to closely reproduce the already-published numbers, not diverge from them;
`--force` remains available for a full deliberate re-solve of everything.

This backfill is cheap: unlike the shipped-default solves (500s+ for the largest models),
`per_constraint_residual=0` solves are the fast configuration (005's own numbers: S85 finished in
about 1/67th of shipped-default's time). Re-solving all nine, including backfilling the original
five, is tractable in one `--all` run.

## R5: Binning scheme

Shared, fixed log-scale magnitude bin edges across every model and both figures, so overlaid
distributions are directly comparable on one axis. Observed violation magnitudes across the
existing five models span from ~7.8e-9 (e_coli_core, effectively solver noise) up to 156.4 (S85);
S9/S15/S23/S83 are expected to be in the same order-of-magnitude range or somewhat larger given
they exceed S85 in size. A generous fixed range with headroom: `numpy.logspace(-9, 3, 25)` (24 bins
spanning 1e-9 to 1e3, two bins per decade) is defined once as a module-level constant, reused by
both the histogram-capture step and the figure-rendering step so they can never silently drift
apart.

Rows whose magnitude is exactly zero (fully satisfied) or falls below the smallest bin edge are
counted in an explicit `n_satisfied` field, separate from the binned `shortfall_counts`/
`excess_counts` arrays — this is what makes a model with zero (or negligible) violations still
representable (edge case in spec.md) without corrupting the log-scale bins with a zero-magnitude
entry.

**Alternatives considered**: per-model adaptive bins (tightest range that fits that model's own
data) — rejected, defeats the point of an overlaid comparison figure where the same y-position must
mean the same magnitude for every model.

## R6: Rendering mechanics and color (dataviz skill consulted)

Consulted the project's dataviz skill for this chart type. Two relevant guidances:

1. **Sequential/ordinal color**: models are ordered by size, a genuine ordinal ranking (swapping the
   order changes the meaning), so this is the skill's "ordinal" job — one hue, monotone lightness
   steps, light end still readable against the surface (not the fully-white end of the ramp). A
   single-hue matplotlib sequential colormap (e.g. `Purples`) is sampled at fixed fractions across
   the 9 model ranks (smallest → lightest, largest → darkest), skipping the lightest ~30% of the
   ramp so even the smallest model's contour stays visible. `Purples` (not `Blues`/`Oranges`/`Reds`)
   is chosen specifically so this ordinal per-model ramp cannot be visually confused with the
   existing `residual_tradeoff` figures' categorical per-*configuration* colors
   (`shipped_default`=blue, `residual_0`=orange, `gurobi`=red, from 005's `CONFIG_COLOR`) — these
   are two different encodings (model identity/size vs. configuration identity) that must not share
   a hue family.
2. **Direct labeling with a large series count**: the skill's accessibility rule direct-labels up to
   ~4 series before falling back to a legend; with up to 9 overlaid models, the spec's explicit
   requirement ("label each contour with its model name") is honored by placing a direct text label
   at each contour's outer extent, *and* a compact size-ordered legend (color swatch + model name)
   is kept as the accessibility backup per the skill's own guidance for higher series counts — belt
   and suspenders, not a substitute for one another.

**Decision**: `matplotlib`, one `fill_betweenx`-style stepped area per model per side (shortfall on
the negative/left x side, excess on the positive/right x side), `alpha≈0.4`, colors from `Purples`
sampled by size rank, y-axis log-scale magnitude (reusing the existing `_floor_for_log`-style
zero-handling convention already established in `make_residual_tradeoff_figures.py`), x-axis a
mirrored count axis, direct per-model text labels plus a backup legend, 300 dpi, `bbox_inches="tight"`,
an embedded caption stating this reflects `per_constraint_residual=0` (not a recommended
configuration), matching every prior figure in this benchmark suite.

## R7: Runtime comparison figure at nine models needs the same width fix as feature 006

`make_residual_tradeoff_figures.py`'s `_bar_figure()` currently sizes for five models per the
original feature 005 scope. Feature 006 hit and fixed the identical label-overlap problem in
`make_figure.py` by widening `figsize` proportionally to model count
(`figsize=(max(8.2, 1.5 * len(df)), 4.6)`). The same fix is applied here for consistency and to
avoid re-discovering the same bug.

## Constitution re-check (Phase 0)

- **Principle I (Correctness-Validated Defaults)**: not implicated — `gpugem/_defaults.py` is not
  touched; `per_constraint_residual=0` remains explicitly non-default, non-recommended (FR-011,
  restated in every figure caption per existing convention).
- **Principle II (Honest Status/Feasibility Reporting)**: this feature *adds* visibility into
  exactly how much correctness `per_constraint_residual=0` costs, in more detail than before —
  directly in service of this principle.
- **Principle III (Test Coverage for Numerical Behavior)**: the new signed-violation and
  histogram-binning functions are pure, synthetic-input-testable (no GPU) — tests planned in
  `tests/test_violation_histogram.py`, matching `tests/test_residual_tradeoff.py`'s precedent.
  `gpugem/solver.py`/`_defaults.py` themselves are not modified, so this principle's mandate is
  satisfied by testing the new benchmark-side computation to the same standard.
- **Principle IV (Minimal, COBRA-Compatible Surface)**: no `gpugem` public API changes; all new code
  is benchmark-only (`benchmarks/`), consistent with 004/005/006.
- **Principle V (Documented Known Limitations)**: no new solver limitation discovered; existing
  `per_constraint_residual` trade-off documentation (README) is extended, not superseded.

No violations. No Complexity Tracking entries required.
