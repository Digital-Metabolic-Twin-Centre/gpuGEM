# Cross-scale cuOpt vs Gurobi LP benchmark

Compares the GPU LP solver (NVIDIA cuOpt, via gpuGEM's shipped size-selected
defaults) against Gurobi standalone on the max-biomass FBA LP of five models
spanning four orders of magnitude:

| model | scale | source | loader |
|---|---|---|---|
| e_coli_core | small | BiGG (cached) | cobra -> gpugem.loaders.from_cobra |
| iML1515 | medium | BiGG (cached) | cobra -> gpugem.loaders.from_cobra |
| Harvey | whole-body | Harvey_1_03c_reduced.mat | gpugem.loaders.from_mat |
| S84 | microbiome | mWBM_S84_male.mat | gpugem.loaders.from_mat |
| S85 | microbiome | mWBM_S85_male.mat | gpugem.loaders.from_mat |

Both solvers receive the **identical** LP built by `gpugem.loaders`. cuOpt uses
gpuGEM's shipped defaults (`gpugem._defaults.default_settings`, size-selected:
mixed-precision PDLP for <=100K vars, PaPILO presolve above). Gurobi uses barrier
+ crossover. The cuOpt settings are consumed, never retuned for the comparison.

## Correctness gate (before any timing is trusted)

For every solve the runner records the stoichiometric residual `||S v - b||_inf`
and the objective. A model cell is **FAILED** (non-zero exit) if a solver is
non-optimal, the residual exceeds `--res-tol` (default 1e-4), or the two solvers'
objectives disagree by more than `--obj-tol` (default 1e-6 relative). No solve
time is reported for a failed cell.

The 1e-4 absolute residual tolerance accommodates the microbiome whole-body
models, whose stoichiometric coefficients span [1e-6, 2e5]; cuOpt's PaPILO
integration has a hardcoded feastol ~1e-5 (see gpugem/_defaults.py), so an
absolute 1e-6 gate would reject a solution that reaches the identical optimum
as Gurobi (objectives agree to 0 relative difference on all five models).

## Run

```bash
cd ~/projects/gpuGEM && conda activate base

python -m benchmarks.run_benchmark --model iML1515 --reps 3     # one model
python -m benchmarks.run_benchmark --all --reps 3               # all (resumable)
python -m benchmarks.make_figure                                # figure from CSV, no GPU
```

`--all` skips models whose `results/<model>.json` already exists unless `--force`.

Model file locations can be overridden with `MWBM_DIR` and `HARVEY_MAT` env vars.

## Outputs (committed)

- `results/<model>.json` — every repeat, provenance (checksums, dims, versions).
- `results/benchmark.csv` — aggregated medians; the single source for the figure.
- `figures/benchmark_solvetime.png` — regenerable from the CSV alone.

## Reproducibility

- BiGG models cached under `model_cache/` (sha256 recorded); `.mat` files pinned
  by sha256. Solver + GPU versions embedded in every JSON and the figure caption.
- The figure imports only pandas + matplotlib — a reviewer can rebuild it with no
  GPU and no solver license.

## S85 multi-objective sweep

S85 was the one outlier in the table above (cuOpt ~10x *slower* than Gurobi on
the single whole-body objective, unlike every other model). `run_objective_sweep.py`
re-solves S85 with both solvers across ~20 additional biologically distinct
objectives (`s85_objectives.py`: organ/tissue biomass, immune-cell biomass,
individual gut-microbiome taxa) to check whether that gap holds on average or
was specific to the whole-body objective. Same correctness gate, same LP
builder pattern as above; unlike the cross-scale benchmark it defaults to 1
repeat per (objective, solver) since the statistical signal here comes from
averaging across ~20 objectives rather than repeating one (see
`specs/003-s85-multi-objective-benchmark/`).

```bash
python -m benchmarks.run_objective_sweep --objective whole_body   # one objective
python -m benchmarks.run_objective_sweep --all                    # all ~20 (resumable, hours)
python -m benchmarks.aggregate_sweep                               # summary from committed JSON, no GPU
```

Because a full `--all` run can take hours, it prints a start/finish line per
(objective, solver) plus a heartbeat line every `--heartbeat-s` (default 30s)
while a solve is in progress, and skips objectives whose result already exists
unless `--force` — so it is safe to interrupt and restart.

Outputs (committed) under `results/s85_objectives/`: `objectives.json` (the
objective registry with each one's biological rationale), one `<id>.json` per
objective, and `summary.json`/`summary.csv` (per-solver average/median/min/max
runtime, the cuOpt/Gurobi runtime ratio, and any objective whose ratio is an
outlier relative to the rest).

**Result**: the gap is real and structural, not an artifact of the biomass
objective. All 20 objectives passed the correctness gate; cuOpt's wall time was
flat across every one of them (507-537s, a ~6% spread) despite spanning wildly
different biology (organs, immune cells, individual gut bacteria) —
`runtime_ratio_median = 9.41`, the original whole-body objective's own ratio
(9.16) sits right on the median, and zero objectives were flagged as outliers.
cuOpt's cost on S85 is governed by the shared constraint matrix, not by which
variable is being maximized.

## S85 alternative solver-mode experiment

Given the above, `run_solver_mode_experiment.py` tests whether any currently-unused
cuOpt solver-mode setting closes the gap: `pdlp_solver_mode=Methodical1` (a PDHG
variant described as more thorough on hard problems), `method=Concurrent`
(cuOpt's own actual default — races PDLP/DualSimplex/Barrier in parallel;
`gpugem`'s shipped defaults currently hardcode PDLP-only for large models,
foreclosing this), and `method=Barrier` run cold (no warm start, since
warm-starting is broken in cuOpt 26.6.0) — all three flagged as untested on this
model family in prior investigation notes. Every variant is expressed as a
`**cuopt_kwargs` override through `gpugem.solve`'s existing per-call mechanism;
`gpugem/_defaults.py` is never edited (see `specs/004-s85-solver-mode-experiment/`).

```bash
python -m benchmarks.run_solver_mode_experiment              # baseline + all 3 candidates
python -m benchmarks.aggregate_solver_modes                  # summary from committed JSON, no GPU
```

Because two of the three candidates have never been run on this model family and
could behave unpredictably (in particular `barrier_cold`'s cold factorization on
an ~874K-variable problem), each variant runs in its own subprocess with a time
budget (`--time-limit`, default 900s cuOpt-level + 60s subprocess-level grace) —
a hang or crash in one variant is recorded as `DidNotComplete` (`"timeout"` or
`"crashed"`) and does not stop the remaining variants. Skips a variant whose
result already exists unless `--force`.

Outputs (committed) under `results/s85_solver_modes/`: one `<id>.json` per
variant (`baseline`, `methodical1`, `concurrent`, `barrier_cold`) and
`summary.json`/`summary.csv` (each candidate's speedup factor vs. baseline,
correctness, and the best verified-correct candidate if any beats the baseline).

**Result**: none of the three candidates beat the baseline while remaining
verified-correct.

| variant | solve_s | status | solved_by | verified_correct |
|---|---|---|---|---|
| baseline (unchanged) | 505.5s | Optimal | PDLP | yes |
| methodical1 | — (`DidNotComplete`/`timeout`) | — | — | no |
| concurrent | 513.4s | Optimal | PDLP | yes (0.98x — a tie) |
| barrier_cold | 7.2s | NumericalError | Barrier | no |

`methodical1` didn't even converge inside the same 900s+60s budget the baseline
finished comfortably within. `concurrent` raced PDLP/DualSimplex/Barrier and PDLP
won again — direct evidence that Barrier/DualSimplex aren't faster contenders on
this problem even head-to-head. `barrier_cold` failed almost immediately with a
numerical error rather than hanging or slowly converging, consistent with cuDSS's
factorization choking on S85's `[1e-6, 2e5]` coefficient range without a warm
start to help it. See the README's "Known limitations" section.

## Constraint-residual speed/correctness trade-off benchmark

A follow-up investigation traced the S85 slowdown to a specific, deliberate `gpugem`
default: `per_constraint_residual=1` (a per-row L-infinity feasibility check requiring
*every one* of ~2 million constraint rows to individually satisfy the tolerance) versus
cuOpt's own actual default, `per_constraint_residual=0` (an aggregate L2-norm check).
`run_residual_tradeoff.py` quantifies that trade-off across every model already in the
cross-scale benchmark — not just S85 — reusing `002`'s existing shipped-default cuOpt and
Gurobi results (never re-solved) and adding one fresh `per_constraint_residual=0` solve per
model. **This benchmark does not change, recommend, or silently adopt
`per_constraint_residual=0`** — `gpugem/_defaults.py` stays untouched regardless of what the
comparison shows (see `specs/005-residual-tradeoff-benchmark/`).

```bash
python -m benchmarks.run_residual_tradeoff --all              # reuse 002 + solve per_constraint_residual=0
python -m benchmarks.aggregate_residual_tradeoff               # comparison.csv from committed JSON, no GPU
python -m benchmarks.make_residual_tradeoff_figures             # both figures from the CSV, no solver
```

Outputs (committed) under `results/residual_tradeoff/`: one `<model>.json` per model (all three
configurations) and `comparison.csv` (15 rows: 5 models x 3 configurations). Figures under
`figures/`: `residual_tradeoff_violations.png` and `residual_tradeoff_solvetime.png` — both carry
an explicit "not a recommended configuration" caption and visually distinguish the
`per_constraint_residual=0` bars (hatched) from the other two.

**Result**: the effect scales with model conditioning, not just size — and it's essentially free
for the two small, well-conditioned models.

| model | vars | shipped_default residual | residual_0 residual | rows violated (>1e-6) | speedup |
|---|---|---|---|---|---|
| e_coli_core | 95 | 7.78e-09 | 7.78e-09 (identical) | 0 | ~0.5x (already sub-second either way) |
| iML1515 | 2,712 | 2.95e-09 | 4.45e-09 | 0 | ~1.0x (no meaningful difference) |
| Harvey | 81,094 | 5.58e-09 | 3.19e-04 | 591 | ~1.4x |
| S84 | 685,998 | 4.72e-05 | 2.57 | 249,173 | ~2.7x |
| S85 | 874,634 | 8.87e-05 | 156.4 | 372,156 | ~66.9x |

For the two small BiGG models, `per_constraint_residual` essentially never binds — the shipped
default and cuOpt's own default land on the same iteration count and residual, confirming this is
specifically a large/ill-conditioned-model phenomenon, not a general cuOpt inefficiency. The
effect grows sharply with scale and coefficient-range severity: by S85, disabling the per-row
check leaves **372,156 of ~2 million constraint rows** (about 19%) violated beyond `1e-6` — a
real, large correctness regression, not numerical noise, which is exactly why `gpugem` pays the
iteration cost to avoid it.
