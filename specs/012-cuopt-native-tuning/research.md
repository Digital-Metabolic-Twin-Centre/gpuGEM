# Phase 0 Research: cuOpt-Native Settings Tuning for Large Microbiome Models

Every finding below was verified directly — against the actually-installed `cuopt-cu12==26.6.0`
package (source introspection + live empirical test), against the primary cuOpt source repository
checked out locally at `/home/farid/projects/cuOpt` (`v26.08.00a`, commit `c34e4edb`), or by
directly loading and analyzing S85's own matrices — not inferred from a single secondary source.
Where a web-fetched summary disagreed with the primary source, the primary source and empirical
test win (see R2).

## R1. What cuOpt versions are involved, and how the upgrade will be tested

**Decision**: The installed `cuopt-cu12==26.6.0` (June 2026) is not the latest; `26.8.0` (August
2026) is available on PyPI (`pip index versions cuopt-cu12`). cuOpt's version scheme is `YY.MM`.
User Story 2's upgrade evaluation will install `cuopt-cu12==26.8.0` into an isolated virtualenv
(`python -m venv` + `pip install cuopt-cu12==26.8.0`, kept separate from the conda `base`
environment every other published benchmark in this repo depends on), not upgrade the shared
environment in place.

**Rationale**: `pip install --upgrade` in the shared `base` conda environment would retroactively
put every already-published benchmark result (002/004/005/010/011) at risk of being non-reproducible
from a fresh checkout without the exact original version pinned — a real, avoidable risk. A venv
costs nothing and fully isolates the test.

**Alternatives considered**:
- *Build cuOpt from the local `/home/farid/projects/cuOpt` source checkout* — rejected for this
  feature: it's a full C++/CUDA project (`cpp/`, CUDA 12.9 build), a from-source build is a
  multi-hour, high-risk undertaking with no benefit over the official `26.8.0` wheel for the
  narrow question User Story 2 asks (does a newer *released* version change the picture). The
  local checkout is, however, an extremely valuable **documentation and release-notes source of
  truth** (see R2-R4) — used for research, not for building.
- *Upgrade the shared environment in place* — rejected, see Rationale above.

## R2. Ground-truth parameter enumeration and enum semantics (verified, not assumed)

**Decision**: `SolverSettings` in the installed 26.6.0 package exposes 92 named parameters
(`cuopt.linear_programming.solver_settings.solver_settings.solver_params`); most are MIP-only.
The LP/PDLP/Barrier-relevant subset (the sweep's actual search space) is:

| Parameter | Installed default | Meaning (verified) |
|---|---|---|
| `method` | `0` = `SolverMethod.Concurrent` | Concurrent (races PDLP/DualSimplex/Barrier), **not** PDLP — confirms cuOpt's own actual default matches what `specs/004-.../research.md` already established; `gpugem`'s defaults hardcode `method=1` (PDLP-only), foreclosing this space entirely for every model, not just large ones |
| `pdlp_solver_mode` | `4` = `PDLPSolverMode.Stable3` | Enum: `Stable1=0, Stable2=1, Methodical1=2, Fast1=3, Stable3=4`. **`Fast1` was never tried in `specs/004-s85-solver-mode-experiment/`** — that experiment only tried `Methodical1` vs. the `Stable3` baseline. `Fast1` ("fastest mode, but with less success in convergence") is a genuinely new, untested candidate for this sweep |
| `pdlp_precision` | `-1` = Default | See R3 — the enum's actual meaning required empirical correction |
| `presolve` | `-1` = Default (auto) | Enum: `-1=Default, 0=OFF, 1=PaPILO, 2=PSLP` (verified in `constants.h`: `CUOPT_PRESOLVE_DEFAULT/OFF/PAPILO/PSLP`) — gpugem's large-model `presolve=1` is confirmed to mean PaPILO exactly as its own comment claims; but "PSLP is 0" would have been a wrong guess — it's `2`, not `0`. See R4 — presolve=`0` (fully OFF, distinct from PSLP) is what warm start actually requires |
| `per_constraint_residual` | `false` | Already gpuGEM's own deliberate override (`true`) for large models; `specs/005-residual-tradeoff-benchmark/` already quantified the false/true trade-off exhaustively — not re-litigated here, but the false-vs-true axis is included as a checkpoint alongside every other candidate for completeness (FR-010) |
| `crossover` | `false` | Barrier-only; adds a basic-solution recovery step after Barrier converges |
| `infeasibility_detection` | `false` | PDLP-only; can affect whether PDLP terminates early with a (possibly premature) infeasibility verdict |
| `strict_infeasibility` | `false` | PDLP-only; tightens the infeasibility-detection criterion |
| `first_primal_feasible` | `false` | Stop as soon as a primal-feasible iterate is found, without waiting for full dual/gap convergence — directly relevant since S85's bottleneck is convergence speed, not feasibility per se |
| `save_best_primal_so_far` | `false` | Retains the best-seen primal iterate rather than the last one |
| `dual_postsolve` | `true` (when Papilo selected) | Whether postsolve reconstructs dual values |
| `folding`, `dualize`, `ordering`, `augmented`, `eliminate_dense_columns`, `cudss_deterministic`, `barrier_dual_initial_point`, `barrier_iterative_refinement`, `barrier_step_scale` | various | Barrier/cuDSS-specific; relevant only if a Barrier-based candidate is retried (see R4 — the presolve/warm-start finding gives Barrier's ill-fated cold run from `004` a reason to be revisited, this time warm, and these knobs govern the factorization path that previously failed with `NumericalError`) |
| `num_gpus` | `1` | This host has a single GPU (`nvidia-smi`: one RTX A4500, 20 GB) — cuOpt 26.08's new multi-GPU PDLP (METIS-partitioned, 2.5-8.8x speedup reported on 8 NVLink B200 GPUs) is **not reachable on this hardware** and is excluded from the sweep, not silently assumed relevant |

**Rationale**: A web-fetched summary of `docs.nvidia.com/cuopt/user-guide/latest/lp-qp-milp-settings.html`
gave a plausible-looking table, but it disagreed with the primary source on two consequential
points (see R3). Cross-checking against (a) the actual installed package's `IntEnum` definitions
(`PDLPSolverMode`, `SolverMethod` — importable, authoritative for what's actually running) and (b)
the local `cuOpt` C++ source checkout's `constants.h`/`solver_settings.hpp` resolved both
discrepancies. Per the user's explicit "use a scientific approach" instruction, no parameter
semantics is taken as given from a single secondary source when it can be checked directly.

**Alternatives considered**: Trusting the fetched documentation table outright — rejected once it
was caught disagreeing with the installed binary's own enum values (R3); would have produced a
sweep with mislabeled candidates.

## R3. `pdlp_precision` semantics were mischaracterized in `gpugem/_defaults.py`'s own comment — verified empirically

**Decision**: The true enum (confirmed in `cpp/include/cuopt/mathematical_optimization/constants.h`
in the local source checkout, and independently confirmed by a live empirical test against the
installed 26.6.0 binary on `e_coli_core`) is:

```
pdlp_precision:  -1 = Default   0 = Single (FP32)   1 = Double (FP64)   2 = Mixed
```

Empirical test (e_coli_core, `time_limit=30s`, `absolute/relative_*_tolerance=1e-8`,
`per_constraint_residual=1`, all four values):

| value | status | objective | residual_inf | time |
|---|---|---|---|---|
| `-1` (Default) | Optimal | 0.8739215056938601 | 7.780e-09 | 0.475s |
| `0` (Single) | TimeLimit | -0.8739092946052551 | 2.713e-03 | 30.0s (did not converge) |
| `1` (Double) | Optimal | 0.8739215056938601 | 7.780e-09 | 0.254s |
| `2` (Mixed) | TimeLimit | 0.8739216351417145 | 2.878e-06 | 30.0s (did not converge) |

`pdlp_precision=1` and `pdlp_precision=-1` (Default) produce **bit-identical** objective and
residual values — i.e. on this problem, cuOpt's own Default precision mode already resolves to
Double, and `gpugem`'s shipped small-model default (`pdlp_precision=1`) is running Double
precision, not Mixed.

**This does not change any already-published number** — the shipped numeric value (`1`) and its
validated result are untouched; this is a documentation/understanding correction, not a
correctness bug. `gpugem/_defaults.py`'s comment ("`pdlp_precision=1` — mixed FP32/FP64 —
required; double diverges") mislabels which mode is active: it correctly observed that setting `0`
diverges at tight tolerance and that setting `1` converges well, but attributed `0`→"double" and
`1`→"mixed" when the true mapping is `0`→Single and `1`→Double. The FP32 wall in the `0` result
(residual floors at `2.7e-3`, consistent with single-precision's representable range) is the
correct, expected explanation for that divergence — it was just mislabeled as "double diverges"
rather than "single hits its precision floor."

**Consequence for this feature**: true Mixed precision (`2`) has **never actually been tried** on
either the small-model or large-model defaults — it is a genuinely new candidate, not a repeat of
what's already shipped. It is included in the R1/settings sweep for S85 (where large-model
defaults don't set `pdlp_precision` at all, leaving it at cuOpt's own `-1` Default).

**Follow-up (explicitly out of this feature's scope, flagged for the user separately)**: correcting
the comment in `gpugem/_defaults.py` to describe what `pdlp_precision=1` actually is (Double, not
Mixed) is a small, independent documentation fix — not bundled into this investigation, which is
scoped to S85/large models per the spec, not small-model housekeeping.

## R4. `presolve` and warm start — two separate leads, kept separate (a self-correction)

**Decision**: Per the local cuOpt repo's `RELEASE-NOTES.md` and the verified `presolve` enum
(R2/`constants.h`: `-1=Default, 0=OFF, 1=PaPILO, 2=PSLP`), there are **two distinct, unrelated**
findings here — an earlier draft of this research conflated them, which is worth showing rather
than silently fixing, since untangling it is itself an example of the "scientific approach" the
user asked for:

1. **PSLP's false-infeasible fix (26.04) is about `presolve=2` (PSLP), not warm start.** The
   26.04 release notes state *"Update to the latest version of PSLP which includes bug fixes for
   incorrect infeasible classification"* — directly targeting the failure mode
   `gpugem/_defaults.py` documents as the reason large models are forced onto PaPILO
  (`presolve=1`) instead of cuOpt's own default presolver (which, per 26.02's notes, is PSLP
  enabled by default). The installed `26.6.0` postdates this fix. This gives a concrete, testable,
  **standalone** hypothesis independent of warm start: **re-test whether PSLP (`presolve=2`)
  still falsely reports S85 infeasible on the current version** — if the 26.04 fix resolved it,
  PSLP becomes a viable, likely-faster alternative to PaPILO for S85 (PaPILO's postsolve is known,
  per `gpugem/_defaults.py`, to add reconstruction error / carry a hardcoded feastol overhead PSLP
  wouldn't).
2. **PDLP warm start requires `presolve=0` (fully OFF), a different value from PSLP's `2`.** The
   26.02 release notes: *"To use PDLP warm start, presolve must now be explicitly disabled by
   setting `CUOPT_PRESOLVE=0`."* This is **not** "PSLP re-enabled" — it is presolve turned off
   entirely, meaning PDLP would face S85's raw, un-presolved `[1e-6, 2e5]`-range matrix directly.
   That is a materially harder numerical starting point than either PaPILO or PSLP, so this
   candidate is tested with tempered expectations, not framed as something the PSLP fix
   "unlocks" — the two are independent axes.

**A further reconciliation, on which solver mode warm start actually supports**: the release
notes' *"Improved primal/dual warm start for PDLP's default solver mode Stable3"* is not the same
claim as which modes the explicit, callable warm-start API supports. The installed package's own
`SolverSettings.set_pdlp_warm_start_data` docstring states plainly: *"Only supported solver modes
are Stable2 and Fast1."* — i.e. `Stable3` (gpugem's own default mode) cannot be fed a warm start
via the documented Python entry point this sweep would actually call, regardless of what internal
improvement the release note is describing (plausibly an internal restart heuristic distinct from
the user-facing warm-start API). The installed package's own docstring is the more authoritative,
more mechanistically relevant source for what this sweep can actually invoke, so **the concrete
warm-start candidate is `presolve=0` + `pdlp_solver_mode=Stable2` (or `Fast1`) + an explicit
two-phase cold-then-warm solve** — kept as a separate candidate from the PSLP re-test above, not
combined with it.

**Rationale**: Both leads are primary-source-grounded, mechanistically-explained, and independently
testable — not guesses, and not one lead mistakenly built on top of the other. Cross-checking the
release notes against the installed package's own docstring and the verified enum values (rather
than taking any single mention — "Stable3," "`CUOPT_PRESOLVE=0`" — at face value or conflating
adjacent-sounding changes) is exactly the kind of verification this feature's "use a scientific
approach" instruction calls for, and catching an error in one's own reasoning before it reaches the
sweep design is part of that.

**Alternatives considered**: Treating "warm start is broken in 26.6.0" (the existing README
"Known limitations" line) as final — rejected; that finding came from `004`'s cold `Barrier` test
specifically, not from a PDLP/`presolve=0`/`Stable2`-or-`Fast1` combination, so it does not
actually cover the combination this release-notes reading now identifies as worth trying.

## R5. Mathematical structure of S85's LP — why this problem is hard, checked directly on the data

Per the user's explicit request to investigate "the type of mathematical problem" before
deciding how to solve it, S85's actual matrices (loaded via `benchmarks.models.build_lp("S85")`)
were analyzed directly, not assumed from the model family's general reputation:

- **Scale**: `S` is 734,457 × 874,634, 3,618,255 nonzeros (density 5.6e-6). Coupling block `C` is
  1,258,572 × 874,634, 2,519,268 nonzeros.
- **Conditioning**: `S`'s nonzero coefficients span `[1e-6, 2e5]` — a ratio of **~2.0e11**. `C`'s
  span `[1, 2e4]` (ratio 2e4). This is the mechanistic explanation for why cuOpt's PaPILO route is
  required (`gpugem/_defaults.py`) and why PDLP (a first-order method, more sensitive to
  conditioning than a factorization-based method) converges slowly: PDLP's iteration count is
  governed by the problem's condition number, and this one is extreme by construction (the model
  mixes molar stoichiometric coefficients spanning many biological scales — individual reaction
  stoichiometries near 1e-6 to whole-organism biomass coefficients near 2e5 — not a numerical
  artifact that a smarter LP formulation would avoid).
- **Connectivity (does the community model actually decompose)**: treating the bipartite
  row/column incidence graph of `S` alone (mass-balance rows only, no coupling) as an undirected
  graph and computing connected components: **1,593,309 of ~1.6M nodes (99.4%) are in a single
  giant component** — i.e. even without the explicit coupling constraints `C`, the shared
  metabolite pool (blood/lumen compartments) already ties essentially every organism/organ
  together at the level of individual mass-balance rows. Adding `C` back in: **2,861,036 of
  2,867,663 nodes (99.77%)** are in one component; the only other components are 603 tiny
  (11-13-node) fragments, consistent with isolated dead-end reactions, not meaningful sub-blocks.
- **Implication for the preprocessing fallback (User Story 3)**: this rules out the most obvious
  non-simplifying preprocessing idea — decomposing the community model into independent
  per-organism LPs solved separately and stitched back together — because the model is not
  graph-decomposable in the first place; the shared lumen/blood metabolite pool makes it one
  single tightly-coupled system by construction, not an artifact of how the coupling constraints
  are layered on top. Any preprocessing that still claims to recover the exact original result
  would need genuine decomposition machinery (e.g. Dantzig-Wolfe / ADMM-style coordination across
  the single connected block) — a materially larger undertaking than "a preprocessing step," which
  further reinforces the spec's existing P3/discouraged ranking for this path.
- **Internal scaling is already applied by cuOpt, non-configurably**: the local source checkout
  confirms PDLP performs its own internal Ruiz/geometric equilibration
  (`pdlp_hyper_params_t`, not exposed via the public 92-parameter `SolverSettings` surface used by
  `gpugem`) — so a user-side "just rescale the matrix better" preprocessing step is likely
  substantially redundant with what cuOpt already does internally before the first PDLP iteration,
  further explaining why this axis is deprioritized relative to the settings sweep.

**Rationale**: This directly answers the user's request to understand the mathematical problem
before choosing how to attack it — the finding that the model does **not** decompose (contrary to
what "community model" might suggest) is a genuine, non-obvious result that reshapes what
"preprocessing" could even mean here, and the extreme, biologically-inherent (not artifactual)
conditioning explains PDLP's iteration-count-driven slowness independent of any specific setting.

**Alternatives considered**: Assuming block-angular structure without checking (common for
multi-organism community models in the literature) — rejected once the connectivity computation
showed the opposite on this specific model family.

## R6. Sweep orchestration reuses `specs/004-s85-solver-mode-experiment/`'s subprocess-per-candidate pattern

**Decision**: Each candidate configuration (settings sweep, version-upgrade re-run, and any
preprocessing-fallback trial) runs as its own subprocess via `subprocess.run([sys.executable,
"-m", ...], timeout=budget)`, exactly as `run_solver_mode_experiment.py` already does, rather than
in-process.

**Rationale**: This feature explicitly enumerates untested territory (`Fast1` mode, true Mixed
precision, warm start on Stable3, presolve=0 revisited, Barrier retried warm) — several of which
are exactly the kind of previously-untested-on-this-model-family combinations `004`'s research.md
already identified subprocess isolation as necessary for (CUDA context crashes are uncatchable
in-process; a fork-based approach is unsafe with CUDA). No new rationale is needed beyond what
`004`'s R1/R2/R3 already established — reusing the proven pattern outright (see
`specs/004-s85-solver-mode-experiment/research.md`).

**Alternatives considered**: none re-litigated — see `004`'s research.md for the full
in-process-vs-subprocess-vs-multiprocessing analysis, which applies unchanged here.

## R7. Correctness gate reuses the project's existing per-repeat, residual+objective-agreement gate

**Decision**: Every candidate (across all three user stories) is graded against S85's existing,
already-published Gurobi ground truth using the same gate already used throughout this project:
`status == "Optimal"`, stoichiometric residual `||S v - b||_inf` within tolerance, and objective
agreement with Gurobi within relative tolerance — reusing `benchmarks/residual.py`'s existing
`feasibility_residual`/`objectives_agree` helpers, not a new correctness definition.

**Rationale**: Consistency with `specs/002`, `specs/004`, `specs/010`, `specs/011` — a candidate
that "solves fast" by a different correctness standard than everything else in this project would
be an apples-to-oranges comparison, and would violate FR-006 (never trade correctness for speed).
Gurobi's S85 result is reused (not re-solved) per FR-003 — it is a read-only oracle input.

**Alternatives considered**: A looser/tighter gate specific to this experiment — rejected; the
whole point of "credibility" language throughout this project's other benchmarks (`010`, `011`) is
one consistent bar applied everywhere.

## R8. Preprocessing fallback candidates (User Story 3), if reached

**Decision**: If R1-R7's settings sweep and version-upgrade evaluation do not produce a
verified-correct win, the only preprocessing candidates considered are ones that are *provably
invertible* at the LP level — i.e. a linear reformulation whose solution can be mapped back to the
original variable space exactly (e.g. an explicit, recorded row/column scaling applied before the
solve and exactly inverted after, with the inversion itself checked against the correctness gate
before any speed claim, per FR-008/SC-003). Given R5's finding that cuOpt already performs
internal Ruiz-style scaling non-configurably, a from-scratch external rescaling is not expected to
add much — the fallback's main remaining candidate is external row/column equilibration tuned
specifically to this model's known `[1e-6, 2e5]` range (R5), applied and then exactly inverted,
purely as a documented, honest last resort per the spec's explicit de-prioritization of this path.

**Rationale**: Matches the spec's FR-008 (no reduction/aggregation/approximation) and User Story
3's requirement that the reconstructed result be checked for correctness *before* speed is even
considered relevant.

**Alternatives considered**: Any decomposition-based preprocessing (per-organism block solving) —
ruled out by R5's connectivity finding, not merely deprioritized.

## R9. Isolated-environment mechanics for the upgrade test (User Story 2)

**Decision**: `python3 -m venv <scratch-path>/cuopt-26.8-venv && <venv>/bin/pip install
cuopt-cu12==26.8.0 numpy scipy` (matching this project's existing `pyproject.toml` pins for
`numpy`/`scipy`), then invoke the same worker entry-point pattern as R6 with that venv's
interpreter (`subprocess.run([<venv>/bin/python, "-m", ...])`) rather than `sys.executable`.
Gurobi's ground-truth result is read from the already-published JSON (no Gurobi install needed in
the scratch venv at all — reinforcing FR-006's no-proprietary-runtime-dependency constraint).

**Rationale**: Keeps the shared `base` conda environment (and every already-published benchmark
that depends on its exact `cuopt-cu12==26.6.0` pin) completely untouched; a plain `venv` is
sufficient since only `cuopt-cu12`, `numpy`, and `scipy` are needed to run a bare LP solve
in isolation (no `gurobipy`, no `cobra`, no `gpugem` package install needed — the worker can
import `benchmarks.models`/`gpugem` directly from the repo checkout via `sys.path`, same as every
other benchmark script already does).

**Alternatives considered**: A full `conda create` clone of `base` — rejected as unnecessarily
heavy (multi-GB, slow) for a test that only needs three packages.
