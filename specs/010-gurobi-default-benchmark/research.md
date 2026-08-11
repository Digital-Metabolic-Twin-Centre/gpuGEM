# Phase 0 Research: Gurobi Default-Settings Benchmark Across All Models

## R1: Gurobi's own factory default for `Method` is confirmed `-1` (automatic)

Checked directly against the installed `gurobipy` rather than assumed:

```python
>>> m.Params.Method
-1
>>> m.getParamInfo('Method')
('Method', <class 'int'>, -1, -1, 6, -1)   # (name, type, default, min, max, current)
```

`-1` is both the parameter's documented default and its current (untouched) value on a freshly
created model — confirming "Gurobi with default settings and no optimisations by settings" means
literally not setting `Method` at all (equivalently, passing `method=-1` through the existing
wrapper), as opposed to this project's existing benchmark tooling, which hardcodes `method=2`
(barrier) via `benchmarks/solve.py::solve_gurobi`'s default argument.

**Decision**: the new benchmark calls the existing `solve_gurobi(lp, time_limit=..., method=-1)`
— no new solver-wrapping code needed, only a different argument value, reusing every other piece
of `solve_gurobi` (model construction, bound sentinel handling, coupling-row translation) exactly
as already validated by every prior feature that depends on it.

## R2: No new introspection mechanism needed to report which algorithm automatic mode picked

`solve_gurobi` already reads `m.BarIterCount` and `m.IterCount` after solving (used today to
collapse into a single `iters` field: barrier count if nonzero, else simplex count). For a
continuous LP (no integers, this project's exact case), Gurobi's `Method=-1` deterministically
picks exactly one of primal simplex / dual simplex / barrier based on problem characteristics — it
does not fall back to racing multiple methods the way `Method=3` (concurrent) does — so this same
existing pair of counters already tells us, after the fact, which single algorithm automatic mode
actually used (`BarIterCount > 0` → barrier ran; otherwise a simplex variant ran).

**Decision**: extend `solve_gurobi`'s return dict with two already-computed values it currently
discards — `bar_iters` and `simplex_iters` — additive and backward-compatible (every existing
caller reads `iters`/`method` and is unaffected). The new benchmark derives `"solved_by":
"barrier" if bar_iters > 0 else "simplex"` from these, satisfying the spec's `GurobiDefaultResult`
key entity ("which underlying algorithm Gurobi's automatic selection actually used") without a
new Gurobi call or new introspection surface.

## R3: File/script layout mirrors feature 005's already-established, reused pattern exactly

Feature 005 (`run_residual_tradeoff.py`) already solved the identical structural problem this
feature has — "reuse two already-recorded configurations, add exactly one new configuration per
model, never touch the reused ones" — via: a dedicated results subdirectory
(`results/residual_tradeoff/`), a `_load_002_result()` reader that errors clearly if the model's
002 result is missing, an orchestrator with `--model`/`--all`/`--force` and skip-if-exists, an
`aggregate_*` script producing a `comparison.csv`, and a `make_*_figures` script reading only that
CSV (no solver import).

**Decision**: replicate this exact pattern rather than inventing a new one:

- `benchmarks/run_gurobi_default_benchmark.py` — reuses `results/<model>.json` for `cuopt` and
  `gurobi` (never re-solved), solves one fresh `solve_gurobi(..., method=-1)` per model, writes
  `results/gurobi_default/<model>.json`.
- `benchmarks/aggregate_gurobi_default.py` — writes `results/gurobi_default/comparison.csv`.
- `benchmarks/make_gurobi_default_figure.py` — reads only the CSV, writes
  `benchmarks/figures/gurobi_default_comparison.png`. No solver import, matching this project's
  existing figure-reproducibility convention (and satisfying spec FR-007 directly).

**Alternatives considered**: folding this into `run_residual_tradeoff.py` itself (it already
touches every model and reuses 002 data) — rejected; that script's whole purpose is the
`per_constraint_residual` trade-off specifically (its own file/variable names, its own non-
recommendation framing), and this feature's data has nothing to do with that setting — conflating
them would make both harder to read for no reuse benefit beyond the `_load_002_result`-style
reader, which is a few lines to duplicate/adapt, not worth coupling two unrelated investigations.

## R4: Scope is solve time only — no dedicated violation-distribution figure

Unlike the `per_constraint_residual=0` cuOpt work (features 005/007), Gurobi's own algorithm
selection is not expected to trade correctness for speed: Gurobi's simplex and barrier+crossover
paths both produce a vertex solution verified against the same feasibility tolerances regardless
of which one runs, so there's no reason to expect this comparison to surface a residual/violation
story the way the cuOpt setting did. The spec's own User Story 2 and `ThreeWayComparison` entity
are scoped to solve time, not a violation distribution. The correctness gate (FR-002/003) is still
enforced and residual/status data is still captured per result (for the gate itself and for
`comparison.csv`), but no dedicated `violation_distribution`-style figure is produced for this
feature — would be scope creep the spec doesn't call for, and would incorrectly imply a
correctness trade-off is under investigation the way the "not a recommended configuration" caption
does for the cuOpt features.

## R5: Figure colors — reuse the already-validated 3-color categorical palette, remapped

Per the newly-ratified constitution Principle VI, this new figure's colors must be validated for
colorblind-safety by computation, not chosen by eye. Rather than deriving a new palette,
`make_residual_tradeoff_figures.py::CONFIG_COLOR` (`#4c72b0` blue, `#dd8452` orange, `#c44e52`
red) was re-validated directly against this exact use (3 categories, checked "all pairs" since any
two of this chart's three bars can sit side by side):

```
[PASS] Lightness band, Chroma floor, CVD separation (worst all-pairs ΔE 21.4)
[WARN] Contrast vs surface: #dd8452 at 2.73:1 -- legal given this project's existing
       per-bar value-annotation convention as the required secondary encoding.
```

**Decision**: reuse these exact three hex values, remapped to this feature's three categories —
blue stays cuOpt (consistent with every prior figure in this project using blue for cuOpt), orange
and red become the two Gurobi configurations (Gurobi barrier and Gurobi default respectively) —
rather than inventing and separately re-validating a new palette for one more 3-category chart.
No hatching on either Gurobi bar (unlike `residual_0`'s hatch in feature 005): neither Gurobi
configuration here is a non-recommended/unvalidated setting (research R4), so there is nothing to
visually flag as "don't use this as a default."

## Constitution re-check (Phase 0)

- **I. Correctness-Validated Defaults**: not implicated — `gpugem/_defaults.py` untouched; this
  feature benchmarks Gurobi-side configuration only.
- **II. Honest Status/Feasibility Reporting**: directly reinforced — spec FR-003 requires a failed
  default-settings solve to be recorded and visibly marked, matching every prior benchmark
  feature's convention.
- **III. Test Coverage for Numerical Behavior**: `solve_gurobi`'s extension (R2) is a small,
  additive change reading already-computed Gurobi attributes — no new numerical logic, but still
  gets a unit-test-level check per plan.md's Technical Context.
- **IV. Minimal, COBRA-Compatible Surface**: no `gpugem` public API change; all changes under
  `benchmarks/`.
- **V. Documented Known Limitations**: N/A — no new solver limitation discovered.
- **VI. Publication-Ready Figure Standards** (new in v1.2.0): the parts of this principle that are
  low-cost and unambiguous for a brand-new figure are applied directly — a CVD-validated palette
  (R5), professional axis/legend phrasing, no internal-setting jargon baked into labels. This
  feature does **not** additionally build the full browsing-PNG + journal-PDF + companion-caption
  treatment (the pattern established for the violation-distribution figures) — that is a
  presentation-format decision spanning every figure this project already has, not something to
  bundle silently into a data-content feature; it stays a separate, explicit follow-up unless the
  user asks for it here too.

No violations. No Complexity Tracking entries required.
