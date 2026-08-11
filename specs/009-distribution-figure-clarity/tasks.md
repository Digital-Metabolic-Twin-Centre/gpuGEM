---

description: "Task list for Colorblind-Friendly, Clearly-Layered Violation Distribution Figures"

---

# Tasks: Colorblind-Friendly, Clearly-Layered Violation Distribution Figures

**Input**: Design documents from `/specs/009-distribution-figure-clarity/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all present)

**Tests**: Included — plan.md's Technical Context commits to reimplementing the relevant
computable color-property checks as a local unit test (monotone OKLCH lightness, adjacent ΔL,
light-end contrast, single hue), per Constitution Principle III applied to this feature's own new
logic.

**Organization**: Tasks are grouped by user story (P1/P1 from spec.md) so each can be implemented
and independently tested on its own, even though both land in the same function.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Include exact file paths in descriptions

## Path Conventions

Single project — one file modified
(`benchmarks/make_violation_distribution_figures.py`), one test file extended. No `gpugem/`
changes (see plan.md Project Structure).

---

## Phase 1: Setup

**Purpose**: Confirm the prerequisite state this feature builds on.

- [X] T001 Confirm both `benchmarks/results/residual_tradeoff/comparison.csv` and every
  `benchmarks/results/residual_tradeoff/<model>.json` referenced by
  `make_violation_distribution_figures.py::_load_entries` are present and up to date (feature 008
  already regenerated these with 10/8 models) — nothing to fix if so, this is a pre-flight check
  before touching rendering code

**Checkpoint**: The figures can be regenerated end-to-end before any code change, giving a known
"before" baseline to compare against.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The single-hue OKLCH ramp function is the shared infrastructure both user stories'
final regenerated figures depend on — User Story 1 wires it in for color, and User Story 2's
z-order/opacity change is verified against the same regenerated output.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 In `benchmarks/make_violation_distribution_figures.py`, add `_hex_to_oklab(hex)` and
  `_oklab_to_hex(L, a, b)` helper functions (standard published OKLab<->linear-sRGB constants, per
  `contracts/ordinal-ramp-and-layering.md` and research R2) — pure functions, no I/O
- [X] T003 In `benchmarks/make_violation_distribution_figures.py`, add `_ordinal_ramp(n)` using
  `LIGHT_HEX = "#86b6ef"`, `DARK_HEX = "#0d366b"`, `MIN_DL = 0.063` per the contract: fix the light
  anchor's OKLCH L, compute `dark_L = L0 - (n-1)*MIN_DL`, linearly interpolate L/a/b across `n`
  steps, convert each back to hex (depends on T002)
- [X] T004 [P] In `tests/test_violation_histogram.py` (or a new `tests/test_ordinal_ramp.py`),
  add tests for `_ordinal_ramp`: for `n` in `{8, 9, 10}`, assert OKLCH lightness is strictly
  monotone decreasing, every adjacent pair's `|ΔL| >= 0.06`, the lightest (`n=...[0]`) hex clears
  2.0:1 WCAG contrast against `#fcfcfb`, and the OKLab hue spread across all `n` colors is `<= 40°`
  — reimplementing just these checks locally (not depending on the dataviz skill's external
  script), per research R4 (depends on T002, T003)
- [X] T005 Run the new tests (`pytest tests/test_violation_histogram.py -k ramp` or equivalent) and
  confirm they pass for `n=8`, `n=9`, and `n=10` before wiring the ramp into any figure (depends on
  T004)

**Checkpoint**: `_ordinal_ramp` is proven correct in isolation — both user stories can now safely
build on it.

---

## Phase 3: User Story 1 - Tell every model's band apart by color alone, including with color vision deficiency (Priority: P1) 🎯 MVP

**Goal**: Both violation-distribution figures use the validated single-hue ramp instead of viridis,
so every adjacent-rank pair of models is distinguishable under common color vision deficiencies.

**Independent Test**: Regenerate both figures and confirm the colors used are `_ordinal_ramp`'s
output (not viridis), matching the color assigned to each model's rank within that figure's own
model count.

### Implementation for User Story 1

- [X] T006 [US1] In `benchmarks/make_violation_distribution_figures.py::_pyramid_figure`, replace
  `CMAP = plt.get_cmap("viridis")` / `color = CMAP(frac)` with `colors = _ordinal_ramp(n)` (computed
  once per figure, using that figure's own `n`) and `color = colors[rank]`, per
  `contracts/ordinal-ramp-and-layering.md` (depends on T005)
- [X] T007 [US1] Run `python -m benchmarks.make_violation_distribution_figures` and visually
  confirm both regenerated PNGs show a single blue hue family, light (smallest model) to dark
  (largest), with every adjacent pair visibly distinct — quickstart.md step 2 (depends on T006)

**Checkpoint**: User Story 1 is fully functional and independently testable — the color assignment
itself is now validated-accessible, independent of the layering change in User Story 2.

---

## Phase 4: User Story 2 - See every model's band, including the smallest ones, without it being hidden behind a larger one (Priority: P1)

**Goal**: Smaller models' bands draw above larger ones, and fill opacity is raised for a more vivid
figure, without any band becoming hidden.

**Independent Test**: Inspect a region of either figure where a small and a large model's bands
overlap and confirm the smaller model's band and color remain visible on top.

### Implementation for User Story 2

- [X] T008 [US2] In `benchmarks/make_violation_distribution_figures.py::_pyramid_figure`, change
  the fill/line `zorder` from `rank` to `n - 1 - rank` (smallest model highest zorder, frontmost)
  for both the shortfall and excess `fill_betweenx`/`plot` calls, per
  `contracts/ordinal-ramp-and-layering.md` (depends on T006, same function)
- [X] T009 [US2] Introduce a `BAND_ALPHA` constant (starting at `~0.7` per research R3) replacing
  the current `alpha=0.42` literal on both fill calls (depends on T008)
- [X] T010 [US2] Run `python -m benchmarks.make_violation_distribution_figures` and visually
  confirm: in every region where a smaller model's band overlaps a larger one, the smaller model's
  band and outline remain visible on top; no band (including the now-backmost largest models) is
  fully hidden or reads as blank at the new opacity — quickstart.md step 2 (depends on T009). If
  any band is hidden or the figure looks off, adjust `BAND_ALPHA` and re-render until it doesn't
  (spec FR-004; no fixed target value beyond "no band hidden")

**Checkpoint**: Both user stories are independently functional — accessible colors (US1) and
correct, hidden-nothing layering at higher opacity (US2) together produce the final figures.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Regression check and final confirmation that nothing outside scope changed.

- [X] T011 [P] Run the full `pytest` suite (`python -m pytest tests/ -q`) and confirm no
  regressions — this feature's changes are additive (new functions, changed constants) and
  shouldn't affect any other test
- [X] T012 Run quickstart.md end-to-end (validation items 1-3) and confirm `git diff --stat
  gpugem/ benchmarks/results/` produces no output — this is a rendering-only change (spec SC-005;
  depends on T007, T010, T011)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS both user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion
- **User Story 2 (Phase 4)**: Depends on User Story 1 (T006) — both change the same
  `_pyramid_figure` function; z-order/opacity changes are sequenced after the color-source change
  to avoid overlapping edits, though User Story 2's own *logic* (z-order formula, alpha constant)
  doesn't depend on which colors are used
- **Polish (Phase 5)**: Depends on both user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Independently testable once Foundational lands — color correctness can be
  verified before any layering change
- **User Story 2 (P1)**: Independently testable once its own tasks land — layering/opacity
  correctness can be verified as its own concern, even though it's implemented after US1 in the
  same file for edit-locality reasons

### Within Each User Story

- Ramp helper functions (T002) before the ramp itself (T003) before its tests (T004) before
  running them (T005) — Foundational
- Wire-in (T006) before visual validation (T007) — US1
- Z-order change (T008) before opacity change (T009) before visual validation (T010) — US2

### Parallel Opportunities

- T004 (new tests) can be written in parallel with finishing T003 once T002's helpers exist, then
  run together at T005
- T011 (full regression suite) can run in parallel with T012's final manual quickstart pass

---

## Parallel Example: Foundational phase

```bash
# After T002/T003 (OKLCH helpers + ramp function) land, run together:
Task: "Write _ordinal_ramp property tests"   # T004
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks both stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: regenerate both figures with only the color change applied (z-order/alpha
   still as-is) — confirms the accessible palette alone, before touching layering
5. Phase 4 adds the layering/opacity improvement on top; Phase 5 is docs-free polish (regression
   check + final confirmation)

### Incremental Delivery

1. Setup + Foundational → `_ordinal_ramp` proven correct in isolation
2. User Story 1 → figures use the validated, colorblind-safe palette
3. User Story 2 → figures also have correct layering and higher opacity, with nothing hidden
4. Polish → regression check, final confirmation that nothing outside scope changed

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- No `gpugem/` changes anywhere in this feature — every task touches only
  `benchmarks/make_violation_distribution_figures.py` or `tests/`
- No new result data or committed JSON changes — purely rendering
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently
