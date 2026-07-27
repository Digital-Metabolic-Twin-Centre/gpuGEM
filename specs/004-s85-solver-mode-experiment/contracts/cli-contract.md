# CLI contract: `run_solver_mode_experiment.py` / `_solver_mode_worker.py` / `aggregate_solver_modes.py`

## `python -m benchmarks.run_solver_mode_experiment` (orchestrator, run this one)

| Flag | Default | Behavior |
|---|---|---|
| `--time-limit SECONDS` | `900.0` | cuOpt-level time budget per variant (research R3). |
| `--force` | off | Re-run a variant whose result JSON already exists (same skip/force semantics as `002`/`003`). |

**Behavior contract**:
1. Solves S85's whole-body objective once with Gurobi (research R6); this reference objective is
   reused for every variant's correctness check.
2. For each of the 4 variants in `solver_mode_variants.SOLVER_MODE_VARIANTS`, in order: skip if
   its result JSON already exists and `--force` wasn't given (prints `[skip] <id>`); otherwise
   launch `python -m benchmarks._solver_mode_worker <id>` via `subprocess.run(...,
   timeout=time_limit + 60)`, print start/finish progress lines (same style as `003`'s sweep),
   classify the outcome per research R4, and write `results/s85_solver_modes/<id>.json`.
3. After all 4 variants have a result (fresh or skipped), regenerates
   `results/s85_solver_modes/summary.json`/`summary.csv` via `aggregate_solver_modes`.
4. Exit code non-zero if the baseline itself fails to complete or fails correctness (that would
   indicate something is wrong with the experiment setup, not just "a candidate didn't pan out");
   a candidate variant failing/timing out does NOT make the overall exit code non-zero, since
   "this candidate doesn't help" is an expected, valid experiment outcome.

## `python -m benchmarks._solver_mode_worker <variant_id>` (subprocess entry point, not run directly)

Looks up `variant_id` in `solver_mode_variants.SOLVER_MODE_VARIANTS`, builds S85's LP via
`s85_objectives.build_lp_for_objective("whole_body")`, solves with
`gpugem.solve(..., **variant.cuopt_kwargs)`, computes the feasibility residual, and prints one
JSON object to stdout (solve_s, status, solved_by, iters, objective, residual_inf) for the parent
to capture. Never called by a user directly — exists only so `run_solver_mode_experiment` has a
clean subprocess boundary (research R1).

## `python -m benchmarks.aggregate_solver_modes`

No flags. Reads the 4 `results/s85_solver_modes/*.json` files (whichever exist), writes
`summary.json`/`summary.csv` per data-model.md's VariantComparison. Runnable standalone, no
solver import — same "regenerable from committed results" property as `002`'s `make_figure.py`
and `003`'s `aggregate_sweep.py`.
