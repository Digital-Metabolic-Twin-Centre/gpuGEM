# Feature Specification: cuOpt-Native Settings Tuning for Large Microbiome Models

**Feature Branch**: `012-cuopt-native-tuning`

**Created**: 2026-08-20

**Status**: Draft

**Input**: User description: "loop over all the cuOpt's settings, read online tutorials and documentations, upgrade cuOpt if needed and see if you can find an optimal setting that works on the big models like S85. no need to benchmark it on all the models, s85 is sufficient. This new setting should not rely on any other proprietry software or solver but it may benefit from open source tools (But it is not recommended ideally we want a cuOpt native setting that works best for big microbiome models). Alternatively we may consider preprocessing the models in a way that we get the original result in the end not simplified not solving smaller version of the model. Just preprocessing so that cuOpt can handle them better. But again no preprocessing is encouraged. Use scientific approach, and consider all the aspects.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Systematic cuOpt-native settings sweep on S85 (Priority: P1)

A researcher who already knows (from `specs/004-s85-solver-mode-experiment/`) that three
specific settings changes didn't close cuOpt's ~9-10x gap against Gurobi on the S85 microbiome
model wants a genuinely systematic answer, not another round of hand-picked guesses: sweep across
the full space of cuOpt's documented, LP-relevant solver parameters (grounded in current official
documentation, not just the ones already tried), and find out whether *any* combination is both
faster than the currently shipped large-model default and still verified-correct.

**Why this priority**: This is the core research question. Without a systematic sweep grounded in
current documentation, the project cannot honestly claim it has exhausted the cuOpt-native option
before reaching for anything else.

**Independent Test**: Can be fully tested by running the sweep against S85's already-published
objective and confirming that every candidate configuration produces a recorded result (wall time,
iteration count, solver status, verified-correct or not), including the unchanged baseline for
comparison.

**Acceptance Scenarios**:

1. **Given** the current shipped large-model default settings as a baseline, **when** the sweep
   runs every candidate configuration drawn from cuOpt's documented parameter space, **then** each
   candidate's wall time, iteration count, solver status, and correctness (residual + objective
   agreement against S85's already-established Gurobi ground truth) is recorded.
2. **Given** a candidate configuration that cuOpt rejects (unsupported parameter, invalid
   combination) or that hangs/crashes, **when** the sweep encounters it, **then** that outcome is
   recorded explicitly (not silently skipped and not allowed to stop the rest of the sweep).
3. **Given** a candidate that finishes faster than the baseline but fails the correctness check,
   **when** results are reported, **then** it is never reported as a win — speed is never traded
   for a wrong answer.
4. **Given** the completed sweep, **when** the researcher reviews it, **then** there is a single
   ranked view identifying the fastest verified-correct candidate, or a plain statement that none
   beat the baseline if that's the outcome.

---

### User Story 2 - Check whether a newer cuOpt release changes the picture (Priority: P2)

The currently installed cuOpt version is not necessarily the latest available. The researcher
wants to know whether upgrading to a newer release changes S85's solve time, correctness, or the
previously-documented broken-warm-start limitation, before concluding the settings space has been
exhausted on a possibly-outdated engine.

**Why this priority**: A settings sweep run against a version with a known, documented bug
(broken warm-start in the currently installed release) risks under-selling what cuOpt can actually
do; this must be checked before the sweep's conclusions are treated as final, but it is secondary
to the sweep itself since an upgrade with no improvement still leaves the settings sweep as the
main finding.

**Independent Test**: Can be fully tested by checking the latest available cuOpt release against
the installed one, and — if newer — re-running the baseline and the best-performing candidate(s)
from User Story 1 under the newer release without disturbing the environment other published
benchmarks depend on, then comparing results.

**Acceptance Scenarios**:

1. **Given** the installed cuOpt version, **when** the check runs, **then** it reports whether a
   newer release is available and, if so, what it is.
2. **Given** a newer release is available, **when** the baseline and best candidate(s) are re-run
   under it, **then** their wall time, iteration count, and correctness are recorded the same way
   as User Story 1, alongside a note on whether the previously-documented warm-start bug is still
   present.
3. **Given** no newer release is available, or the upgrade cannot be installed in the isolated
   test environment, **when** the check completes, **then** that is reported plainly and the
   settings-sweep results from User Story 1 stand as the current answer.

---

### User Story 3 - Non-simplifying preprocessing as a last resort (Priority: P3)

If neither a cuOpt-native setting nor a newer cuOpt release meaningfully closes the gap, the
researcher wants to know whether a preprocessing step applied before handing the model to cuOpt
could help it converge faster — but only if the preprocessing is provably non-simplifying: the
final reported result must correspond exactly to the original, full model (not a reduced,
aggregated, or approximated version of it), and it must not introduce a dependency on a
proprietary solver.

**Why this priority**: This is explicitly the least-preferred path in the request — pursued only
if the first two avenues don't work — and carries the highest risk of accidentally changing what
problem is actually being solved, so it needs the strictest correctness bar of the three.

**Independent Test**: Can be fully tested by applying a candidate preprocessing transform to S85,
solving the preprocessed model with cuOpt, reconstructing the result back to the original model's
variable space, and confirming the reconstructed result is verified-correct against the same
Gurobi ground truth used in User Story 1 — before its speed is even considered relevant.

**Acceptance Scenarios**:

1. **Given** a candidate preprocessing transform, **when** it is applied to S85 and the
   preprocessed model is solved, **then** the result is reconstructed back to the original
   model's full variable space and checked for correctness before any speed claim is made.
2. **Given** a preprocessing transform whose reconstructed result fails the correctness check,
   **when** results are reported, **then** it is disqualified outright — it is never reported as a
   viable option regardless of how much faster it solved.
3. **Given** this user story only runs because User Stories 1 and 2 did not produce a sufficient
   cuOpt-native win, **when** the final report is assembled, **then** it clearly labels any
   preprocessing-based finding as the fallback path it is, distinct from a cuOpt-native result.

---

### Edge Cases

- A candidate settings configuration is valid syntactically but produces `TimeLimit`,
  `NumericalError`, or another non-`Optimal` status — recorded as a failed/non-viable candidate,
  not silently dropped and not retried indefinitely.
- The parameter space is large enough that an exhaustive combinatorial sweep is impractical —
  the sweep covers every documented parameter individually/in documented-meaningful combinations,
  not a brute-force cross product of all values of all parameters.
- Upgrading cuOpt is not possible in the current environment (platform/CUDA incompatibility,
  network restriction) — reported as such; User Story 1's findings still stand on their own.
- A candidate setting or preprocessing transform happens to match Gurobi's objective by coincidence
  while violating the residual tolerance — still fails the correctness gate; objective agreement
  alone is never sufficient.
- No candidate across all three user stories beats the baseline while remaining verified-correct —
  reported plainly as a negative result (consistent with `specs/004-s85-solver-mode-experiment/`'s
  precedent), not implied or spun as a partial win.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The investigation MUST enumerate cuOpt's documented, LP-solving-relevant tunable
  parameters (e.g. method selection, PDLP solver mode, precision mode, tolerances, presolve,
  per-constraint-residual mode, and any others found in current official cuOpt documentation),
  going beyond the specific settings already tried in prior work
  (`specs/004-s85-solver-mode-experiment/`).
- **FR-002**: For each candidate configuration, the investigation MUST solve S85's
  already-published objective reaction with cuOpt and record wall time, iteration count, and
  solver status.
- **FR-003**: The investigation MUST verify every candidate's correctness by comparing its result
  against S85's already-established Gurobi ground truth (residual tolerance + objective
  agreement), reusing the existing published Gurobi result rather than re-solving it.
- **FR-004**: The investigation MUST check whether a cuOpt release newer than the currently
  installed one is available, and if so, evaluate it as described in User Story 2, without
  disturbing the environment that other already-published benchmarks depend on.
- **FR-005**: Each candidate (settings or version-upgrade re-run) MUST run with a bounded time
  budget and in a way that one candidate hanging, crashing, or erroring does not prevent the
  remaining candidates from running — same non-blocking pattern as
  `specs/004-s85-solver-mode-experiment/`.
- **FR-006**: Any configuration or preprocessing approach recommended as a result of this
  investigation MUST NOT depend on a proprietary solver or software at solve time. Gurobi's role
  in this investigation is strictly as an offline correctness oracle (as already established by
  prior benchmarks), never a runtime dependency of the recommended approach.
- **FR-007**: If User Stories 1 and 2 do not produce a verified-correct configuration that beats
  the baseline, the investigation MUST evaluate the non-simplifying preprocessing fallback
  described in User Story 3, clearly distinguishing it from a cuOpt-native result in the final
  report.
- **FR-008**: Any preprocessing transform considered MUST be reconstructible back to the original,
  full model's result — it MUST NOT reduce, aggregate, or approximate the problem in a way that
  changes what is actually being solved.
- **FR-009**: Running this investigation MUST NOT modify gpuGEM's shipped defaults
  (`gpugem/_defaults.py`) as a side effect — this is an experiment/investigation, matching the
  non-destructive pattern of `specs/004-s85-solver-mode-experiment/`. Promoting a winning
  candidate to a shipped default is a distinct, explicit follow-up action outside this feature's
  automatic scope.
- **FR-010**: The investigation MUST produce a single comparison covering every candidate
  attempted across all three user stories — including failed, timed-out, or disqualified ones —
  so no attempted approach is silently omitted from the record.
- **FR-011**: The investigation MUST record which documentation, tutorials, or release notes
  informed each candidate configuration, so the sweep is traceable to its sources rather than
  appearing as ad hoc guessing.

### Key Entities

- **Candidate Configuration**: A named cuOpt parameter set tested against S85; tracks its source
  (which documentation informed it), the cuOpt version it was tested under, and its recorded
  result (wall time, iterations, status, verified-correct or not).
- **cuOpt Version**: The specific cuOpt release under test (installed baseline vs. any newer
  release evaluated); tracks which candidates were run under which version and whether the
  previously-documented broken-warm-start limitation is still present.
- **Preprocessing Transform** (fallback only): A candidate transformation applied to S85 before
  solving; tracks whether its result is reconstructible back to the original model's full
  variable space and whether that reconstructed result is verified-correct.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The investigation produces a definitive, evidence-backed answer to whether any
  purely cuOpt-native configuration narrows S85's cuOpt-vs-Gurobi runtime gap while remaining
  verified-correct — every configuration attempted has a recorded, verified-correct-or-not
  outcome, with none silently omitted.
- **SC-002**: The investigation determines whether upgrading to the latest available cuOpt release
  changes S85's solve time, correctness, or the previously-documented broken-warm-start
  limitation, without disrupting any already-published benchmark result.
- **SC-003**: If a preprocessing-based approach is explored, its reconstructed result is proven to
  exactly match the original, unpreprocessed model's verified-correct result before its speed is
  considered relevant at all — a preprocessing candidate that changes the answer is never reported
  as viable regardless of speed.
- **SC-004**: A single, complete comparison of every approach attempted (settings sweep, version
  upgrade, and — if reached — preprocessing) ranked by verified speedup over the current baseline
  is available for review in one place, without needing to re-run any already-completed candidate.

## Assumptions

- S85 is an adequate proxy for "big models like S85" for this investigation, per the user's
  explicit instruction; re-validating a winning candidate across the other large models
  (S9/S15/S23/S83, Harvey, Harvetta) is a follow-up decision outside this feature's scope.
- "Optimal setting" means verified-correct (same correctness gate used throughout this project's
  benchmarks) **and** faster than the currently shipped large-model default; a tie or non-
  improvement is a valid, reportable outcome of the investigation, not a failure of the feature.
- Testing a newer cuOpt release will be done in a way that does not disturb the currently pinned
  environment other published benchmarks depend on (e.g. an isolated environment/clone) — an
  upgrade evaluated here is exploratory and does not itself change the project's supported cuOpt
  version.
- Gurobi continues to serve only as the correctness oracle already established by prior benchmarks
  (`specs/002-benchmark-cuopt-gurobi/` and later) — it is never proposed as part of a recommended
  runtime configuration, consistent with the "no proprietary software dependency" constraint.
- "Open source tools" other than cuOpt itself are permitted for the preprocessing fallback (User
  Story 3) if reached, but are explicitly discouraged relative to a cuOpt-native settings win, per
  the user's stated preference.
- This investigation does not itself change `gpugem/_defaults.py`; if a winning candidate is
  found, promoting it to a shipped default is expected to follow this project's existing
  correctness-validated-defaults process as a separate, later step.
