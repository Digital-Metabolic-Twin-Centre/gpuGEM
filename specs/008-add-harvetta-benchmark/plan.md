# Implementation Plan: Add Harvetta to the Benchmark Suite and Commit Model Files

**Branch**: `008-add-harvetta-benchmark` | **Date**: 2026-08-04 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/008-add-harvetta-benchmark/spec.md`

## Summary

Register Harvetta (the female whole-body counterpart to the already-benchmarked Harvey model) as a
tenth model in the benchmark suite, run it through both existing benchmarks (cross-scale
cuOpt-vs-Gurobi, and the three-configuration `per_constraint_residual` trade-off with its violation
histograms), regenerate every existing comparison figure to include it, and commit the model files
the benchmark suite actually references — Harvetta's plus the four microbiome models added in
feature 006 — to version control, narrowing (not fully removing) the `.gitignore` exclusion so the
size-heavy, currently-unused `_lifted` variants stay untracked. Direct inspection of Harvetta's
`.mat` file (research R1) confirms it needs only a `REGISTRY` entry — same structure, same
objective reaction name as Harvey — no new loader or benchmark-script code.

## Technical Context

**Language/Version**: Python 3.10+ (matches `pyproject.toml` floor)

**Primary Dependencies**: numpy, scipy (sparse + `.mat` I/O), matplotlib (Agg), pandas — all
already project dependencies; no new dependency introduced.

**Storage**: Committed JSON result files and CSVs (existing convention), plus — new for this
feature — five committed binary `.mat` model files (≈ 299 MB) directly in the git repository
(previously gitignored).

**Testing**: `pytest`. No new pure-function logic is introduced (a `REGISTRY` dict entry has no
branch to unit test), consistent with feature 006's precedent; existing tests
(`test_residual_tradeoff.py`, `test_violation_histogram.py`, `test_models.py` if present) are
schema-based and cover Harvetta automatically once it's a `REGISTRY` entry.

**Target Platform**: Linux + NVIDIA GPU for the two solve steps; figure regeneration and the
git-tracking change need neither.

**Project Type**: Single project — benchmarking/analysis scripts under `benchmarks/`, plus a
repository-configuration change (`.gitignore`); no `gpugem` library change.

**Performance Goals**: N/A (benchmark tooling). Harvetta's own solve time is unknown until run —
structurally similar to Harvey (same family, same objective, comparable variable count: 83,521 vs
Harvey's 81,094) so a similar order-of-magnitude solve time is a reasonable expectation, not a
requirement.

**Constraints**: Must not alter any other model's already-recorded result (FR-006). Must not touch
`gpugem/_defaults.py` (FR-008). The git-tracking change must not silently balloon the repository by
committing files no `REGISTRY` entry references (research R3).

**Scale/Scope**: One new model, one new `REGISTRY` entry, two benchmark runs (one solve each,
reusing already-recorded shipped-default/Gurobi results for the trade-off comparison per the
existing `_load_002_result` pattern), five figures regenerated, five files newly committed to
version control (≈ 299 MB), one `.gitignore` line narrowed.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Correctness-Validated Defaults**: PASS. `gpugem/_defaults.py` untouched; Harvetta is run
  through already-validated, unchanged shipped defaults and the already-non-default
  `per_constraint_residual=0` comparison.
- **II. Honest Status/Feasibility Reporting**: PASS — reinforced. FR-004 requires a Harvetta
  correctness-gate failure to be recorded and visibly marked, matching every prior benchmark
  feature; nothing about this feature relaxes that.
- **III. Test Coverage for Numerical Behavior**: PASS. No `gpugem/solver.py`/`scaling.py`/
  `_defaults.py` change; the one new `REGISTRY` entry has no new logic branch requiring a dedicated
  unit test (feature 006 precedent).
- **IV. Minimal, COBRA-Compatible Surface**: PASS. No `gpugem` public API change; all changes are
  under `benchmarks/` plus `.gitignore`.
- **V. Documented Known Limitations**: PASS. `benchmarks/README.md` is updated to document both
  Harvetta's addition and the git-tracking policy change (research R3/R4) explicitly, rather than
  leaving either as an undocumented side effect.

No violations. Re-checked after Phase 1 design (research.md/data-model.md/contracts above) — still
PASS, no new considerations introduced by the design.

## Project Structure

### Documentation (this feature)

```text
specs/008-add-harvetta-benchmark/
├── plan.md              # This file
├── research.md           # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/
│   ├── registry-entry.md
│   └── gitignore-and-tracking.md
└── tasks.md              # Phase 2 output (/speckit-tasks, not yet created)
```

### Source Code (repository root)

```text
benchmarks/
├── models.py                          # MODIFIED: one new REGISTRY["Harvetta"] entry
├── results/
│   ├── Harvetta.json                  # NEW: cross-scale (002) result
│   ├── benchmark.csv                  # regenerated, 10 models
│   └── residual_tradeoff/
│       ├── Harvetta.json              # NEW: trade-off (005/007) result, both histograms
│       └── comparison.csv             # regenerated, 30 rows
├── figures/
│   ├── benchmark_solvetime.png                # regenerated, 10 models
│   ├── residual_tradeoff_solvetime.png        # regenerated, 10 models
│   ├── residual_tradeoff_violations.png       # regenerated, 10 models
│   ├── violation_distribution_equations.png   # regenerated, 10 models
│   └── violation_distribution_constraints.png # regenerated, 8 models (Harvetta has a C-block)
├── model_cache/
│   ├── Harvetta_1_03d.mat             # NEWLY TRACKED
│   ├── mWBM_{S9,S15,S23,S83}_male.mat # NEWLY TRACKED (plain variants only)
│   └── mWBM_*_lifted.mat              # remains untracked (narrowed .gitignore)
└── README.md                          # MODIFIED: document Harvetta + the tracking-policy change

.gitignore                              # MODIFIED: *.mat -> *_lifted.mat (model_cache scope)
```

**Structure Decision**: single project, benchmarks-only functional change (matches every prior
feature's precedent — no `gpugem/` library code touched) plus a narrowly-scoped repository
configuration change (`.gitignore`). No new module, no new script — this feature is purely data
(one `REGISTRY` entry, five newly-committed model files) flowing through already-existing,
already-generalized tooling (research R1/R2).

## Complexity Tracking

*No Constitution Check violations — this section is not needed.*
