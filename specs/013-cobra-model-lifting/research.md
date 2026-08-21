# Phase 0 Research: Opt-In Model Lifting for Badly-Scaled LPs

Every finding below is grounded in direct inspection of the actual reference source
(`/home/farid/projects/cobratoolbox/src/base/solvers/rescale/reformulate.m`, re-read in full for
this feature rather than relied on from memory) and of this project's own current code
(`gpugem/scaling.py`, `gpugem/solver.py`, `gpugem/loaders.py`, `gpugem/result.py`), plus a direct,
empirical check of the actual model (S85) this feature will be validated against.

## R1. `reformulate.m`'s mass-balance (`S`-block) algorithm, translated precisely

**Decision**: The Python port must replicate this exact structure, not a simplified approximation:

1. Only rows that are homogeneous equalities (`csense=='E' & b==0`) are candidates — exactly
   gpuGEM's own `S`/`b` mass-balance block (FBA mass balance is always homogeneous by
   construction, so this condition is expected to hold trivially for every row of `S`).
2. Within a candidate row, **every** large entry (`|value| > BIG`) shares **one** auxiliary-variable
   chain, not an independent chain per entry. The chain's step size `stp` is computed once per row
   as `mode(nthroot(lrgnums, dum+1))` where `lrgnums` are that row's large entries and `dum` is a
   per-entry level count (`dum_i = max(floor(log(|value_i|)/log(BIG)), 1)`).
3. **Critical, easy-to-mistranslate detail**: MATLAB's `mode()` on a vector of (in practice)
   all-distinct floating-point values returns the *minimum* value, not an average or the first
   element — MATLAB's documented tie-breaking rule is "smallest value wins," and an all-unique
   vector has every element tied at frequency 1. A naive port using, e.g., Python's
   `statistics.mode()` (which returns the *first* most-common value, arbitrary for all-unique
   float data) would silently diverge from `reformulate.m`'s actual behavior. **The correct
   translation is `stp = min(value_i ** (1/(dum_i+1)) for i in row)`.**
4. The row's `maxdum = max(dum_i)` auxiliary variables and rows form a bidiagonal chain
   (`aux_k - stp * aux_{k+1} = 0` for consecutive levels), connected to the original row via a
   single `-stp` entry into the first chain link.
5. Each entry with its own `dum_i` level "taps into" the chain at that level: the auxiliary row at
   level `dum_i` gets a direct entry back to the *original* column `j`, valued
   `original_value_j / stp**dum_i` — entries needing fewer levels tap in earlier, sharing the same
   physical chain as entries needing more levels in the same row. This is what makes the transform
   produce far fewer auxiliary variables than one independent chain per large entry would (relevant
   directly to FR-002/SC-002's "coefficients within threshold" requirement without ballooning
   problem size unnecessarily).
6. The original large entries are then deleted from the row (replaced by the single `-stp` link).

**Rationale**: This is the actual, specific algorithm named in the spec's own reference
requirement (FR-002/FR-008) — approximating it with a simpler per-entry decomposition (see R3)
would not satisfy "faithful correspondence to `reformulate.m`."

**Alternatives considered**: A simplified per-entry-independent chain (like `gpugem/scaling.py`
already implements, see R3) — rejected because it is a materially different algorithm, not a
translation of this one.

## R2. `reformulate.m`'s coupling-constraint (`C`-block) algorithm

**Decision**: Simpler than R1 — no per-row sharing needed because each targeted row has, by its
own selection criterion, exactly one large entry to decompose:

1. Candidate rows: inequality (`csense` is `L` or `G`), homogeneous (`b==0`), with **exactly two**
   nonzero entries of **opposite sign** — the specific shape of a pairwise flux-coupling
   constraint (`v_i - k*v_j <= 0`-style). Confirmed empirically relevant to this project's own
   validation model: of S85's 1,258,572 coupling rows, 1,255,838 have exactly two nonzeros, of
   which 136,550 match the full pattern (opposite sign + homogeneous), of which 68,259 have a
   coefficient exceeding `BIG=1000` and would actually be lifted.
2. For each such row, `dum = max(floor(log(qty)/log(BIG)), 1)` (`qty` = the row's one large
   entry's magnitude) and `stp = qty ** (1/(dum+1))` (a plain root here — no `mode()`/sharing
   needed since there is exactly one large value per targeted row).
3. A `dum`-length chain of new coupling rows and auxiliary variables is appended, sign-consistent
   with the original entry's sign, and the original large entry is zeroed.
4. Non-matching rows (wrong nonzero count, same sign, or non-homogeneous) pass through completely
   unchanged — this is not a fallback/error path, it is `reformulate.m`'s own designed behavior
   (spec Edge Cases).

**Rationale**: Directly required by spec FR-003; the pattern-matching precondition is not optional
scope-narrowing on this project's part — it is what the reference algorithm itself does.

## R3. `gpugem/scaling.py` is a different, pre-existing algorithm — do not reuse or extend it

**Decision**: Build a new module (`gpugem/lifting.py`) rather than extending
`gpugem/scaling.py`'s existing `decompose_stoichiometry`/`scale_model`/`remap_fluxes`, even though
the two are superficially similar (both split badly-scaled coefficients into auxiliary-variable
chains and map results back via prefix truncation).

**Rationale — the two algorithms materially diverge**, confirmed by direct code reading:

| | `reformulate.m` (this feature's target) | `gpugem/scaling.py` (existing) |
|---|---|---|
| Which coefficients | Only *large* (`> BIG`) | Both large and small (`< min_abs`) |
| Chain construction | One chain **shared per row** across all its large entries, step size from `mode()`/min of per-entry roots | One **independent chain per nonzero entry** |
| Coupling (`C`) block | Explicitly lifted (its own algorithm, R2) | Not lifted at all — only zero-padded for the new auxiliary columns from the `S`-block lift |
| Auxiliary variable bounds | Fully unbounded (`-Inf`/`Inf`) | Bounded at `±aux_bound` (model's largest finite bound, or 1000 default) |
| Integration | New: opt-in flag directly on `gpugem.solve()` (R4) | Existing: a manual two-step utility the caller invokes themselves — never wired into `solve()` |

Reusing or silently extending `scaling.py` to also match `reformulate.m` would either break its
existing (tested, committed) behavior for its own existing callers, or produce a module doing two
unrelated things behind one name — both worse than a clearly-separate, clearly-named module.
`gpugem/scaling.py` is left completely untouched by this feature.

**Alternatives considered**: Extending `scale_model` with a `mode="reformulate"` switch — rejected
as needless complexity (Constitution: no speculative generality) for two genuinely different
algorithms with different callers' needs; a plain new module is simpler and clearer.

## R4. Integration point: `lift`/`lift_big` become real parameters on `gpugem.solve()`, and every other entry point inherits them for free

**Decision**: Add `lift: bool = False, lift_big: float = 1000.0` as explicit, keyword-only
parameters on `gpugem.solve()`'s signature (consumed before the `**cuopt_kwargs` merge into
`SolverSettings`, so they are never mistaken for a cuOpt solver parameter and never rejected by
`settings.set_parameter`).

**Rationale**: Confirmed by direct code reading that this is the *only* integration point needed —
`gpugem`'s other two entry points already transparently forward arbitrary keyword arguments down
to `solve()`:
- `solve_cobra(model, **cuopt_kwargs)` → `_solver.solve(**arrays, **cuopt_kwargs)`: passing
  `solve_cobra(model, lift=True)` already works today with zero changes to `solve_cobra.py`,
  because `lift=True` lands in its `**cuopt_kwargs` and is forwarded straight through.
- `FBASolver.__init__(..., **cuopt_kwargs)` stores `self._defaults = cuopt_kwargs`, and
  `.solve()` merges `self._defaults` with any per-call override before calling `solve()` — so
  `FBASolver(S, b, lb, ub, c, lift=True)` also already works with zero changes.

This means the spec's "gpuGEM's LP-solving entry points MUST accept..." (FR-001, plural) is
satisfied by touching exactly one function's signature, not three — a direct, evidence-based
minimality win (Constitution Principle IV).

**Alternatives considered**: A separate `gpugem.lift_and_solve(...)` wrapper function —
rejected: would duplicate `solve()`'s existing DataModel/SolverSettings/Solve wiring for no
benefit, and would not automatically extend to `solve_cobra`/`FBASolver` the way an in-`solve()`
parameter does.

## R5. Map-back is a literal prefix slice, not a stored inverse transform

**Decision**: Because `reformulate.m` never reorders, rescales, or removes original variables —
only appends new ones after them — mapping a lifted solution back to the original model is
`fluxes_lifted[:n_original_vars]`. No inverse arithmetic is needed (a materially simpler property
than `specs/012-cuopt-native-tuning/`'s external-scaling preprocessing candidate, whose reported
tolerance failed to survive its inverse transform — see that feature's README write-up). This
matches `gpugem/scaling.py`'s own `remap_fluxes` precedent (same prefix-slice principle, confirmed
directly in its source), even though the two modules' forward transforms differ (R3).

**Rationale**: Directly satisfies spec FR-005 ("direct, lossless extraction... never an
approximation or a rescaling operation") — and explains *why* that requirement is achievable at
all for this specific algorithm family, not just asserted.

## R6. Feasibility/residual reporting under `lift=True` must be computed against the *original*, not the lifted, system

**Decision**: When `lift=True`, after solving the lifted `DataModel` and truncating `fluxes` to
the original variable count, `gpugem.solve()` MUST recompute `FBAResult.feasibility` (stoichiometric
residual, etc.) against the **original** `S`/`b`/`C`/`d_lb`/`d_ub` — not the lifted, larger system
cuOpt actually solved internally.

**Rationale**: Two independent reasons converge on this:
1. `FBAResult.fluxes`'s existing docstring already commits to "Flux vector in the *original*
   variable space" — a caller's feasibility diagnostics should be about the same space their
   flux vector is in, not a different (lifted) one they never see.
2. This is also the cheapest, always-on version of spec FR-006's correctness check: recomputing
   the residual against the *original* system on every lifted solve means a translation bug in the
   lifting module would show up immediately as a bad residual on ordinary use, not only inside a
   dedicated benchmark script — a stronger default than only checking correctness in a separate
   test suite.

**Alternatives considered**: Reporting the lifted system's own internal residual (what cuOpt
itself computed) — rejected: it answers "did the lifted LP solve correctly" but not "does the
original model's user get a trustworthy answer," which is the actual question `FBAResult` exists
to answer for every other gpuGEM caller.

## R7. Validation methodology without a local MATLAB/Octave installation

**Decision**: Three independent layers, matching spec FR-008/SC-004's "traceable, not just
black-box" requirement:
1. **Line-level correspondence**: the Python port's mass-balance and coupling functions carry
   comments referencing the specific `reformulate.m` line ranges they translate (already mapped
   out in R1/R2 above), so a reviewer can check the translation directly against the MATLAB
   source without running it.
2. **Hand-verifiable linear-algebra check**: for a small constructed example, assert
   `S_lifted @ x_lifted` reproduces `S_original @ x_original` on the original rows and exactly
   zero on every new auxiliary row, for an `x_lifted` built by hand from a chosen `x_original` and
   the transform's own recorded chain metadata — the same style of test
   `tests/test_scaling.py::test_decompose_stoichiometry_preserves_original_rows` already
   establishes as this project's precedent for validating this class of transform, adapted to
   `reformulate.m`'s actual (row-shared-chain) construction rather than `scaling.py`'s.
3. **Solve-and-compare** (this project's standard correctness gate throughout every prior
   benchmark feature): solving a model lifted-and-mapped-back must match solving it unlifted,
   within the same residual/objective tolerances already used everywhere else in this project.

**Rationale**: Matches the spec's own Assumption (recorded there for exactly this reason) and
this project's established, consistent way of proving correctness without needing a reference
implementation to diff against at runtime.

## R8. Validation models: e_coli_core (small, no-op case) and S85 (large, both blocks exercised)

**Decision**: `e_coli_core` validates the "lifting is a safe no-op on a well-conditioned model"
edge case (spec Edge Cases; no coefficients exceed `BIG` there). `S85` validates both the
mass-balance and coupling-constraint lifting paths on real, badly-scaled data — confirmed directly
(not assumed) by the row-count check in this research: S85's `S` block spans `[1e-6, 2e5]`
(established in `specs/012-cuopt-native-tuning/research.md` R5) and its `C` block has 68,259 rows
that will actually be lifted at the default `BIG=1000` (checked directly above), so this one model
exercises everything FR-002/FR-003 require without needing to hunt for a second large model.

**Rationale**: Satisfies spec FR-010 (small + large model coverage) with the minimum number of
models needed to genuinely exercise every code path, reusing a model this project's benchmark
suite (and the immediately preceding feature) already has deep, validated familiarity with.

## R9. `BIG` default

**Decision**: Default `lift_big=1000.0` — the lower/more conservative end of `reformulate.m`'s own
documented recommended range ("BIG should be set between 1000 and 10000 on double precision
machines"), confirmed above to already trigger meaningful lifting on both blocks of S85 at this
setting (no need to pick a more aggressive value to get real test coverage).

**Alternatives considered**: `10000` (the upper end of the documented range) — not rejected
outright, but `1000` is chosen as the more conservative default since it lifts *more* rows (safer
default behavior — closer to reformulate.m's own conditioning goal), while `lift_big` remains a
caller-configurable parameter for anyone who wants to match the less aggressive end of the range.
