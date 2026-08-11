# Phase 0 Research: Colorblind-Friendly, Clearly-Layered Violation Distribution Figures

## R1: The current palette (viridis, sampled by rank) fails this project's own ordinal-ramp validation — concretely, not just by inspection

Consulted the dataviz skill and ran its computable ordinal-ramp validator (`validate_palette.py
--ordinal`, a Python port of the skill's `validate_palette.js`, both bundled with the skill) against
the exact 10 hex colors `make_violation_distribution_figures.py` currently generates for the
equations figure (`viridis`, sampled at `frac = 0.12 + 0.80*(rank/(n-1))`):

```
#472a7a,#404688,#355f8d,#2b748e,#238a8d,#1fa088,#31b57b,#5ac864,#8ed645,#cae11f
```

Result: **FAILED, 3 of 4 checks**:
- Adjacent ΔL: every adjacent pair is ~0.05 apart, below the ordinal floor of 0.06.
- Light-end contrast: the lightest step (`#cae11f`, yellow — the *largest* model) is 1.43:1
  against the white figure background, below the 2.0:1 floor a mark needs to read at all.
- Single hue: viridis spans purple→blue→teal→green→yellow, a 179° hue spread — the skill's
  ordinal category specifically wants a **single-hue** ramp (light→dark within one hue family);
  a multi-hue ramp is categorized differently on purpose, because sampling it densely to encode
  many discrete ranks produces exactly the too-close/too-flat problems measured above.

This is the concrete evidence behind spec FR-001: viridis is well known as a *perceptually
uniform, CVD-friendly continuous colormap for magnitude* (e.g. a heatmap), but that is a different
job than a *discrete, size-ranked* per-model color assignment — dense rank-sampling of a
continuous multi-hue map doesn't inherit that same property once collapsed into ~8-10 discrete
category swatches, exactly as its ordinal-check failure shows.

## R2: A validated single-hue replacement ramp, built from the skill's own reference blue hue, parametrized by model count

The skill's reference sequential/ordinal hue is blue (`references/palette.md`), with named steps
250 (`#86b6ef`, lightest step clearing the 2:1 ordinal contrast floor on light backgrounds) through
700 (`#0d366b`, darkest). Directly using all 10 named steps still fails the ΔL check (~0.047 gaps,
because those named steps are spaced for a *continuous* sequential ramp, not discrete ordinal
categories): `#86b6ef,#6da7ec,#5598e7,#3987e5,#2a78d6,#256abf,#1c5cab,#184f95,#104281,#0d366b` →
FAILED (adjacent ΔL).

**Decision**: construct the ramp directly in OKLCH space rather than sampling the named steps.
Fix the light anchor at step 250's OKLCH L (already exactly clears the 2:1 contrast floor), take
the hue/chroma trajectory from step 250 → step 700 as the single-hue reference, and choose the
dark anchor as `light_L - (N-1) * 0.063` for `N` models (`0.063` > the 0.06 floor, a small safety
margin against floating-point/rounding). This produces a ramp that mathematically guarantees
monotone lightness and adjacent ΔL ≥ 0.06 by construction, for whatever `N` a figure has, rather
than hardcoding one fixed-size palette. Verified against the two concrete cases this project needs:

- **N=10** (equations figure): `#86b6ef,#73a2da,#618ec6,#4e7bb2,#3d689f,#2b568b,#1a4478,#073266,
  #002154,#000f42` → **all 4 ordinal checks PASS** (adjacent ΔL, light-end contrast 2.06:1, hue
  spread 10°, monotone).
- **N=8** (constraints figure): `#86b6ef,#73a2db,#618ec6,#4f7bb3,#3d689f,#2c568c,#1b4379,#083266`
  → **all 4 ordinal checks PASS** (hue spread 4°, more L-budget per step since fewer models).

**Alternatives considered**: (a) keep viridis but only sample a narrower, safer sub-range —
rejected, viridis's multi-hue nature means no sub-range passes the single-hue check, only ΔL could
be patched this way; (b) hand-pick 8-10 distinct hex values without a formula — rejected, not
reproducible/self-verifying if a future feature changes model count, and reintroduces "eyeballing"
exactly what spec SC-001 says to avoid; (c) use the skill's 8-hue *categorical* palette instead of
an ordinal ramp — rejected, model size is a genuine ordinal ranking (spec's own existing framing,
carried over from feature 007) where swapping order changes meaning, which is precisely the
skill's definition of when to use an ordinal ramp, not categorical hues.

## R3: Z-order reversal (smaller models drawn last/on top) and an opacity increase this makes safe

Current code (`_pyramid_figure`, both fill calls): `zorder=rank` where `rank` ascends by solved
`n_cols` (rank 0 = smallest model). This draws the **largest** model's band last (frontmost),
exactly backwards from spec FR-002 — and is the direct cause of the alpha=0.42 compromise already
in the code (comment: "Kept semi-transparent... an opaque top layer would fully hide a smaller
model's band"). That comment's problem is solved by fixing the draw order instead of only lowering
opacity.

**Decision**: `zorder = n - 1 - rank` — the smallest model (rank 0) gets the highest zorder (drawn
last, frontmost); the largest model (rank n-1) gets zorder 0 (drawn first, backmost). Once smaller
bands can no longer be covered by larger ones, opacity can rise substantially without any band
becoming hidden (spec FR-004) — raising it from 0.42 to approximately 0.7 is proposed as a starting
point (a visibly more vivid, "solid" appearance while still leaving a translucent cue where two
bands genuinely overlap), with the exact value confirmed by rendering both figures and visually
checking every model's band remains individually identifiable, per the spec's own Assumptions
(no number mandated in advance) — matching this project's established visual-QA-driven tuning
precedent for these exact figures (features 007/008 both tuned label placement this way).

## R4: Implementation surface — one new pure function, reused by both figures, with its own test

The ramp-construction math (R2) is implemented as a new pure function (e.g.
`_ordinal_ramp(n) -> list[str]`) in `benchmarks/make_violation_distribution_figures.py`, replacing
`CMAP = plt.get_cmap("viridis")` / `CMAP(frac)` with a call to this function once per figure (since
each figure has its own model count `n`, consistent with the spec's Assumptions: "each figure's
color assignment... evaluated within that figure's own set of models"). The OKLCH conversion math
is small (~15 lines, standard published constants) and self-contained — no new dependency, and no
runtime dependency on the dataviz skill's script path (which is outside this repository and not
guaranteed to exist in every environment). A unit test reimplements just the check this feature
actually relies on (adjacent-step OKLCH-L gap ≥ 0.06, monotone, single-hue) directly against the
generated ramp for representative `n` values (8, 9, 10), so a future model-count change that broke
this property would be caught locally rather than only by manually re-running the external
validator — consistent with the constitution's Principle III (test coverage for computed numerical
behavior) applied to this feature's own new logic.

## Constitution re-check (Phase 0)

- **Principle I (Correctness-Validated Defaults)**: not implicated — `gpugem/_defaults.py`
  untouched; this is a rendering-only change to already-non-default comparison figures.
- **Principle II (Honest Status/Feasibility Reporting)**: not implicated — no change to what's
  computed or reported, only how already-correct data is drawn.
- **Principle III (Test Coverage for Numerical Behavior)**: directly addressed — the new ramp
  function gets its own test (R4), reimplementing the relevant computable check rather than relying
  on eyeballing or an external, non-committed script.
- **Principle IV (Minimal, COBRA-Compatible Surface)**: no `gpugem` public API change.
- **Principle V (Documented Known Limitations)**: N/A — no new limitation introduced.

No violations. No Complexity Tracking entries required.
