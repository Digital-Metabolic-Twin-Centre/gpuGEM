# Phase 0 Research: Add Harvetta to the Benchmark Suite and Commit Model Files

## R1: Harvetta's `.mat` file needs a REGISTRY entry only — no new loader code

Inspected `benchmarks/model_cache/Harvetta_1_03d.mat` directly (`scipy.io.loadmat`):

- Top-level struct key is **`female`** (not `modelReduced`, Harvey's key) — a standard COBRA-style
  struct with `S, b, lb, ub, c, csense, osenseStr` plus a genuine coupling block
  (`C, ctrs, d, dsense` all present, `C` has 217,103 nonzero entries), matching Harvey's shape, not
  the flat/top-level-keys layout the microbiome (mWBM) models use.
- `S` shape: 58,851 rows × 83,521 columns — so Harvetta has **83,521 variables**, larger than
  Harvey's 81,094. `lb`/`ub` use the same `±1e6`/`±1,000,000`-style sentinel convention already
  handled by `gpugem.loaders.from_mat` for every other model here.
- The `c` (objective) vector is all-zero in the raw file — same as Harvey, the objective must be
  set explicitly by reaction name, not read from `c` directly.
- Searched `rxns` for the objective: **`Whole_body_objective_rxn` is present verbatim** — the
  exact same reaction name Harvey already uses. This is expected (Harvey and Harvetta are the
  male/female pair from the same whole-body reconstruction pipeline, sharing reaction-ID
  conventions by design) and confirms the spec's assumption empirically rather than leaving it
  untested.

**Decision**: register Harvetta exactly like Harvey — `kind="mat"`, `model_key="female"`,
`objective="Whole_body_objective_rxn"`, `source=str(CACHE / "Harvetta_1_03d.mat")`,
`scale="whole-body"`. `benchmarks/models.py::build_lp`'s existing `kind == "mat"` branch and
`_mat_rxns` helper already handle an arbitrary `model_key` string and an explicit named objective
(this is exactly the code path Harvey already exercises) — no new loader logic, no new branch, one
new `REGISTRY` entry. Matches feature 006's precedent of zero-new-loader-code model onboarding.

**Alternatives considered**: probing `model_key="modelReduced"` (Harvey's key) first — rejected
once the actual top-level key (`female`) was found by inspection; guessing rather than inspecting
would have produced a `KeyError` at first solve.

## R2: `_solve_residual_0` and both figure scripts already generalize to any `ALL_MODELS` entry — no changes needed there either

`benchmarks/run_residual_tradeoff.py::main()` iterates `M.ALL_MODELS`; `_solve_residual_0` reads
`lp["C"]`/`lp["d_lb"]`/`lp["d_ub"]` generically (present or `None`) to decide whether to compute a
`violation_histogram_constraints` entry. Since Harvetta has a genuine coupling block (R1), it will
automatically get both histograms once solved — no special-casing, and it will automatically
appear in `violation_distribution_constraints.png`, not just the equations figure. This mirrors
exactly how feature 007 already generalizes across every model with a `C` block (Harvey, S84/S85,
S9/S15/S23/S83) with zero code change required for a ninth (now tenth) member. `make_figure.py` and
`make_residual_tradeoff_figures.py` already size their figures by `len(models)` (feature 006/007's
fix), so a tenth model needs no further width adjustment beyond what's already in place.

**Decision**: no code changes to any of the three benchmark-running/figure scripts. Onboarding
Harvetta is: one `REGISTRY` entry, then re-running `run_benchmark.py --all`,
`run_residual_tradeoff.py --all`, and both `make_*` figure scripts — identical operational sequence
to feature 006 + 007 combined, applied to one model instead of four.

## R3: Git-tracking scope — commit the files the benchmark suite actually uses, not every file that happens to sit in the directory

`benchmarks/model_cache/` currently contains, per model, both a plain `.mat` and a `_lifted.mat`
variant for S9/S15/S23/S83 (added in feature 006); only the plain variant is registered in
`REGISTRY` and used by any benchmark — the `_lifted` variants were explicitly called out as
out-of-scope in feature 006's own spec (its Edge Cases: "out of scope for this feature — only the
plain variant is used") and this feature's own spec repeats that framing in its Assumptions.

Exact current sizes (`ls -la`):

| file | size |
|---|---|
| `Harvetta_1_03d.mat` | 13.9 MB |
| `mWBM_S9_male.mat` | 72.4 MB |
| `mWBM_S9_male_lifted.mat` | 89.2 MB |
| `mWBM_S15_male.mat` | 70.6 MB |
| `mWBM_S15_male_lifted.mat` | 87.1 MB |
| `mWBM_S23_male.mat` | 65.4 MB |
| `mWBM_S23_male_lifted.mat` | 80.9 MB |
| `mWBM_S83_male.mat` | 76.7 MB |
| `mWBM_S83_male_lifted.mat` | 94.6 MB |

Committing every plain variant actually referenced by `REGISTRY` (Harvetta + S9/S15/S23/S83) totals
**≈ 299 MB**. Committing the `_lifted` variants too would add another **≈ 352 MB** (≈ 651 MB
combined) for files that reproduce nothing currently published — no result in this repository was
ever produced from a `_lifted` file.

**Decision**: narrow the `.gitignore` rule from the current blanket
`benchmarks/model_cache/*.mat` to a `_lifted`-specific exclusion
(`benchmarks/model_cache/*_lifted.mat`), and `git add` only the five plain `.mat` files that
`REGISTRY` actually references (Harvetta's + the four from feature 006) plus the already-tracked
BiGG XMLs (unaffected). This satisfies spec FR-007 literally (every file the registry references
becomes tracked and committed) and satisfies the spec's Assumptions section literally (a `_lifted`
file "becoming trackable... does not itself make it part of the registered benchmark suite" — it
remains excluded, not merely untracked-by-omission) while keeping the repository-size growth to
what's actually needed to reproduce this project's published results (≈ 299 MB, not ≈ 651 MB).

**Alternatives considered**: (a) commit everything in the directory indiscriminately — rejected,
doubles the size increase for zero reproducibility benefit, and contradicts the spec's own
Assumptions section; (b) keep the blanket `.gitignore` rule and add narrow per-file exceptions
(`!benchmarks/model_cache/Harvetta_1_03d.mat` etc.) — functionally equivalent to the chosen
approach but more fragile (every future plain-variant model addition needs its own exception line,
whereas the chosen `*_lifted.mat` pattern needs no maintenance as new plain models are added);
rejected in favor of the self-maintaining pattern.

## R4: Repository-hosting size considerations (informational, not a gate)

None of the five files to be committed individually exceeds GitHub's 100 MB hard limit (largest is
`mWBM_S83_male.mat` at 76.7 MB), so no push will be hard-blocked. All five exceed GitHub's 50 MB
*soft* warning threshold and will each trigger a "this exceeds GitHub's recommended maximum file
size" advisory on push — expected, not an error, and not addressed by switching to Git LFS here
(the spec's own request is for these files to be ordinary, directly-cloneable repository content,
not an LFS pointer requiring a separate `git lfs pull`; LFS remains a reasonable future follow-up
if repository size becomes a practical problem, but is out of scope for what was asked).

## Constitution re-check (Phase 0)

- **Principle I (Correctness-Validated Defaults)**: not implicated — `gpugem/_defaults.py`
  untouched; this feature only runs existing, already-validated benchmark tooling against one
  additional model.
- **Principle II (Honest Status/Feasibility Reporting)**: directly reinforced — spec FR-004
  requires a Harvetta correctness-gate failure to be recorded and visibly marked, not hidden,
  matching every prior benchmark feature's convention.
- **Principle III (Test Coverage for Numerical Behavior)**: not implicated — no new
  `gpugem/solver.py`/`scaling.py`/`_defaults.py` code; the benchmark-side code touched (a
  `REGISTRY` dict literal) has no new logic branch to unit test, consistent with feature 006's
  precedent (that feature's own four-model addition needed no new tests either).
- **Principle IV (Minimal, COBRA-Compatible Surface)**: no `gpugem` public API change.
- **Principle V (Documented Known Limitations)**: this feature's own README update documents the
  git-tracking policy reversal (R3) and its size consequence explicitly, rather than leaving it an
  undocumented side effect of the commit history.

No violations. No Complexity Tracking entries required.
