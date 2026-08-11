# Feature Specification: Colorblind-Friendly, Clearly-Layered Violation Distribution Figures

**Feature Branch**: `009-distribution-figure-clarity`

**Created**: 2026-08-05

**Status**: Draft

**Input**: User description: "I want the distribution figures under benchmarks/figures to be
colorblind friendly and also increasing the opacity while putting the smaller figures on the
forward layer would increase the clarity of the figure. Therefore in the bottom we will have the
bigger figures and on the top the smaller ones. This way the colors would look better"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tell every model's band apart by color alone, including with color vision deficiency (Priority: P1)

A reader looking at either violation-distribution figure (equations or coupling constraints) wants
to visually distinguish every model's overlaid band by its color, including a reader with a common
form of color vision deficiency (CVD) — not just by reading the direct text labels.

**Why this priority**: This is the entire point of the request — a figure whose color-coding isn't
actually distinguishable, for a CVD reader or anyone, fails at the one job color is doing in this
chart (showing model identity/size ordering at a glance).

**Independent Test**: Can be fully tested by inspecting every pair of adjacent-size-rank models'
colors in both figures and confirming they remain visually distinct under simulated common forms
of color vision deficiency, not only in unimpaired vision.

**Acceptance Scenarios**:

1. **Given** both violation-distribution figures as currently generated, **when** the color
   assigned to each model is checked against every other model adjacent to it in size ordering,
   **then** every adjacent pair remains distinguishable under common color vision deficiencies, not
   just under typical color vision.
2. **Given** a figure with the corrected color treatment, **when** it is viewed by someone with
   red-green color vision deficiency (the most common form), **then** they can still tell which
   band belongs to a smaller model versus a larger one without relying on the text labels.

---

### User Story 2 - See every model's band, including the smallest ones, without it being hidden behind a larger one (Priority: P1)

A reader wants every model's band to be visible where it overlaps another model's band, including
the smallest, narrowest, most easily-hidden ones — not obscured by a larger model's band that
happens to be drawn on top of it.

**Why this priority**: Equal priority to User Story 1 — this is the second, complementary half of
the same underlying problem: a smaller model's band being visually swallowed by a larger, more
prominent one defeats the same "identify every model by color" goal, regardless of how good the
underlying palette is.

**Independent Test**: Can be fully tested by inspecting a region of either figure where a small
model's band and a large model's band overlap, and confirming the smaller model's band and color
remain visible in that region rather than being fully covered.

**Acceptance Scenarios**:

1. **Given** both figures, **when** a smaller model's band overlaps a larger model's band,
   **then** the smaller model's band is drawn so it remains visible in the overlapping region
   (rendered above the larger model's band, not beneath it).
2. **Given** the improved layering, **when** the fill opacity is increased for a more vivid,
   easier-to-read appearance, **then** no model's band — including the largest, bottom-most ones —
   becomes so faint or fully covered that it stops being individually identifiable.

---

### Edge Cases

- What happens to the two models with negligible or zero violations, whose bands are already
  effectively invisible (near-zero width) regardless of layering? Layering order doesn't change
  anything visible for them; their existing direct-label placement (already off to the side, not
  reliant on fill visibility) is unaffected by this feature.
- What happens where three or more models' bands overlap in the same region? The layering rule
  (smaller models drawn above larger ones) applies consistently across all of them, not just to
  pairs — the smallest model present in that region is always the topmost, most visible one there.
- What happens to the two figures' consistency with each other (the equations figure covers ten
  models, the coupling-constraint figure covers eight)? Each figure's color assignment and layering
  are evaluated within that figure's own set of models, consistent with how model size ordering
  already works independently per figure.
- What happens to the direct text labels and their white halo, already used for legibility? They
  are unaffected — this feature changes fill color and layering, not label placement or styling.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST assign each model's band a color such that every pair of
  adjacent-size-rank models remains visually distinguishable under common forms of color vision
  deficiency, not only under typical color vision.
- **FR-002**: The system MUST draw smaller models' bands above (visually in front of) larger
  models' bands wherever they overlap, reversing the current largest-in-front layering.
- **FR-003**: The system MUST increase the bands' fill opacity from its current level to produce a
  more vivid, easier-to-read appearance.
- **FR-004**: Increasing opacity (FR-003) MUST NOT cause any model's band — including the largest,
  now-bottom-most ones — to become fully hidden or indistinguishable from another model's band.
- **FR-005**: This change MUST apply to both violation-distribution figures (mass-balance
  equations and coupling constraints) consistently — the same color and layering treatment, each
  evaluated within its own figure's set of models.
- **FR-006**: Both figures MUST remain regenerable from committed result data alone, without
  requiring cuOpt or Gurobi to be installed, consistent with this project's existing figure
  reproducibility convention.
- **FR-007**: This work MUST NOT modify any of this project's shipped default solver settings or
  any previously-recorded benchmark result — it is a rendering-only change.

### Key Entities *(include if feature involves data)*

- **ModelBandStyle**: per model, per figure — the color and z-layer (front-to-back drawing order)
  assigned to that model's overlaid distribution band, derived from its size rank within that
  figure's set of models.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every pair of adjacent-size-rank models in both figures has colors that remain
  distinguishable when simulated under common color vision deficiencies, verified by a repeatable,
  automatable check rather than eyeballing.
- **SC-002**: In every region where a smaller model's band overlaps a larger model's band, the
  smaller model's band and color are visibly identifiable, not covered.
- **SC-003**: A reader can identify which band belongs to which model primarily from its color and
  position, with the direct text labels as confirmation rather than the only usable signal.
- **SC-004**: Both figures remain regenerable from committed result data alone.
- **SC-005**: No previously-recorded benchmark result or shipped default solver setting changes as
  a result of this work.

## Assumptions

- "The distribution figures under benchmarks/figures" refers to the two population-pyramid-style
  violation-distribution figures introduced in a prior feature
  (`violation_distribution_equations.png` and `violation_distribution_constraints.png`) — not the
  bar-chart comparison figures in the same directory, which already use an unrelated, fixed
  categorical color scheme (by solver configuration, not by model) that this request doesn't
  describe or implicate.
- "Putting the smaller figures on the forward layer" and "bigger figures" at "the bottom" refers to
  each model's *band* within a single distribution figure (front-to-back drawing/z-order), not to
  separate figure files or their layout on a page — there is one figure per comparison, containing
  one overlaid band per model, and this request is about the stacking order of those bands.
- The current color treatment already uses a single-hue-family ordered ramp (light-to-dark by
  model size) rather than arbitrary, unordered hues; "colorblind friendly" is interpreted as
  ensuring that ramp's actual sampled colors keep sufficient perceptual separation between
  neighboring models under color vision deficiency simulation, adjusting the specific colors or
  sampling if a check reveals they don't — not necessarily replacing the overall light-to-dark,
  size-ordered visual language, which independently already carries meaning (smaller vs. larger)
  beyond raw hue.
- No specific opacity value is mandated by the request beyond "increasing" it; the exact value is
  chosen so the smallest model's band stays clearly visible even after both changes are applied
  (per FR-004), verified visually rather than fixed to an arbitrary number in advance.
- This feature is rendering-only: no change to what data is captured, computed, or persisted by any
  benchmark script — only how already-committed violation-histogram data is drawn.
