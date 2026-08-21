# Implementation Plan: cuOpt-Native Settings Tuning for Large Microbiome Models

**Branch**: `012-cuopt-native-tuning` | **Date**: 2026-08-20 | **Spec**: ./spec.md

**Input**: Feature specification from `/specs/012-cuopt-native-tuning/spec.md`

## Summary

Add a `benchmarks/` investigation that systematically sweeps cuOpt's documented LP-relevant
solver settings against S85 (874,634 vars, the same model `specs/004-s85-solver-mode-experiment/`
already used), grounded in primary-source verification rather than assumption (research.md
R1-R9): ground-truth parameter/enum semantics read from the installed package and the local cuOpt
source checkout (`/home/farid/projects/cuOpt`), a corrected understanding of `pdlp_precision`'s
actual meaning (R3), a concrete new candidate — `presolve=0` + `pdlp_solver_mode=Stable2`/`Fast1`
+ explicit warm start — surfaced by reading the actual release notes rather than repeating `004`'s
already-published "warm start is broken" finding at face value (R4), and a direct mathematical
characterization of S85's matrices (R5: extreme `[1e-6, 2e5]` conditioning, and — checked, not
assumed — the model does *not* graph-decompose into per-organism blocks even before the coupling
constraints are added). A second, secondary avenue evaluates whether upgrading to the newer
`cuopt-cu12==26.8.0` release (tested in an isolated venv, never touching the shared environment
other published benchmarks depend on) changes any of this. A third, explicitly last-resort avenue
evaluates one non-simplifying preprocessing candidate only if the first two produce no
verified-correct win. Every candidate is graded by this project's existing correctness gate
(residual + Gurobi objective agreement, reusing S85's already-published Gurobi result) and runs in
an isolated subprocess exactly like `004` already established is necessary for this model family.
`gpugem/_defaults.py` is never edited by this feature — it is an investigation, and promoting any
winning candidate to a shipped default is an explicit, separate follow-up.

## Technical Context

**Language/Version**: Python 3.13 (host base conda env for the settings sweep and preprocessing
fallback; a separate isolated `venv` — also Python 3.13 — for the `26.8.0` upgrade test, see
research.md R9)

**Primary Dependencies**: `cuopt-cu12` 26.6.0 (installed) and 26.8.0 (isolated venv, upgrade
test only), `gurobipy` 13.0.2 (read-only ground-truth oracle — S85's already-published result is
reused, never re-solved by this feature), `scipy`, `numpy` — the in-repo `gpugem` package
(`solve`, unchanged — every candidate is expressed as `**cuopt_kwargs`, gpuGEM's existing per-call
override mechanism, exactly like `004`) and `benchmarks` package (`models.build_lp`, `solve.py`,
`residual.py`), all reused. No new third-party dependency added to the project's own
`pyproject.toml`.

**Storage**: flat files — `benchmarks/results/cuopt_tuning/<candidate_id>.json` (one per
candidate, across all three user stories), `benchmarks/results/cuopt_tuning/summary.json`/`.csv`
(the single ranked comparison FR-010/SC-004 require), mirroring `004`'s
`results/s85_solver_modes/` convention.

**Testing**: `pytest` for the candidate registry (every candidate has a valid, well-formed
`cuopt_kwargs` dict; the warm-start two-phase candidates are correctly marked as needing a
cold-then-warm pair, not a single solve) and the aggregation/ranking math (speedup factor,
best-verified-correct-candidate selection, never-report-a-win-that-fails-the-gate), all on
synthetic candidate results — no GPU/Gurobi required, same pattern as `004`'s
`test_solver_mode_variants.py`. Actual sweep runs are exercised on the GPU host per
`quickstart.md`.

**Target Platform**: Linux GPU host with one NVIDIA GPU (confirmed via `nvidia-smi`: a single RTX
A4500, 20 GB — cuOpt 26.08's new multi-GPU PDLP is not reachable on this hardware and is excluded,
not silently assumed relevant) and a Gurobi license — same host as `002`/`004`/`010`/`011`.

**Project Type**: single project — extends the existing `benchmarks/` CLI tooling package. No
change to `gpugem/` (unlike `004`, which added one additive field; this feature needs nothing new
from `gpugem.solve`'s existing `**cuopt_kwargs`/return-value surface).

**Performance Goals**: not a latency target — the goal is a *measurement*: does any candidate
(settings, version upgrade, or last-resort preprocessing) reduce cuOpt's wall time on S85 below
the current large-model default's baseline while remaining verified-correct, and if so by how
much.

**Constraints**: each candidate gets its own time budget (reused convention: 900s cuOpt-level +
60s subprocess-level grace, same as `004`); a candidate that does not finish is recorded as
inconclusive (`TimeLimit`/`timeout`/`crashed`), never silently dropped (FR-005/FR-010). Every
candidate runs in its own OS process (research.md R6). The upgrade test (User Story 2) runs in an
isolated venv that never touches the shared conda environment other published benchmarks depend on
(research.md R1/R9).

**Scale/Scope**: one model (S85, 874,634 vars / 1,993,029 total rows), one fixed objective
(whole-body, for direct comparability to the already-published baseline), roughly a dozen settings
candidates grounded in research.md's ground-truth parameter enumeration (not an exhaustive
cross-product — spec Edge Cases explicitly rules that out) + 1 fresh baseline re-solve + up to ~3
re-runs under the upgraded version (baseline + best 1-2 candidates, per User Story 2's scope) +ᅟ
at most 1 preprocessing candidate if User Stories 1/2 produce no win.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Correctness-Validated Defaults**: PASS — this investigation never edits
  `gpugem/_defaults.py` (spec FR-009); every candidate is expressed as a per-call `**cuopt_kwargs`
  override through `gpugem.solve`'s existing, already-documented mechanism. Promoting a winning
  candidate to a shipped default is explicitly out of this feature's scope (spec Assumptions) and
  would need its own benchmark-backed justification as a later, separate change.
- **II. Honest Status/Feasibility Reporting**: PASS — reuses `benchmarks.residual`'s existing
  feasibility/objective-agreement checks verbatim (research.md R7); a candidate that times out,
  errors, or is rejected by cuOpt as an invalid combination is recorded as such, never coerced into
  "Optimal" or silently dropped (spec FR-005/FR-010, Edge Cases).
- **III. Test Coverage for Numerical Behavior**: N/A this time — unlike `004`, this feature adds
  no change to `gpugem/solver.py`, `gpugem/scaling.py`, or `gpugem/_defaults.py`; every candidate
  is expressed purely through `gpugem.solve`'s existing `**cuopt_kwargs` passthrough. New
  `benchmarks/`-side numerical logic (correctness gating, speedup ranking) still gets dedicated
  unit tests per the project's established `benchmarks/` testing convention, just not because this
  principle strictly requires it for files it doesn't name.
- **IV. Minimal, COBRA-Compatible Surface**: PASS — no new public surface on `gpugem` at all this
  time (contrast with `004`'s justified `solved_by` addition); this feature is entirely new
  `benchmarks/` tooling.
- **V. Documented Known Limitations**: APPLIES — this feature's own Phase 0 research already
  surfaced one finding worth recording regardless of the sweep's outcome: `gpugem/_defaults.py`'s
  comment mischaracterizes `pdlp_precision=1` as "mixed" when it is actually "double" (research.md
  R3) — a documentation correction, not a behavior change (the shipped numeric default and its
  validated result are untouched). This is flagged to the user directly and, if they agree, is a
  tiny separate doc-only fix, not bundled into this feature's own commits. Any new limitation the
  sweep itself surfaces (e.g. a candidate that reveals a new cuOpt bug) MUST be recorded in the
  README's "Known limitations" section as part of this feature's results, matching `004`'s
  precedent.
- **VI. Publication-Ready Figure Standards**: APPLIES IF a figure is produced — if the final
  comparison is presented as a chart (not just the required CSV/JSON), it MUST follow the
  constitution's figure standards (CVD-validated color, PDF vector copy, no baked-in captions).
  Given this feature's primary deliverable is a ranked comparison table (SC-004), a figure is
  optional scope, added only if it materially clarifies the result — not a hard requirement.

No unjustified violations. No Complexity Tracking entries needed (contrast with `004` — this
feature adds no new `gpugem` public surface).

## Project Structure

### Documentation (this feature)

```text
specs/012-cuopt-native-tuning/
├── plan.md              # This file (/speckit-plan command output)
├── research.md           # Phase 0 output (/speckit-plan command) — R1-R9
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md         # Phase 1 output (/speckit-plan command)
├── contracts/            # Phase 1 output (/speckit-plan command)
└── tasks.md              # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
benchmarks/
├── models.py                      # existing — reused unchanged: build_lp("S85")
├── solve.py                       # existing — reused unchanged: solve_gurobi (baseline reference,
│                                   #   only ever read from committed results/S85.json, never re-run)
├── residual.py                    # existing — reused unchanged: correctness gate
├── cuopt_tuning_candidates.py     # NEW: the full candidate registry (mirrors
│                                   #   solver_mode_variants.py's pattern) — one entry per settings
│                                   #   candidate (research.md R2/R3/R4), each with id, cuopt_kwargs,
│                                   #   a two-phase warm-start flag where applicable, a
│                                   #   `source_note` field recording which research.md finding
│                                   #   motivated it (spec FR-011: traceability), and the
│                                   #   version-upgrade re-run list (which candidate ids to re-test
│                                   #   under 26.8.0)
├── run_cuopt_tuning.py            # NEW: orchestrator CLI — for each candidate, launches a
│                                   #   subprocess (research.md R6) against the installed 26.6.0;
│                                   #   `--upgrade-venv <path>` re-runs the baseline + best
│                                   #   candidate(s) under an already-provisioned 26.8.0 venv
│                                   #   (research.md R1/R9); `--preprocessing` runs the one
│                                   #   last-resort candidate (research.md R8), only meaningful
│                                   #   after Stories 1/2 are recorded
├── _cuopt_tuning_worker.py        # NEW: subprocess entry point — solves one candidate (or the
│                                   #   cold+warm pair for a warm-start candidate), prints its JSON
│                                   #   result to stdout for the parent to capture; runnable under
│                                   #   either the base env's or the upgrade venv's interpreter
├── aggregate_cuopt_tuning.py      # NEW: reads results/cuopt_tuning/*.json -> one ranked
│                                   #   comparison (speedup vs. baseline, verified-correct or not,
│                                   #   which user story/avenue each row belongs to) ->
│                                   #   summary.json + summary.csv (spec FR-010/SC-004)
├── results/
│   └── cuopt_tuning/
│       ├── <candidate_id>.json    # one per candidate across all three user stories
│       └── summary.csv            # the single ranked comparison
└── README.md                      # existing — append a section for this investigation, plus the
                                     #   pdlp_precision documentation-correction note (research.md R3)

tests/
└── test_cuopt_tuning.py           # NEW: candidate-registry validation (well-formed kwargs,
                                     #   correct warm-start pairing) + ranking/speedup math on
                                     #   synthetic results (no GPU/Gurobi required)
```

**Structure Decision**: Single project, extending `benchmarks/` in place exactly like `004`/`011`.
Results are namespaced under `results/cuopt_tuning/` so they don't collide with `002`'s
`results/S85.json`, `004`'s `results/s85_solver_modes/`, or `005`'s `results/residual_tradeoff/`.
No `gpugem/`-internal change at all this time — the entire feature lives in `benchmarks/` and
`tests/`, a smaller footprint than `004`.

## Complexity Tracking

*No entries — this feature adds no new `gpugem` public surface and no Constitution Check
violations requiring justification.*
