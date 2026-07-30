# Phase 0 Research: Expand Cross-Scale Benchmark to Additional Microbiome Models

## R1. Where the 4 new models' source files live

**Decision**: Point the new `REGISTRY` entries' `source` directly at
`benchmarks/model_cache/mWBM_<name>_male.mat` — i.e. leave the files exactly where the user
already put them, rather than moving them to `MWBM_DIR` (the external, env-var-configurable
location S84/S85 use).

**Rationale**: `benchmarks/models.py` already defines `CACHE = HERE / "model_cache"` at module
scope (currently used for cached BiGG SBML files). Each `REGISTRY` entry's `source` is already an
independent literal string — S84/S85 use `MODELS_DIR / "mWBM_S84_male.mat"`, but nothing requires
every large-model entry to share that same base path. Pointing the 4 new entries at `CACHE`
instead is a zero-new-mechanism change: no new environment variable, no fallback-path search
logic, and it respects a deliberate action the user already took (placing the files there) rather
than asking them to relocate ~637MB of data to match a convention that was really just "wherever
S84/S85 happened to be checked out," not a documented requirement.

**Alternatives considered**:
- *Move the 4 files into `MWBM_DIR` to match S84/S85* — rejected: requires moving ~637MB of data
  outside the repo for no functional benefit; the loader (`gpugem.loaders.from_mat`) doesn't care
  where the file lives, only that the path is correct.
- *Add a new env var (e.g. `MODEL_CACHE_DIR`) with fallback search across both locations* —
  rejected: adds configuration surface for a problem four literal path strings already solve;
  `REGISTRY` entries have always been literal per-model paths, not derived from a shared root.

## R2. Protecting the new `.mat` files from accidental commit

**Decision**: Add `benchmarks/model_cache/*.mat` to `.gitignore`.

**Rationale**: Confirmed via `git status` that all 8 new `.mat` files (4 plain + 4 `_lifted`,
~637MB total) are currently untracked *and* unprotected — `.gitignore` has no pattern excluding
them, unlike `__pycache__/`/`*.pyc` which are covered. A single careless `git add -A` or `git add
benchmarks/` would sweep all 637MB into history, which is expensive to undo (requires history
rewriting, not a simple revert). `benchmarks/model_cache/*.xml` (the existing, intentionally
committed BiGG caches: `e_coli_core.xml`, `iML1515.xml`, both already tracked) are unaffected by
an `.mat`-scoped pattern — this matches this project's existing convention that whole-body/
microbiome `.mat` models are never committed (S84/S85 already live entirely outside the repo for
exactly this reason), while small BiGG XML caches are.

## R3. Objective handling for the 4 new models — confirmed, no special case needed

**Decision**: `objective=None` for all 4 new `REGISTRY` entries, identical to S84/S85 — use each
model's own shipped `c` vector unchanged.

**Rationale**: Directly verified by loading each new `.mat` file's raw `c` array: all four
(S9, S15, S23, S83) have exactly one nonzero entry, at `Whole_body_objective_rxn`, coefficient
`1.0` — bit-for-bit the same convention S84/S85 already use. Unlike Harvey (whose `.mat` ships an
all-zero `c` and needs an explicit `objective` override in `REGISTRY`), none of the 4 new models
need any special-casing.

## R4. Repeats and time budget

**Decision**: Reuse `run_benchmark.py`'s existing defaults unchanged (`--reps 3`, `--time-limit
900.0`) for the 4 new models — no per-model override.

**Rationale**: Matches spec Assumptions ("same repeat count and per-model time-limit convention
already used") and requires zero new configuration. All 4 new models are larger than S85
(1,007,742-1,179,186 vars vs. S85's 874,634), and `005`'s finding shows cuOpt's iteration/time
cost scales with model size and conditioning under `gpugem`'s shipped (correctness-first) large-
model settings — so it's plausible one or more of these could approach or exceed the 900s budget.
That's an expected, already-handled outcome, not a gap: `run_benchmark.py`'s existing correctness
gate already reports a `TimeLimit` status as a gate failure (`FAILED`, `both_feasible=False`)
rather than silently treating it as success, which is exactly spec FR-003/User Story 3's
requirement — already satisfied by existing, unmodified code.

**Alternatives considered**: *Raise the time limit preemptively for the new, larger models* —
rejected: no evidence yet that 900s is insufficient for any of the 4, and preemptively loosening
the budget would weaken the same gate spec FR-002 requires applying identically; if a model
genuinely needs more time, that's a finding to make and document (Constitution Principle V),
not something to route around before observing it.

## R5. `make_figure.py`'s ordering change

**Decision**: Replace `df.sort_values(["_sc", "n_cols"])` with `df.sort_values("n_cols")`; drop
the `SCALE_ORDER`/`_sc` scale-class mapping entirely (spec FR-005).

**Rationale**: For the current 5-model set, scale-class-then-size and pure-size ordering produce
the *same* relative order (size happens to increase monotonically with scale class:
small < medium < whole-body < microbiome, verified against the existing committed dimensions), so
this change is a strict simplification, not a behavior change for the existing 5 models. It only
starts to matter once several same-scale-class ("microbiome") models of different sizes coexist —
exactly the situation these 4 new models create.
