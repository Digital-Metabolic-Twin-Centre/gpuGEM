# Implementation Plan: Expand Cross-Scale Benchmark to Additional Microbiome Models

**Branch**: `006-expand-microbiome-benchmark` | **Date**: 2026-07-29 | **Spec**: ./spec.md

**Input**: Feature specification from `/specs/006-expand-microbiome-benchmark/spec.md`

## Summary

Add four new `BenchmarkModel` entries (S9, S15, S23, S83 — all larger than S85, 1.0M-1.18M
variables) to `benchmarks/models.py`'s existing `REGISTRY`, sourced from their plain `.mat` files
already placed under `benchmarks/model_cache/` (not moved), and run them through the `002`
cross-scale benchmark's existing, unmodified tooling (`run_benchmark.py`, same correctness gate).
Change `make_figure.py`'s bar ordering from scale-class-then-size to size-only, and regenerate the
comparison figure to show all nine models. The only code changes are: 4 registry entries, a
one-line sort-key change, and a `.gitignore` entry to stop the new ~637MB of `.mat` files from
ever being accidentally committed (they are untracked today and currently unprotected).

## Technical Context

**Language/Version**: Python 3.13 (host base conda env — same as `002`-`005`)

**Primary Dependencies**: cuopt-cu12 26.6.0, gurobipy 13.0.2, scipy, numpy, matplotlib, pandas —
all already installed, no new dependency. The in-repo `gpugem`/`benchmarks` packages
(`models.build_lp`, `run_benchmark.run_one`, `residual.py`, `make_figure.py`), reused unchanged
except the two edits described in Summary.

**Storage**: `benchmarks/results/<model>.json` for each of the 4 new models (same shape as
existing `S84.json`/`S85.json`), `benchmarks/results/benchmark.csv` (regenerated, now 9 rows),
`benchmarks/figures/benchmark_solvetime.png` (regenerated, now 9 models). Model source files stay
at `benchmarks/model_cache/mWBM_{S9,S15,S23,S83}_male.mat` (research R1) — **not** committed to
git (research R2).

**Testing**: No new test file — this feature adds registry data and a one-line sort-key change to
already-tested code paths (`002`'s `run_benchmark.py`/`make_figure.py` have no existing unit
tests of their own to extend; correctness is validated by the correctness gate itself, which is
unchanged, plus the GPU-host quickstart run). Consistent with how `002` itself was validated.

**Target Platform**: Linux GPU host with an NVIDIA GPU (cuOpt) and a Gurobi license — same host
as `002`-`005`.

**Project Type**: single project — extends `benchmarks/` in place, no `gpugem/` changes.

**Performance Goals**: not a latency target — the deliverable is correctness-gated coverage of 4
additional models plus a regenerated, size-ordered 9-model comparison figure.

**Constraints**: MUST NOT modify `gpugem/_defaults.py` (spec FR-008). MUST NOT alter any of the 5
existing models' committed results (spec FR-007) — achieved for free by `run_benchmark.py`'s
existing skip-if-exists behavior, since the 5 existing `results/<model>.json` files already exist
and `--all` without `--force` will not touch them. MUST NOT commit the new large `.mat` files to
git (research R2 — a genuinely hard-to-reverse mistake at ~637MB if it happened).

**Scale/Scope**: 4 new models (1,007,742-1,179,186 variables — all larger than the current
largest, S85 at 874,634), each solved once with N=3 repeats matching `002`'s existing convention,
producing 4 new result files and one regenerated figure covering all 9 models.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Correctness-Validated Defaults**: PASS — no default changes; new models are solved with
  `gpugem`'s existing size-selected defaults (all 4 exceed the 100K-reaction large-model
  threshold, so they get the same PaPILO-presolve settings S84/S85 already use). The correctness
  gate is applied identically (spec FR-002); a fast-but-wrong result for any new model is
  impossible to report since `002`'s gate already prevents that generically.
- **II. Honest Status/Feasibility Reporting**: PASS — `run_benchmark.py`'s existing "FAILED" /
  `both_feasible=False` handling already covers spec FR-003/User Story 3 with zero new code: a
  new model that fails the gate is marked `FAILED` and excluded from claiming success, exactly
  like any existing model would be.
- **III. Test Coverage for Numerical Behavior**: N/A — no `gpugem/solver.py`, `scaling.py`, or
  `_defaults.py` changes.
- **IV. Minimal, COBRA-Compatible Surface**: PASS — zero `gpugem` changes, zero new public
  surface. `benchmarks/models.py`'s `REGISTRY` is internal tooling data, not a public API.
- **V. Documented Known Limitations**: APPLIES conditionally — if any of the 4 new models
  surfaces a genuinely new solver behavior (e.g. one fails the correctness gate, or is
  dramatically slower even than S85 in a way worth recording), that MUST be added to `README.md`'s
  "Known limitations," per the precedent already set by the S85 finding.

No violations. Complexity Tracking left empty.

## Project Structure

### Documentation (this feature)

```text
specs/006-expand-microbiome-benchmark/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
.gitignore                    # MODIFIED (additive): exclude benchmarks/model_cache/*.mat
                               #   (research R2) -- benchmarks/model_cache/*.xml (existing BiGG
                               #   caches) stay tracked, unaffected

benchmarks/
├── models.py                  # MODIFIED (additive): 4 new REGISTRY entries (S9, S15, S23, S83),
│                               #   source = benchmarks/model_cache/mWBM_<name>_male.mat
│                               #   (research R1), objective=None (research R3 -- matches
│                               #   S84/S85, each model's own shipped c vector is directly usable)
├── run_benchmark.py            # existing — reused unchanged: --model NAME | --all already
│                               #   generalizes to any REGISTRY entry, including the 4 new ones
├── residual.py                 # existing — reused unchanged
├── make_figure.py              # MODIFIED (one line): sort_values(["_sc", "n_cols"]) ->
│                               #   sort_values("n_cols") (spec FR-005); SCALE_ORDER/_sc column
│                               #   removed since scale-class grouping no longer drives ordering
├── model_cache/
│   ├── mWBM_S9_male.mat        # already present (user-added), untracked, now gitignored
│   ├── mWBM_S15_male.mat       # already present (user-added), untracked, now gitignored
│   ├── mWBM_S23_male.mat       # already present (user-added), untracked, now gitignored
│   ├── mWBM_S83_male.mat       # already present (user-added), untracked, now gitignored
│   └── *_lifted.mat            # already present, untouched, out of scope (spec Assumptions),
│                               #   also covered by the new gitignore pattern
├── results/
│   ├── S9.json                 # NEW, same schema as existing S84.json/S85.json
│   ├── S15.json                # NEW
│   ├── S23.json                # NEW
│   ├── S83.json                 # NEW
│   └── benchmark.csv           # REGENERATED — now 9 rows (existing 5 untouched in content,
│                               #   just re-emitted alongside the 4 new rows)
└── figures/
    └── benchmark_solvetime.png # REGENERATED — now 9 models, size-ordered
```

**Structure Decision**: Single project, extending `benchmarks/` in place. This is the smallest
possible change that satisfies the spec: no new modules, no new CLI, no new file format — the 4
new models are just 4 more rows in data structures that `002`'s tooling already generalizes over
(`REGISTRY`, `ALL_MODELS = list(REGISTRY.keys())`, `run_benchmark.py`'s `--all`,
`aggregate_csv()`). The only genuinely new logic is the one-line sort-key change in
`make_figure.py` and the `.gitignore` addition.

## Complexity Tracking

*No Constitution Check violations — this section is intentionally empty.*

**Post-Phase-1 re-check**: data-model.md, contracts/, and quickstart.md confirm the full change
surface is: 4 registry dict entries, one sort-key line, one `.gitignore` line. No `gpugem/`
changes, no new `benchmarks/` modules. Gate still PASSES.
