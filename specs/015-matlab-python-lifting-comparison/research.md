# Phase 0 Research: MATLAB vs Python Lifted-Model Runtime & Fidelity Comparison

## R1. Model-source parity between the two pipelines

**Decision**: Both pipelines load the identical, already-committed model files under
`benchmarks/model_cache/`, never a re-exported or re-derived copy:

- `e_coli_core` / `iML1515` — cached SBML (`benchmarks/model_cache/{name}.xml`), written by
  `benchmarks/models.py::_load_cobra`. MATLAB's COBRA Toolbox reads the same file directly via
  `readCbModel`.
- `Harvey` / `Harvetta` / `S84` / `S85` — native COBRA `.mat` files (already the *original* MATLAB
  format; Python never round-trips them). Confirmed directly: `gpugem/loaders.py::from_mat`
  (lines 50-110) parses exactly the native COBRA field names -- `S, b, c, lb, ub, csense,
  osenseStr` and, for whole-body/microbiome models, `C, d, dsense, ctrs` -- meaning the temporary
  MATLAB script can `load()` the same `.mat` file and read those same fields with zero conversion,
  guaranteeing both pipelines start from byte-identical model data.

**Rationale**: FR-005/SC-002/SC-003's cross-language agreement claim is only meaningful if both
pipelines are solving the same input. Reusing the already-committed files (rather than exporting a
fresh copy from either side) removes an entire class of "which export step introduced the
mismatch" ambiguity.

## R2. `reformulate.m`'s exact input/output contract

**Decision**: Confirmed directly from source
(`cobratoolbox-f-develop/src/base/solvers/rescale/reformulate.m`) and its test
(`test/verifiedTests/base/testLifting/testReformulate.m`):

```matlab
LPproblem_lifted = reformulate(LPproblem, BIG, printLevel);
```

`LPproblem` is a single struct with a **combined** constraint matrix -- `.A`, `.b`, `.c`, `.lb`,
`.ub`, `.csense` (one char per row), optional `.modelID`. Internally (reformulate.m ~line 76),
mass-balance rows are identified as `csense == 'E' & b == 0` and lifted via
`lift_mass_balance`'s ported algorithm; other rows matching the two-nonzero-opposite-sign pattern
are lifted via the coupling transform -- exactly the same row classification
`gpugem/lifting.py`'s module docstring already documents as the faithful Python translation
(spec 013). The output is the same struct shape, reformulated, with `.modelID` prefixed `'L_'`.

**Rationale**: The temporary MATLAB script must therefore **stack** the model's mass-balance block
(`S`, `b`, all-`'E'`) and coupling block (`C`, `d`, `dsense`) into one `LPproblem.A`/`.b`/`.csense`
before calling `reformulate` -- mirroring exactly how `benchmarks/solve.py::solve_gurobi` (lines
68-83) already classifies coupling rows into equality/upper/lower groups for Gurobi's own
`addMConstr` calls. Same row-sense logic, both languages.

## R3. Gurobi invocation in MATLAB, matched to the Python side's configuration

**Decision**: Standard COBRA Toolbox path: `changeCobraSolver('gurobi', 'LP')` then
`solveCobraLP(LPproblem, 'method', 2)` (barrier, matching `benchmarks/solve.py::solve_gurobi`'s
`method=2` default, confirmed at solve.py:41-52 as this project's established Gurobi
configuration -- not the separate, explicitly-labeled `gurobi_default`/`method=-1` variant from
spec 010). Both this machine's MATLAB (R2025a, confirmed installed) and Python environment resolve
the same Gurobi 11.0.x installation (`GUROBI_HOME=/opt/gurobi1103/linux64`,
`GRB_LICENSE_FILE` set), so no separate license or version-skew concern exists.

**Rationale**: FR-006 requires matched solver settings; barrier is this project's own established
Gurobi convention (reused, not reinvented) for every non-`gurobi_default` benchmark, including the
Python-lifted-and-solved side this feature adds.

## R4. The Python-side "lift then solve with Gurobi" pipeline does not exist yet -- assembled, not built from scratch

**Decision**: No existing entry point lifts a model and solves it with Gurobi in one step. This
feature assembles one from three already-existing, already-validated primitives, with no changes
to `gpugem/solver.py`, `gpugem/scaling.py`, or `gpugem/_defaults.py`:

1. `gpugem.lift_mass_balance(S, b, big=lift_big)` and `gpugem.lift_coupling(C, d_lb, d_ub,
   lift_big, mapping)` (spec 013) -- already used exactly this way, for reporting rather than
   solving, in `benchmarks/run_model_lifting_validation.py::scale_report` (lines 43-66).
2. `benchmarks.solve.solve_gurobi(lp, time_limit, method=2)` (unchanged) -- solves whatever
   `S`/`C`/`b`/`d_lb`/`d_ub`/`lb`/`ub`/`c` dict it is given; it has no opinion about whether that
   system is lifted.
3. `gpugem.map_back(fluxes_lifted, mapping)` (spec 013) -- restricts the lifted solution back to
   the original variable indices.

**Rationale**: Since none of `gpugem`'s three numerically-sensitive files change, Constitution
Principle III's mandatory-test requirement is not triggered in its literal sense -- but this
feature still adds `tests/` coverage for the new glue, matching the shape (not the letter) of
every sibling benchmark feature (`test_model_lifting_validation.py`,
`test_version_lifting_comparison.py`).

## R5. Correctness tolerances and the repeated-run/median convention

**Decision**: Reused verbatim, not re-derived:

- `RES_TOL = 1e-4`, `OBJ_TOL = 1e-6` -- `benchmarks/run_model_lifting_validation.py` lines 31-32,
  spec 013's own established correctness gate.
- Repeated-run/median timing -- the same pattern already used throughout `benchmarks/` (e.g.
  `run_gurobi_default_benchmark.py`'s `solve_s_median` field, `run_benchmark.py`'s `reps`
  argument), applied identically to both the MATLAB and Python pipelines so neither side's
  runtime is measured more or less generously.

**Rationale**: A cross-language comparison whose tolerance or repeat convention differed between
the two sides would not be a fair comparison. Reuse removes that risk entirely.

## R6. Expected per-model time budget on this machine

**Decision**: From spec 014's own research (R2), of the six in-scope models only **S85**
(874,634 vars) is expensive at all -- Gurobi's *unlifted* solve there is ~52.6s; the rest resolve
in low tens of seconds or faster at the project's existing 900s time-limit convention
(`benchmarks/_version_lifting_worker.py` default). Lifting adds rows/variables but spec 013 already
solved every one of these six models lifted (with cuOpt) without any runtime blow-up requiring a
special exclusion path. This is an order-of-magnitude expectation, not a guarantee for the
MATLAB-specific path (which has never been run in this project before) -- the spec's "impractically
long -> document as excluded" edge case (FR-009) remains the safety valve if a genuine
MATLAB-specific slowdown appears, but is not expected to trigger for any of the six models.

**Rationale**: Confirms the six-model scope is tractable as a same-day, single-machine exercise,
consistent with the user's clarification that both pipelines run locally here.

## R7. Comparison figure: new figure, not an extension of an existing one

**Decision**: Unlike spec 014 (which extended `benchmark_solvetime.png`), this feature has no
existing figure to extend -- MATLAB has never been run in this project before. A new,
standalone grouped-bar figure (styled after `benchmarks/make_gurobi_default_figure.py`'s
already-established pattern: log-scale y-axis, per-model grouped bars, annotated values, CVD-safe
palette) shows, per model, the MATLAB-lifted-and-Gurobi-solved runtime beside the
Python-lifted-and-Gurobi-solved runtime. Colors are reused verbatim from
`benchmarks/make_residual_tradeoff_figures.py::CONFIG_COLOR` (already CVD-validated, per that
file's own established precedent -- `make_gurobi_default_figure.py` already reuses the same
palette rather than re-validating), and export follows Constitution Principle VI exactly: 300+ dpi
PNG for browsing, PDF for the vector/publication copy (not EPS, per the constitution's explicit
PDF-over-EPS rationale), sized/captioned per this project's already-established target journal
convention (no baked-in title/caption inside the image itself).

**Rationale**: Directly implements FR-010/FR-011/SC-001/SC-006 while reusing, rather than
reinventing, this project's figure tooling and validated palette.

## R8. Where the temporary MATLAB script lives

**Decision**: The MATLAB script that calls `reformulate` + `solveCobraLP` never enters either
repository's tracked source tree (not committed to gpuGEM, not committed to
`cobratoolbox-f-develop`, not even gitignored-in-place) -- it is written and run from a scratch
location outside both repos' working trees, exactly matching the user's own framing during
clarification ("does not need to be added to the gpuGEM project as it is out of its scope").
Its **output** -- one JSON result per model, schema mirroring the Python side's own result shape
(data-model.md) -- is what gets copied into `benchmarks/results/matlab_python_lifting/` and
committed, the same way every other benchmark feature commits its `results/*.json` while the
process that produced version-pinned or environment-specific data (e.g. spec 014's `/tmp` venv)
stays outside the repo.

**Rationale**: This is the cleanest resolution consistent with both FR-007 (script itself must not
become a permanent deliverable of either repo) and this project's existing convention of
committing benchmark *results* regardless of how ephemeral the process that produced them was.
`cobratoolbox-f-develop` has its own, separate spec-kit gate for any change to its tracked
codebase (confirmed via that repo's `CLAUDE.md`) -- keeping the script entirely outside its
tracked tree avoids that gate being implicated for a script that was never meant to be permanent
there either.
