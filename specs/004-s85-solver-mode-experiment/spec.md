# Feature Specification: S85 Alternative Solver-Mode Experiment

**Feature Branch**: `004-s85-solver-mode-experiment`

**Created**: 2026-07-27

**Status**: Draft

**Input**: User description: "Test alternative cuOpt PDLP solver settings on the S85 model to see whether they close the ~9-10x cuOpt/Gurobi runtime gap observed in the 002 cross-scale benchmark and confirmed structural (not objective-specific) by the 003 multi-objective sweep. Specifically evaluate three settings changes, each currently unused/overridden by gpugem's large-model defaults: (1) pdlp_solver_mode=Methodical1 instead of the default Stable3 -- described as more thorough/better on hard problems, untested on these microbiome whole-body models; (2) method=Concurrent, the solver's own actual default, instead of gpugem's hardcoded PDLP-only, which forecloses the other methods entirely; (3) method=Barrier run cold (no warm start), theoretically more tolerant of ill-conditioning than PDLP, never tested on these models. For each variant, solve S85 and record wall time, iteration count, and correctness, so we can tell whether any variant meaningfully reduces cuOpt's solve time without sacrificing correctness. Must not modify gpugem's shipped defaults -- this is an experiment/comparison, not a defaults change."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run each candidate setting against S85 and see whether it helps (Priority: P1)

A researcher who has established that cuOpt is structurally ~9-10x slower than Gurobi on the S85
model (regardless of which objective is used) wants to know whether any of three specific,
currently-unused solver-mode settings changes closes that gap, without having to hand-run and
manually compare each one. They run the experiment and get back, for each candidate setting and
for the current (unchanged) baseline setting, the solve time, iteration count, and whether the
solution was still correct.

**Why this priority**: This is the entire point of the feature — without it, there is no answer
to whether any of the three candidate settings actually helps, which is the question motivating
this work.

**Independent Test**: Can be fully tested by running the experiment against S85 and confirming
that a result (solve time, iteration count, correctness) is recorded for the current baseline
setting and for each of the three candidate settings, on the same objective and the same
underlying LP.

**Acceptance Scenarios**:

1. **Given** the S85 model solved with cuOpt's current settings (the same ones already used in
   the existing cross-scale benchmark) as a baseline, **when** the experiment also solves the
   identical LP with each of the three candidate settings applied one at a time, **then** a
   result (solve time, iteration count, solver status, and a feasibility/correctness check
   against Gurobi's solution) is recorded for the baseline and for every candidate.
2. **Given** a candidate setting whose solve does not reach a verified-correct solution (wrong
   objective, infeasible result, or it does not finish within the allotted time), **when** the
   experiment records its result, **then** that outcome is captured explicitly (not silently
   dropped and not misreported as a successful improvement).
3. **Given** the experiment has already produced a baseline result from prior work (the existing
   S85 cross-scale benchmark numbers), **when** the researcher reviews this experiment's own
   freshly-recorded baseline, **then** the two are close enough to confirm they're measuring the
   same thing (consistent with normal run-to-run variance).

---

### User Story 2 - Compare all candidates against the baseline in one place (Priority: P2)

Having run all three candidates, the researcher wants a single, clear comparison showing how each
one's solve time and iteration count relate to the baseline, so they can immediately tell whether
any candidate is a meaningful improvement, a wash, or worse — without manually cross-referencing
separate result files.

**Why this priority**: Individual results (User Story 1) are necessary but not sufficient — the
research question is comparative ("did any of these help, and by how much"), so a side-by-side
view is what actually answers it.

**Independent Test**: Can be fully tested by, after User Story 1's results exist, producing a
report that shows each candidate's solve time and iteration count alongside the baseline's, plus
a clear speedup/slowdown figure for each, and confirming it correctly identifies the fastest
verified-correct candidate (if any beats the baseline).

**Acceptance Scenarios**:

1. **Given** results exist for the baseline and all three candidates, **when** the comparison
   report is produced, **then** it shows, for each candidate, how its solve time compares to the
   baseline (faster/slower and by what factor) and whether it remained correct.
2. **Given** one or more candidates are faster than the baseline and still correct, **when** the
   report is produced, **then** it clearly identifies the best-performing verified-correct
   candidate.
3. **Given** none of the candidates improve on the baseline, **when** the report is produced,
   **then** it says so plainly rather than implying an improvement exists.

---

### User Story 3 - Don't let an unproven setting hang the experiment (Priority: P3)

Because two of the three candidate settings (Concurrent and cold Barrier) have never been tried
on this model family and could behave unpredictably (e.g. Barrier attempting a very large
factorization, or Concurrent waiting on its slowest competing method), the researcher wants a
guarantee that a misbehaving candidate is capped and clearly reported as "did not finish in the
allotted time" rather than blocking the rest of the experiment indefinitely.

**Why this priority**: Lower priority than getting and comparing results, but without it a single
bad candidate could make the whole experiment unusable, since two of the three settings are
explicitly untested on this model.

**Independent Test**: Can be fully tested by capping a candidate's allotted solve time and
confirming that if it doesn't finish first, the experiment reports a clear "did not finish within
the time budget" outcome for that candidate and still proceeds to run the remaining candidates.

**Acceptance Scenarios**:

1. **Given** a candidate setting that does not reach a solution within its allotted time,
   **when** the time budget is reached, **then** the experiment records it as not-completed
   (not as a false success or a crash) and moves on to the next candidate.
2. **Given** one candidate hits its time budget, **when** the researcher reviews the overall
   comparison (User Story 2), **then** that candidate is clearly marked as inconclusive rather
   than being silently omitted or counted as a failure equivalent to "produced a wrong answer."

---

### Edge Cases

- What happens if a candidate setting produces a solution that disagrees with Gurobi's objective
  value beyond the established tolerance, or fails the feasibility residual check? It MUST be
  recorded as not verified-correct, and MUST NOT be considered a viable improvement even if it
  finished faster than the baseline.
- What happens if the Concurrent setting's winning method changes between runs (since it races
  multiple methods and returns whichever finishes first)? Each run's result MUST record which
  underlying method actually produced the returned solution, not just report "Concurrent" as if
  it were a single deterministic method.
- What happens if a candidate is not actually different in practice from the baseline (e.g.
  Concurrent ends up picking PDLP anyway)? That MUST still be reported as its own explicit result,
  not merged with or hidden by the baseline result.
- What happens if this experiment is re-run later (e.g. after a cuOpt version upgrade)? Re-running
  MUST be possible without any special handling beyond what already exists for reproducible
  benchmarks in this project (fresh results, same comparison method).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST solve the S85 model's linear program with cuOpt under the current
  (unchanged) baseline settings and under each of the three candidate settings
  (`pdlp_solver_mode=Methodical1`, `method=Concurrent`, `method=Barrier` run without a warm
  start), using the same objective and the same underlying LP for every variant.
- **FR-002**: For every variant (baseline and each candidate), the system MUST record wall-clock
  solve time, iteration count (where the underlying method reports one), solver status, and a
  correctness check consisting of the feasibility residual and agreement with Gurobi's objective
  value on the same LP, using the tolerances already established in this project's existing
  benchmark tooling.
- **FR-003**: A variant's solve time MUST NOT be treated as a valid comparison point unless it
  passes the correctness check; a variant that finishes fast but fails correctness MUST be
  reported as such, not counted as an improvement.
- **FR-004**: When the Concurrent setting is used, the system MUST record which underlying method
  (PDLP, Dual Simplex, or Barrier) actually produced the returned solution, since Concurrent races
  multiple methods and the winner can vary.
- **FR-005**: Each variant's solve MUST be subject to a time budget; a variant that does not reach
  a solution within its budget MUST be recorded as not-completed/inconclusive, distinctly from
  both a verified-correct result and a verified-incorrect result, and MUST NOT block the remaining
  variants from being attempted.
- **FR-006**: The system MUST produce a single comparison of all variants against the baseline,
  showing each candidate's solve-time and iteration-count relationship to the baseline
  (speedup/slowdown factor) and whether it was verified-correct, and MUST clearly identify the
  fastest verified-correct candidate if one outperforms the baseline, or state plainly that none
  do.
- **FR-007**: The experiment MUST NOT modify this project's shipped default solver settings; it
  MUST run as a self-contained comparison that consumes the existing settings and LP-building
  logic without altering them.
- **FR-008**: The experiment MUST be re-runnable, producing a fresh, independently reviewable
  result each time, consistent with how this project's other benchmarks are reproduced.

### Key Entities *(include if feature involves data)*

- **SolverModeVariant**: One configuration under test — its name/id (baseline, methodical1,
  concurrent, barrier_cold), the specific setting(s) that differ from the current defaults, and a
  short rationale for why it might help (drawn from prior investigation notes).
- **VariantResult**: The outcome of solving S85 under one variant — solve time, iteration count,
  solver status, which underlying method actually ran (relevant for Concurrent), feasibility
  residual, objective value, agreement with Gurobi, and whether it completed within its time
  budget.
- **VariantComparison**: The aggregated view across all variants — each candidate's speedup/
  slowdown factor relative to the baseline, its correctness outcome, and the identified
  best-performing verified-correct candidate (if any).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A researcher can determine, from one comparison, whether any of the three candidate
  solver-mode settings reduces cuOpt's solve time on S85 relative to the current baseline, and if
  so, by what factor, without manually running or cross-referencing separate experiments.
- **SC-002**: Every reported solve-time comparison is paired with a correctness verification, so a
  faster-but-wrong result can never be mistaken for a genuine improvement.
- **SC-003**: A candidate setting that behaves unpredictably (does not finish, or races
  unpredictably in the case of Concurrent) does not prevent the researcher from getting results
  for the other candidates in the same run.
- **SC-004**: The project's currently shipped default solver behavior is unchanged after this
  experiment is run — re-running the existing cross-scale benchmark afterward produces the same
  settings-derived behavior as before.

## Assumptions

- The experiment solves S85 using the same objective already used in the existing cross-scale
  benchmark (the model's whole-body objective), so its baseline result is directly comparable to
  the previously-recorded ~52s (Gurobi) / ~509s (cuOpt) numbers. Testing the candidate settings
  across multiple objectives is out of scope here; if a candidate looks promising, a follow-up
  could combine it with the multi-objective sweep.
- Each variant is solved once (not repeated) by default, consistent with this project's existing
  precedent of preferring breadth across variants over repeats of a single one when wall time is
  constrained; a promising candidate can be manually re-run with repeats to confirm stability.
- The per-variant time budget defaults to the same value already used elsewhere in this project's
  benchmarks; because two of the three candidates are untested on this model family and could
  behave very differently from PDLP, a longer or separately configurable budget for this
  experiment specifically may be warranted, but the default is a reasonable starting point.
- This experiment is exploratory tooling, not a change to any shipped default — even if a
  candidate outperforms the baseline, adopting it as a new default is a separate follow-up
  decision requiring its own benchmark-backed justification (per this project's governance rules
  for changing defaults), not an automatic outcome of this feature.
- "Cold" Barrier means no warm-start data is supplied, since warm-starting is a known-broken path
  in the currently installed solver version; this experiment tests Barrier's behavior as a
  standalone, from-scratch solve.
