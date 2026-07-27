# Phase 0 Research: S85 Alternative Solver-Mode Experiment

## R1. Why each variant needs its own OS process, and how

**Decision**: The orchestrator (`run_solver_mode_experiment.py`) launches each variant as a fresh
child process via `subprocess.run([sys.executable, "-m", "benchmarks._solver_mode_worker",
variant_id, ...], timeout=budget)` — a genuinely separate OS process and CUDA context, not a
`multiprocessing` fork and not an in-process call.

**Rationale**: Two of the three candidates (`method=Concurrent`, `method=Barrier` cold) have never
been run on this model family. Barrier in particular performs a sparse Cholesky/LDL factorization
via cuDSS; on an ~874,634-variable, ~1,993,029-row problem with no prior data point, an
out-of-memory abort (GPU or host RAM) is a real, plausible outcome, and OOM kills typically arrive
as an uncatchable `SIGKILL` — no Python exception handler in the same process can save the
experiment's remaining variants or its already-collected results if this happens in-process. A
separate process means a crash in one variant is just a nonzero/negative exit code the parent
observes and records, with zero effect on the other three variants. `subprocess.run` (not
`multiprocessing.Pool`) is used specifically because the default `fork` start method on Linux does
not produce a clean CUDA context in the child (a well-known CUDA/fork incompatibility) — a genuine
new Python process via `sys.executable` avoids that entirely, matching how the `003` sweep's
GPU-host validation was itself run as independent process invocations.

**Alternatives considered**:
- *In-process, catch exceptions* — rejected: cannot catch a `SIGKILL` from the OOM killer or a
  CUDA driver-level crash; a single bad variant could take down the whole experiment and any
  variants after it in the list, directly violating spec FR-005/User Story 3.
- *`multiprocessing` with `fork` context* — rejected: CUDA contexts are not fork-safe; the forked
  child inherits a CUDA state that is undefined/broken, a well-documented failure mode.
- *`multiprocessing` with `spawn` context* — viable in principle (spawn avoids the fork issue) but
  adds pickling/serialization complexity for no benefit over `subprocess.run` with a small,
  file-based worker entry point that just re-reads the variant registry by id; `subprocess.run`
  is simpler and its `timeout=` parameter directly implements the time-budget requirement (R3).

## R2. Passing variant configuration across the process boundary

**Decision**: The worker subprocess is invoked with only the `variant_id` (a string) as its
argument; it re-imports `benchmarks.solver_mode_variants` and looks up the same
`SolverModeVariant` entry the parent already has, rather than serializing the `cuopt_kwargs` dict
across the boundary.

**Rationale**: `solver_mode_variants.py` is a plain, deterministic, file-based registry (same
pattern as `s85_objectives.py`'s `OBJECTIVES`) — both processes import the identical source, so
looking the variant up by id in the child guarantees it sees exactly the same configuration the
parent used to decide to launch it, with no serialization/versioning risk.

**Alternatives considered**:
- *Serialize `cuopt_kwargs` as a JSON CLI argument* — rejected: redundant with the registry import,
  and risks the child silently using a stale or hand-edited copy if the two ever diverge.

## R3. Time budget: cuOpt's own `time_limit` vs. the subprocess-level timeout

**Decision**: Two layers, not one. cuOpt's own `time_limit` parameter (passed through
`gpugem.solve`) is the primary stopping mechanism and produces a clean `"TimeLimit"` status from
inside the solve — this is how `002`/`003` already report a variant that didn't converge.
`subprocess.run(..., timeout=budget)` is a backstop, set to `time_limit + 60s` grace, that only
fires if a variant hangs in a way that ignores cuOpt's own limit (plausible for a single very long
factorization step in Barrier that isn't checked mid-step).

**Rationale**: Relying on the subprocess timeout alone would mean every timed-out variant looks
identical to a hang (`TimeoutExpired`, process killed), losing the distinction between "reached
`TimeLimit` cleanly with a partial/primal-feasible result" and "never got anywhere." Relying on
cuOpt's `time_limit` alone would mean a true hang (e.g. stuck inside a C++/CUDA call that doesn't
poll the time budget) blocks the whole experiment indefinitely, which is exactly what spec User
Story 3 rules out.

**Alternatives considered**:
- *Subprocess timeout only, no cuOpt `time_limit`* — rejected: loses the clean-vs-hung distinction
  described above.
- *cuOpt `time_limit` only, no subprocess timeout* — rejected: no protection against a genuine hang
  inside the C++/CUDA layer that doesn't respect the budget, which is exactly the unknown-behavior
  risk motivating User Story 3 in the first place.

## R4. Distinguishing "timed out cleanly," "crashed," and "succeeded"

**Decision**: The orchestrator classifies each variant's outcome from the subprocess's own exit
behavior:
- Exit code 0 with a parseable JSON result on stdout → proceed to the normal correctness gate
  (verified-correct / verified-incorrect, per `002`/`003`'s existing logic).
- `subprocess.TimeoutExpired` → recorded as `status: "DidNotComplete"`, reason `"timeout"`.
- Nonzero/negative exit code (crash, OOM kill, CUDA error) with no parseable result → recorded as
  `status: "DidNotComplete"`, reason `"crashed"` (exit code included for diagnosis).

**Rationale**: Spec FR-005 and the Edge Cases section both require a variant that doesn't finish to
be recorded distinctly from both a correct and an incorrect result — collapsing "timed out" and
"crashed" into one bucket would still satisfy the letter of FR-005 but loses diagnostic value for
almost no extra code (the two cases are already naturally distinguished by whether
`subprocess.run` raised `TimeoutExpired` or returned a bad exit code).

## R5. Defining the "baseline" variant

**Decision**: The baseline variant applies **zero** `cuopt_kwargs` overrides — it calls
`gpugem.solve` exactly as `benchmarks.solve.solve_cuopt` already does, letting
`gpugem._defaults.default_settings` supply the large-model defaults (`method=1` PDLP,
`presolve=1` PaPILO, `per_constraint_residual=1`) untouched.

**Rationale**: Hand-copying the current default values into an explicit override dict would risk
silent drift if `_defaults.py` ever changes — the baseline would then be testing stale settings
without anyone noticing. Applying no overrides at all guarantees the baseline is always,
by construction, "whatever `gpugem` currently ships," which is the correct comparison point and
requires zero maintenance.

## R6. Solving Gurobi once, not once per variant

**Decision**: Gurobi's reference solve (used for the objective-agreement half of the correctness
gate) runs exactly once per experiment invocation, in the orchestrator itself, before any cuOpt
variant subprocess is launched. Its objective value is passed to each worker (or compared
post-hoc by the orchestrator) rather than re-solved per variant.

**Rationale**: Gurobi's result does not depend on which cuOpt setting is under test — re-solving it
four times would cost an extra ~150s (3 x ~52s) for zero additional information, and risks
introducing spurious run-to-run Gurobi variance into what should be a controlled comparison across
cuOpt variants only.

**Alternatives considered**: *Re-solve Gurobi inside each worker subprocess* — rejected as
described; also would have complicated R1's process-isolation design for no benefit, since Gurobi
solves have already been shown reliable and fast (`002`/`003`) and are not the thing under test.

## R7. Speedup/best-candidate computation

**Decision**: For each verified-correct candidate, `speedup = baseline_solve_s /
candidate_solve_s` (>1 means faster than baseline). The best candidate is
`argmin(candidate_solve_s)` among verified-correct candidates whose `speedup > 1`; if no candidate
is both verified-correct and faster than baseline, the comparison explicitly states that (spec
FR-006, User Story 2 Acceptance Scenario 3) rather than omitting a "best candidate" field.

**Rationale**: Directly matches FR-006's wording; a simple, auditable ratio avoids any ambiguity
about what "improvement" means.

## R8. `solved_by` applies uniformly, not just to Concurrent

**Decision**: `sol.get_solved_by()` (confirmed live: `SolverMethod` enum —
`Concurrent/PDLP/DualSimplex/Barrier/Unset`) is captured for every variant, not conditionally only
when `method=Concurrent` is set.

**Rationale**: Simpler and more informative to always record it — for the `baseline` and
`methodical1` variants (which force `method=1`/PDLP) it should consistently read back `"PDLP"`,
and for `barrier_cold` it should read back `"Barrier"`; capturing it uniformly turns "does the
reported method match what we requested" into a free consistency check across every variant, not
just Concurrent, and needs no special-casing in the worker.
