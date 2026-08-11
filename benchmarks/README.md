# Cross-scale cuOpt vs Gurobi LP benchmark

Compares the GPU LP solver (NVIDIA cuOpt, via gpuGEM's shipped size-selected
defaults) against Gurobi standalone on the max-biomass FBA LP of ten models
spanning four orders of magnitude:

| model | scale | source | loader |
|---|---|---|---|
| e_coli_core | small | BiGG (cached) | cobra -> gpugem.loaders.from_cobra |
| iML1515 | medium | BiGG (cached) | cobra -> gpugem.loaders.from_cobra |
| Harvey | whole-body | Harvey_1_03c_reduced.mat | gpugem.loaders.from_mat |
| Harvetta | whole-body | Harvetta_1_03d.mat (model_cache/) | gpugem.loaders.from_mat |
| S84 | microbiome | mWBM_S84_male.mat | gpugem.loaders.from_mat |
| S85 | microbiome | mWBM_S85_male.mat | gpugem.loaders.from_mat |
| S23 | microbiome | mWBM_S23_male.mat (model_cache/) | gpugem.loaders.from_mat |
| S15 | microbiome | mWBM_S15_male.mat (model_cache/) | gpugem.loaders.from_mat |
| S9 | microbiome | mWBM_S9_male.mat (model_cache/) | gpugem.loaders.from_mat |
| S83 | microbiome | mWBM_S83_male.mat (model_cache/) | gpugem.loaders.from_mat |

Harvetta is the female whole-body counterpart to Harvey (male) — same reconstruction
family, same `Whole_body_objective_rxn` objective reaction, a genuine coupling block,
and a comparable variable count (83,521 vs Harvey's 81,094), loaded via `model_key=
"female"` (Harvey's `.mat` nests its struct under `"modelReduced"` instead — the two
files use different top-level keys despite otherwise matching structure).

S9/S15/S23/S83 are all larger than S85 (874,634 vars) — 1,007,742 to 1,179,186
variables — and live under `benchmarks/model_cache/` alongside Harvetta, rather than
the `MWBM_DIR` location S84/S85 use. The comparison figure orders all ten models
strictly by variable count, not by the table order above.

**Model files under `benchmarks/model_cache/` are committed to this repository** —
every `.mat`/`.xml` file the registry above references (≈ 299 MB total: Harvetta,
S9/S15/S23/S83's plain variants, plus the small BiGG XMLs) is tracked, so the full
benchmark suite is reproducible from a checkout of this repository alone, with no
separate download or `MWBM_DIR`/`HARVEY_MAT` environment configuration needed for
these ten models. This reverses an earlier size-driven decision to gitignore these
files; `benchmarks/model_cache/*_lifted.mat` remains excluded, since the `_lifted`
variants aren't used by any registered model or published result — only the plain
variant each `S9`/`S15`/`S23`/`S83` entry above actually loads.

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
as Gurobi (objectives agree to 0 relative difference on all ten models).

## Run

```bash
cd ~/projects/gpuGEM && conda activate base

python -m benchmarks.run_benchmark --model iML1515 --reps 3     # one model
python -m benchmarks.run_benchmark --all --reps 3               # all (resumable)
python -m benchmarks.make_figure                                # figure from CSV, no GPU
```

The figure's right-hand panel is a separate Gurobi-only method comparison on the
Harvey Kynuric two-demand biomarker LP (`C02470[bc]` and `kynate[bc]`, both
increased). Its three cold repeats are stored in
`results/harvey_two_demand_gurobi.json`: dual simplex has a 25.245 s median and
barrier with default crossover has a 5.215 s median (4.84x faster). This
supplemental problem is labelled separately because it is not the canonical
whole-body-objective Harvey LP used in the main cross-solver panel.

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
`run_residual_tradeoff.py` quantifies that trade-off across every model in the cross-scale
benchmark — now all nine, not just the original five — reusing `002`'s existing shipped-default
cuOpt and Gurobi results (never re-solved) and adding one fresh `per_constraint_residual=0` solve
per model. **This benchmark does not change, recommend, or silently adopt
`per_constraint_residual=0`** — `gpugem/_defaults.py` stays untouched regardless of what the
comparison shows (see `specs/005-residual-tradeoff-benchmark/`,
`specs/007-violation-distribution-figures/`).

```bash
python -m benchmarks.run_residual_tradeoff --all              # reuse 002 + solve per_constraint_residual=0
python -m benchmarks.aggregate_residual_tradeoff               # comparison.csv from committed JSON, no GPU
python -m benchmarks.make_residual_tradeoff_figures             # runtime comparison figures from the CSV, no solver
python -m benchmarks.make_violation_distribution_figures        # violation-distribution figures, no solver
```

`--all` skips a model whose `results/residual_tradeoff/<model>.json` is already up to date; a file
from before the violation-histogram fields existed is automatically re-solved once (printed as
`[backfill] <model>`, not `[skip]`) rather than silently left stale — `--force` still forces an
unconditional re-solve of any model.

Outputs (committed) under `results/residual_tradeoff/`: one `<model>.json` per model (all three
configurations, plus per-row violation histograms for the S-block and, where present, C-block) and
`comparison.csv` (30 rows: 10 models x 3 configurations). Figures under `figures/`:

- `residual_tradeoff_violations.png` / `residual_tradeoff_solvetime.png` — the three-configuration
  comparison for all ten models, hatched `per_constraint_residual=0` bars, both carrying an
  explicit "not a recommended configuration" caption.
- `violation_distribution_equations.png` — a population-pyramid-style figure showing, for every
  model, how many mass-balance equations are violated and by what magnitude under
  `per_constraint_residual=0` (not just the single worst-row number above): violation magnitude on
  the log-scale y-axis, count of equations at that magnitude on the x-axis, equations falling short
  of the required balance mirrored (left) against equations exceeding it (right). Every model is
  overlaid as a semi-transparent filled distribution, colored by a single ordinal ramp keyed to
  model size and labeled directly by name.
- `violation_distribution_constraints.png` — the same layout for coupling constraints, limited to
  the eight models that have a coupling block (`e_coli_core`/`iML1515` are absent, not shown empty).

**Result**: the effect scales with model conditioning, not just size — and it's essentially free
for the two small, well-conditioned models.

| model | vars | shipped_default residual | residual_0 residual | rows violated (>1e-6) | speedup |
|---|---|---|---|---|---|
| e_coli_core | 95 | 7.78e-09 | 7.78e-09 (identical) | 0 | ~0.5x (already sub-second either way) |
| iML1515 | 2,712 | 2.95e-09 | 4.45e-09 | 0 | ~1.0x (no meaningful difference) |
| Harvey | 81,094 | 5.58e-09 | 3.19e-04 | 591 | ~1.4x |
| Harvetta | 83,521 | 3.21e-09 | 4.89e-04 | 1,047 | ~1.0x (no meaningful difference) |
| S84 | 685,998 | 4.72e-05 | 2.57 | 249,173 | ~2.8x |
| S85 | 874,634 | 8.87e-05 | 156.4 | 372,156 | ~71.9x |
| S23 | 1,007,742 | 3.12e-05 | 2.58 | 340,300 | ~54.7x |
| S15 | 1,084,341 | 9.94e-05 | 8.19 | 371,854 | ~17.9x |
| S9 | 1,111,943 | 5.56e-05 | 294.7 | 469,579 | ~48.7x |
| S83 | 1,179,186 | 2.14e-05 | 4.32 | 359,446 | ~32.4x |

For the two small BiGG models, `per_constraint_residual` essentially never binds — the shipped
default and cuOpt's own default land on the same iteration count and residual, confirming this is
specifically a large/ill-conditioned-model phenomenon, not a general cuOpt inefficiency. Harvetta
behaves like Harvey rather than like the microbiome models here — despite being whole-body scale
and having a genuine coupling block, its speedup is negligible (~1.0x), reinforcing that this
effect tracks conditioning severity, not just size: Harvey and Harvetta are both well-conditioned
enough (relative to the microbiome models) that the per-row check costs little extra time even
though it still meaningfully changes the correctness residual (3.2e-09 -> 4.9e-04, 1,047 rows
newly violated). The effect grows sharply with scale and coefficient-range severity: across the
eight whole-body/microbiome models, disabling the per-row check leaves hundreds to hundreds of
thousands of constraint rows violated beyond `1e-6` — a real correctness regression, not numerical
noise, which is exactly why `gpugem` pays the iteration cost
to avoid it. The magnitude of that regression (not just the row count) varies by nearly two orders
of magnitude across the largest models even at similar scale (S9's worst-row residual ~294.7 vs
S23's ~2.58) — visible directly in `violation_distribution_equations.png`, which the single
worst-row number in the table above can't show.

## Gurobi default-settings benchmark

Every Gurobi number published above uses `method=2` (barrier + default crossover), a
deliberate choice this project's benchmark tooling makes. `run_gurobi_default_benchmark.py`
adds a third Gurobi data point per model: `method=-1`, Gurobi's own untouched factory
default (automatic algorithm selection) — exactly what any user who never touches Gurobi's
tuning parameters would get. It reuses, never re-solves, each model's existing cuOpt and
`method=2` results (see `specs/010-gurobi-default-benchmark/`).

```bash
python -m benchmarks.run_gurobi_default_benchmark --all   # reuse existing results + solve method=-1
python -m benchmarks.aggregate_gurobi_default              # comparison.csv from committed JSON, no solver
python -m benchmarks.make_gurobi_default_figure             # solve-time comparison figure from the CSV, no solver
```

`--all` skips a model whose `results/gurobi_default/<model>.json` already exists; `--force`
forces an unconditional re-solve. A default-settings solve that fails the correctness gate
(non-optimal status, out-of-tolerance residual, or objective disagreement with the model's
existing cuOpt result) is still recorded, marked `feasible: false`, and shown as failed on the
figure rather than silently dropped.

Outputs (committed) under `results/gurobi_default/`: one `<model>.json` per model and
`comparison.csv` (10 rows, one per model). Figure under `figures/`:
`gurobi_default_comparison.png` — cuOpt, Gurobi (barrier), and Gurobi (default settings) solve
time, log scale, per-bar annotations.

**Result**: on this host, Gurobi's automatic mode picks simplex for the two small BiGG models
and barrier for every whole-body/microbiome model — the same family of algorithm the project's
deliberate `method=2` choice already uses at that scale, so the two Gurobi numbers land close
together (within roughly 0.7x-1.2x of each other) rather than automatic mode finding something
qualitatively different:

| model | vars | Gurobi (barrier) | Gurobi (default) | default picked | default vs. barrier |
|---|---|---|---|---|---|
| e_coli_core | 95 | 0.00079s | 0.00090s | simplex | ~0.87x |
| iML1515 | 2,712 | 0.034s | 0.028s | simplex | ~1.22x |
| Harvey | 81,094 | 2.82s | 3.80s | barrier | ~0.74x |
| Harvetta | 83,521 | 3.53s | 4.60s | barrier | ~0.77x |
| S84 | 685,998 | 40.6s | 57.5s | barrier | ~0.71x |
| S85 | 874,634 | 52.6s | 75.7s | barrier | ~0.70x |
| S23 | 1,007,742 | 85.3s | 83.7s | barrier | ~1.02x |
| S15 | 1,084,341 | 82.6s | 106.7s | barrier | ~0.77x |
| S9 | 1,111,943 | 73.0s | 92.6s | barrier | ~0.79x |
| S83 | 1,179,186 | 99.6s | 93.5s | barrier | ~1.07x |

Every default-settings solve reached `Optimal` and agreed with cuOpt's objective, so this run
found no model where automatic mode's choice changes the correctness picture — only, in most
cases, a modest time cost relative to this project's already-deliberately-chosen `method=2`.
`gpugem/_defaults.py` and this project's shipped Gurobi wrapper default are unchanged by this
benchmark regardless of what it shows.
