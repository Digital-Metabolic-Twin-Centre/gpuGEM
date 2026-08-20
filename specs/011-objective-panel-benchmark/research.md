# Phase 0 Research: Cross-Model Objective-Panel Credibility Benchmark

## R1: "Previously tested settings" -- reps, time_limit, and tolerances are already uniform across all 10 models

Checked every main-suite model's committed `results/<model>.json` directly rather than assumed:

```
Harvetta reps=3 time_limit=900.0 res_tol=0.0001 obj_tol=1e-06
Harvey   reps=3 time_limit=900.0 res_tol=0.0001 obj_tol=1e-06
S15      reps=3 time_limit=900.0 res_tol=0.0001 obj_tol=1e-06
S23      reps=3 time_limit=900.0 res_tol=0.0001 obj_tol=1e-06
S83      reps=3 time_limit=900.0 res_tol=0.0001 obj_tol=1e-06
S84      reps=3 time_limit=900.0 res_tol=0.0001 obj_tol=1e-06
S85      reps=3 time_limit=900.0 res_tol=0.0001 obj_tol=1e-06
S9       reps=3 time_limit=900.0 res_tol=0.0001 obj_tol=1e-06
e_coli_core reps=3 time_limit=900.0 res_tol=0.0001 obj_tol=1e-06
iML1515     reps=3 time_limit=900.0 res_tol=0.0001 obj_tol=1e-06
```

**Decision**: reuse `reps=3`, `time_limit=900.0`, `res_tol=1e-4`, `obj_tol=1e-6` for every (model, objective)
combination -- reading them from each model's own `results/<model>.json` at run time (not hardcoded), matching
feature 010's `_load_existing_result` pattern, so a future change to any model's published tolerance is picked
up automatically rather than silently drifting out of sync. `run_objective_sweep.py`'s own `--reps` default of
`1` is NOT reused here -- the spec's whole point is a median across repeats, so this feature's default must be
`3`, matching what every other recorded result in this project already uses.

## R2: Resolving an arbitrary objective reaction to a column index works differently per model kind, but both paths already exist in this codebase

- **`kind="cobra"` models** (`e_coli_core`, `iML1515`): `gpugem/loaders.py::from_cobra` builds `c`/`lb`/`ub`
  in exactly `model.reactions` order (verified by reading the loader: `c = np.array([r.objective_coefficient
  for r in model.reactions], ...)`). So the column index for a reaction ID is
  `[r.id for r in model.reactions].index(reaction_id)`.
- **`kind="mat"` models** (`Harvey`, `Harvetta`, `S84`/`S85`/`S9`/`S15`/`S23`/`S83`): `benchmarks/models.py::
  _mat_rxns(path, model_key)` returns the exact rxns array in column order; the index is
  `np.where(rxns == reaction_id)[0][0]`. This is the same lookup `benchmarks/models.py::build_lp`'s own
  `meta["objective"]` branch and `benchmarks/s85_objectives.py::build_lp_for_objective` already use for a
  single, hardcoded objective each.

**Decision**: write one small, model-kind-dispatching helper -- `build_lp` (reused verbatim for everything
except the objective vector) followed by a single override step that zeroes `lp["c"]` and sets index 1.0 at
the resolved reaction, `maximize=True` -- generalizing the existing per-kind lookup logic to accept any
`reaction_id` argument instead of a hardcoded one. No new LP-construction code; only a new reaction-lookup
wrapper around the two already-proven lookup mechanisms above.

## R3: Objective panel CSVs have different documentation columns per model type, but `reaction_id` is universal

Inspected all 10 files under `benchmarks/objective_candidates/`:

- `e_coli_core.csv` / `iML1515.csv`: `reaction_id, reaction_name, formula, category, why_selected, notes`
- `Harvey.csv` / `Harvetta.csv`: `reaction_id, organ_or_cell_type, category, why_selected, notes`
- `S84.csv`/`S85.csv`/`S9.csv`/`S15.csv`/`S23.csv`/`S83.csv`: `reaction_id, taxon_or_organ, category,
  why_selected, notes`

**Decision**: this feature reads only `reaction_id` (required, to build the LP) and `category` (carried
through into results/plots for readability -- already present in every file under that exact column name).
The remaining columns (`reaction_name`/`formula`/`organ_or_cell_type`/`taxon_or_organ`/`why_selected`/
`notes`) are curation documentation from the prior objective-panel review work and are not consumed here.

## R4: Realistic runtime cost -- this is a genuinely long-running batch operation, not a quick command

Using the already-collected single-objective solve times from feature 010's `results/gurobi_default/*.json`
(same models, same settings, one objective each) as a lower-bound estimate per objective:

```
S85  cuopt ~509s   S9  cuopt ~534s   S23 cuopt ~740s   S83 cuopt ~527s   S84 cuopt ~25s   S15 cuopt ~295s
```

Extrapolated across a 50-objective panel x 3 repeats for just the slowest microbiome models, cuOpt alone
implies tens of thousands of seconds (multiple hours) **per model**, before Gurobi's (faster, ~50-100s/solve)
repeats or the other five models are even counted. Total wall-clock time across all ten models' full panels
is realistically multi-day.

**Decision**: accept this as a known, expected property of the feature (already captured in spec.md's
Assumptions), and make two things non-negotiable in the design: (a) per-(model, objective) resumability with
a skip-if-exists check (FR-011 -- already this project's standard pattern), and (b) a heartbeat print during
each long solve so a multi-hour run is visibly progressing rather than indistinguishable from a hang -- reuse
`run_objective_sweep.py::_with_heartbeat` verbatim rather than reinventing it.

## R5: File/script layout mirrors this project's established three-script benchmark pattern

**Decision**: `benchmarks/run_objective_panel.py` (orchestrator: `--model NAME | --all`, `--force`, iterates
every `reaction_id` in that model's `objective_candidates/<model>.csv`, writes one JSON per (model,
objective) under `results/objective_panel/<model>/<objective_id>.json`), `benchmarks/
aggregate_objective_panel.py` (reads the committed per-objective JSONs -> the two CSVs from R6, no solver
import), `benchmarks/make_objective_panel_figures.py` (reads the CSVs -> one PNG per model, no solver
import). Mirrors features 005/010's `run_*`/`aggregate_*`/`make_*_figure(s)` triad exactly.

## R6: Two additive CSV views satisfy FR-007's "only objective value and runtime" + "also... violations and other benchmarks"

**Decision**:
- `results/objective_panel/objective_runtime.csv` -- `model, objective_id, reaction_id, solver,
  objective_value_median, runtime_s_median`. Nothing else. This is the literal "only the objective value and
  runtime" view the spec calls for.
- `results/objective_panel/benchmark_details.csv` -- `model, objective_id, reaction_id, category, solver,
  status, residual_inf_median, iters_median, feasible, obj_agree_with_cuopt, both_feasible`. The fuller
  correctness/benchmark view, additive to (not replacing) the first CSV, per FR-007's "also save."

Per-repeat data (needed to compute both medians) is preserved in the per-(model, objective) JSON, mirroring
every other feature's `"repeats": [...]` + `"*_median"` convention -- the two CSVs are pure aggregations of
that already-complete JSON, regenerable without a solver (matching `aggregate_residual_tradeoff.py`/
`aggregate_gurobi_default.py`'s existing "no solver import" property).

## R7: The correctness GATE stays as strict as established; only the *displayed* residual value is a median

FR-004 requires the constraint-violation residual to be *reported* as a median across repeats. This must NOT
loosen the correctness gate itself: `run_objective_sweep.py`'s existing gate logic (`g_feas = all(r["feasible"]
for r in gurobi_reps)`) requires **every individual repeat** to pass status/residual/objective-agreement
checks, not just the median repeat. **Decision**: keep that per-repeat-then-`all()` gate exactly as-is
(FR-005/FR-006); separately compute and report `residual_inf_median` (FR-004) purely as the number shown in
`benchmark_details.csv`, not as an input to the pass/fail decision. A combination could in principle have a
good median residual but still fail the gate because one repeat individually violated tolerance -- that MUST
still be marked failed (spec Edge Cases), so the gate reads all repeats, the display reads the median.

## R8: Figure design -- one figure per model, not one cross-model mega-chart

Panel sizes range from 10 (e_coli_core) to 50 (each microbiome model) objectives, and runtimes range from
sub-millisecond to 500+ seconds across models -- a single combined chart would be unreadable on both axes.
**Decision**: one PNG per model (10 total), x-axis = that model's objective IDs, y-axis = `runtime_s_median`
(log scale, matching this project's established convention for wide-dynamic-range solve-time figures),
grouped bars for the two solvers. Colors reused verbatim from the already CVD-validated `CONFIG_COLOR` in
`make_residual_tradeoff_figures.py`/`make_gurobi_default_figure.py` (`#4c72b0` blue = cuOpt, `#dd8452` orange
= Gurobi) -- consistent with every prior figure's solver-color convention in this project, no new palette to
validate.

## Constitution re-check (Phase 0)

- **I. Correctness-Validated Defaults**: PASS -- no `_defaults.py` change; this feature only reuses each
  model's already-published, already-validated settings.
- **II. Honest Status/Feasibility Reporting**: PASS, and central to this feature's purpose -- a failing
  (model, objective, solver) combination is recorded and marked failed (R7), never silently dropped or
  smoothed over by the median-reporting requirement.
- **III. Test Coverage for Numerical Behavior**: the new reaction-lookup helper (R2) and the two-CSV
  aggregation logic (R6) get `pytest` coverage on synthetic data, no GPU/Gurobi required.
- **IV. Minimal, COBRA-Compatible Surface**: PASS -- zero new `gpugem` public surface; every new file lives
  in `benchmarks/`.
- **V. Documented Known Limitations**: N/A -- no new solver limitation discovered; this feature validates
  existing published numbers, it doesn't change solver behavior.
- **VI. Publication-Ready Figure Standards** (v1.2.0): the CVD-validated, already-established solver-color
  convention (R8) is applied directly. Consistent with features 005/010's own re-check: this feature does
  **not** additionally build the full journal-PDF/TIFF/caption treatment -- that stays a separate, explicit,
  not-silently-bundled follow-up.

No violations. No Complexity Tracking entries required.
