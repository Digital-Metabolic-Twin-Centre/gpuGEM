# Phase 0 Research: S85 Multi-Objective cuOpt vs Gurobi Benchmark

## R1. Candidate pool for ~20 biologically meaningful objectives

**Decision**: Draw the ~20 objectives from S85's existing single-reaction biomass/maintenance
reactions and the model's whole-body objective, spanning distinct organ systems, immune-cell
types, and microbiome taxa — not from newly-constructed composite objectives.

**Rationale**: Inspecting `mWBM_S85_male.mat` directly confirms the pool is large and already
biologically labeled:
- `rxns` has 874,634 entries; 500 of them match `*biomass*` (case-insensitive), covering 236
  distinct compartment prefixes (organs — Kidney, Liver, Brain, Heart, Lung, Muscle, Pancreas,
  Colon, Skin, Retina, ...; immune/blood cell types — Bcells, CD4Tcells, Nkcells, Monocyte,
  Platelet, RBC; and microbiome-related compartments — `Micro`, `Diet`, `GI`, `Excretion`, `SI`,
  `LI` exchange/transport reactions).
- `c` (the model's shipped objective) has exactly one nonzero entry: `Whole_body_objective_rxn`
  — the same reaction the existing cross-scale benchmark (`002`) already uses for S85.
- The `Microbiota` array in the `.mat` file is a boolean/0-1 mask over reactions identifying the
  microbiome-associated subset, giving a direct way to pick taxon-level objectives distinct from
  host-organ objectives.

Because every candidate is already a named single-reaction objective present in the model, no
new reactions or composite objective vectors need to be constructed — each objective is just
"set `c[idx] = 1`, `maximize = True`" exactly like the existing `models.py` pattern used for
Harvey's `Whole_body_objective_rxn`.

**Selection approach for the ~20**: pick a diverse, non-redundant cross-section rather than an
exhaustive or random sample, so the set actually stresses different parts of the network:
1. The model's own whole-body objective (`Whole_body_objective_rxn`) — the baseline already
   measured in `002`, included so the sweep's average can be directly compared to it.
2. ~10 organ/tissue biomass-maintenance reactions spanning different metabolic roles (e.g.
   Liver, Kidney, Brain, Heart, Muscle, Colon, Pancreas, Lung, Skin, Adipocytes) — large,
   metabolically central compartments most likely to differ in solve difficulty.
3. ~5 immune/blood-cell biomass reactions (Bcells, CD4Tcells, Nkcells, Monocyte, RBC or
   Platelet) — smaller, more peripheral compartments as a contrast to organs.
4. ~4 microbiome-associated objectives, selected via the `Microbiota` mask (e.g. a
   community/microbiome biomass or exchange reaction and a couple of taxon-specific ones if
   individually named) — directly relevant since S85 is a microbiome-integrated whole-body model.

Exact reaction names for groups 2-4 are finalized during task execution by running the same
inspection script used for this research (filter `rxns` by the `biomass`/`maintenance` substring
and the `Microbiota` mask, then hand-pick for diversity) and recorded in
`benchmarks/results/s85_objectives/objectives.json` with each entry's category and rationale
(spec FR-002/FR-003) — not hardcoded speculatively in this document.

**Alternatives considered**:
- *Randomly sample 20 reactions from the full 874,634* — rejected: most reactions are internal
  transport/exchange steps with no independent biological interpretation as an "objective" to
  maximize; would fail spec FR-002 (each objective must be biologically interpretable).
- *Use only organ biomass reactions, skip microbiome* — rejected: S85 is specifically a
  microbiome-integrated model (mWBM = "microbiome Whole Body Model"); excluding that axis would
  miss the part of the model most distinctive to S85 vs. e.g. plain Harvey.
- *Construct composite multi-reaction objectives (e.g. weighted sum of two organs)* — rejected:
  adds a design/weighting decision with no clear biological grounding and would deviate from the
  "same LP, different objective vector" pattern the existing benchmark code already supports
  cleanly; single-reaction objectives are sufficient to test the runtime-gap question.

## R2. Progress visibility during a single long blocking solve

**Decision**: Print a start line and a finish line for every (objective, solver) step
(objective id/name, index/total, solver, elapsed on finish), and run a lightweight background
heartbeat thread during each solve call that prints elapsed time every 30s while the call blocks.

**Rationale**: `gpugem.solve` (used by `benchmarks.solve.solve_cuopt`) and the Gurobi wrapper in
`benchmarks.solve.solve_gurobi` are both single blocking calls with no progress callback or
verbose hook (`gpugem/solver.py` has no `verbose`/`callback` parameter). The only way to satisfy
spec FR-005 / SC-002 ("distinguish still solving from hung") without modifying `gpugem`'s public
API (Constitution IV) is an out-of-band heartbeat: start a daemon thread immediately before the
blocking call that sleeps in a loop and prints `"...still solving <objective> on <solver>,
<Ns> elapsed"`, and stop it (via an `Event`) as soon as the call returns. This is the same
technique already informally used for the S85 cross-scale run (~500s cuOpt solves observed in
`002`), just formalized into the sweep runner instead of relying on terminal patience.

**Alternatives considered**:
- *Add a progress callback to `gpugem.solve`* — rejected: out of scope (would touch `gpugem`'s
  solver-facing public API, requiring Constitution IV justification and III test coverage, for a
  benchmarking-only need); cuOpt's own PDLP loop doesn't expose per-iteration callbacks through
  the wrapper today either.
- *Poll GPU utilization via `nvidia-smi` as a proxy for "still working"* — rejected: adds a
  subprocess dependency and platform assumption for a problem the heartbeat thread already solves
  more simply and portably.

## R3. Resumability

**Decision**: Mirror `run_benchmark.py`'s existing pattern exactly — one JSON file per unit of
work (`results/s85_objectives/<objective_id>.json`), skip on restart if it exists unless
`--force`, aggregate at the end.

**Rationale**: Already proven correctness-preserving in `002` (same skip/force semantics, same
"warn + carry `any_failed`" pattern for cells that failed the correctness gate). Reusing it keeps
the two benchmark tools consistent and avoids inventing new resume/checkpoint machinery.

**Alternatives considered**:
- *Single results file updated in place with file locking* — rejected: more failure modes
  (partial-write corruption on interruption) for no benefit over one-file-per-objective, which is
  atomic by construction (a JSON file only appears once `.write_text()` completes).

## R4. Outlier detection for the summary

**Decision**: Flag an objective as an outlier when its cuOpt/Gurobi runtime ratio deviates from
the *median* ratio across all successfully-gated objectives by more than 2x (i.e., ratio <
median/2 or > median*2). Report median (not mean) as the primary spread statistic alongside
min/max, given a sample size of ~20.

**Rationale**: Ratio-based comparison directly answers the motivating question ("is the ~10x gap
typical or an outlier") without needing a distributional assumption; median is robust to the
small sample size and to the possibility that 1-2 objectives are themselves extreme. A fixed 2x
multiplicative band is simple to explain in the summary report (spec SC-004) and matches the
order-of-magnitude framing already used to describe the original S85 result ("~10x").

**Alternatives considered**:
- *Standard-deviation / z-score based outlier detection* — rejected: solve times across
  structurally different objectives are not expected to be normally distributed (some
  compartments are tiny, some are large); z-scores on a right-skewed, n≈20 sample are unreliable.
- *No automated flagging, leave it to visual inspection of the CSV* — rejected: fails spec FR-007
  which explicitly requires the system to identify and call out deviating objectives, not just
  report raw numbers.

## R5. Repeats per objective and total runtime budget

**Decision**: Confirmed default of 1 repeat per (objective, solver), per spec Assumptions — no
change from the spec-level decision, recorded here for the runtime-budget rationale.

**Rationale**: With the previously-measured S85 numbers (Gurobi ~52s, cuOpt ~509s median on one
objective) as a rough scale reference, ~20 objectives x (1 cuOpt + 1 Gurobi) rep is already on
the order of hours if several objectives are similarly large; 3 repeats (matching `002`) would
plausibly triple that to a multi-day run, which conflicts with the spec's own "verbose because it
may take hours" framing (not days). The statistical need for repeats is instead met by having 20
independent objectives, which already shows whether the gap is consistent or objective-specific.

**Alternatives considered**:
- *3 repeats per objective, matching `002`* — rejected for this feature per the above; remains
  available as a manual follow-up (`run_objective_sweep.py --objective ID --reps 3 --force`) for
  any single objective whose 1-rep result looks anomalous, per spec Assumptions.
