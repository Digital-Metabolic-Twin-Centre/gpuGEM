"""Candidate registry for the cuOpt-native settings-tuning investigation on S85.

Answers: does any purely cuOpt-native setting (no proprietary solver dependency),
a newer cuOpt release, or -- as a last resort -- a non-simplifying preprocessing
step, close (ideally beat outright, not just narrow) the cuOpt/Gurobi runtime gap
on S85, the project's real preferred goal for whole-body/microbiome models. Every
settings candidate is expressed purely as **cuopt_kwargs overrides through
gpugem.solve's existing per-call override mechanism -- gpugem/_defaults.py is
never touched (spec FR-009). Every entry's cuopt_kwargs is grounded in a specific
research.md finding (R2/R3/R4), recorded in source_note, not guessed
(spec FR-011).

See specs/012-cuopt-native-tuning/.
"""
from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent

# id, user_story, cuopt_kwargs, warm_start, source_note, requires_isolated_venv
CANDIDATES = [
    {
        "id": "baseline",
        "user_story": "US1",
        "cuopt_kwargs": {},
        "warm_start": False,
        "source_note": "R1 cross-check: gpugem's current shipped large-model defaults "
                        "(method=PDLP, presolve=PaPILO, per_constraint_residual=1), applied "
                        "by giving no overrides at all so this can never silently drift from "
                        "what gpugem._defaults.default_settings actually ships.",
        "requires_isolated_venv": False,
    },
    {
        "id": "pdlp_mode_fast1",
        "user_story": "US1",
        "cuopt_kwargs": {"pdlp_solver_mode": 3},
        "warm_start": False,
        "source_note": "R2: pdlp_solver_mode=Fast1 -- 'fastest mode, but with less success "
                        "in convergence' per the installed package's own enum docstring. "
                        "Never tried in specs/004-s85-solver-mode-experiment/, which only "
                        "tested Methodical1 vs. the Stable3 baseline.",
        "requires_isolated_venv": False,
    },
    {
        "id": "pdlp_precision_mixed",
        "user_story": "US1",
        "cuopt_kwargs": {"pdlp_precision": 2},
        "warm_start": False,
        "source_note": "R3: true Mixed precision (verified enum: -1=Default, 0=Single, "
                        "1=Double, 2=Mixed, from cpp/include/.../constants.h). Never "
                        "actually exercised on any model in this project under either name "
                        "-- gpugem's own pdlp_precision=1 comment mislabels Double as "
                        "'mixed'; true Mixed has never been tried.",
        "requires_isolated_venv": False,
    },
    {
        "id": "pdlp_precision_single",
        "user_story": "US1",
        "cuopt_kwargs": {"pdlp_precision": 0},
        "warm_start": False,
        "source_note": "R3: Single/FP32 precision, included for completeness (spec FR-001 "
                        "-- every documented parameter). Expected to hit the FP32 precision "
                        "floor observed empirically on e_coli_core (residual floors ~2.7e-3, "
                        "cannot reach this project's tolerances) -- included to confirm that "
                        "expectation holds at S85's scale too, not assumed.",
        "requires_isolated_venv": False,
    },
    {
        "id": "pdlp_precision_double_explicit",
        "user_story": "US1",
        "cuopt_kwargs": {"pdlp_precision": 1},
        "warm_start": False,
        "source_note": "R3: explicit Double precision. On e_coli_core this produced a "
                        "bit-identical result to pdlp_precision=-1 (cuOpt's own Default). "
                        "This candidate confirms whether that equivalence (Default==Double) "
                        "also holds at S85's scale, or whether Default resolves differently "
                        "on a problem this large/ill-conditioned.",
        "requires_isolated_venv": False,
    },
    {
        "id": "presolve_pslp_retest",
        "user_story": "US1",
        "cuopt_kwargs": {"presolve": 2},
        "warm_start": False,
        "source_note": "R4: presolve=PSLP (verified enum: -1=Default, 0=OFF, 1=PaPILO, "
                        "2=PSLP). gpugem's large-model default forces PaPILO (1) specifically "
                        "because PSLP was found to falsely report Infeasible on extreme-"
                        "coefficient-range models. The 26.04 release notes record 'Update to "
                        "the latest version of PSLP which includes bug fixes for incorrect "
                        "infeasible classification' -- this candidate re-tests whether that "
                        "fix (already present in the installed 26.6.0) resolves it for S85, "
                        "which would make PSLP a viable, likely-faster alternative to PaPILO "
                        "(PaPILO's postsolve is documented to add reconstruction error).",
        "requires_isolated_venv": False,
    },
    {
        "id": "first_primal_feasible",
        "user_story": "US1",
        "cuopt_kwargs": {"first_primal_feasible": True},
        "warm_start": False,
        "source_note": "R2: new, untested axis -- stop as soon as a primal-feasible iterate "
                        "is found rather than waiting for full dual/gap convergence, directly "
                        "relevant since S85's bottleneck is convergence speed, not feasibility "
                        "per se.",
        "requires_isolated_venv": False,
    },
    {
        "id": "infeasibility_detection_strict",
        "user_story": "US1",
        "cuopt_kwargs": {"infeasibility_detection": True, "strict_infeasibility": True},
        "warm_start": False,
        "source_note": "R2: new, untested axis -- PDLP-only infeasibility-detection options; "
                        "included for completeness of the documented parameter space.",
        "requires_isolated_venv": False,
    },
    {
        "id": "save_best_primal",
        "user_story": "US1",
        "cuopt_kwargs": {"save_best_primal_so_far": True},
        "warm_start": False,
        "source_note": "R2: new, untested axis -- retains the best-seen primal iterate "
                        "rather than the last one, in case PDLP's iterate quality is "
                        "non-monotonic on this ill-conditioned problem.",
        "requires_isolated_venv": False,
    },
    {
        "id": "warm_start_stable2",
        "user_story": "US1",
        "cuopt_kwargs": {"presolve": 0, "pdlp_solver_mode": 1},
        "warm_start": True,
        "source_note": "R4: presolve=0 is fully OFF (distinct from PSLP=2) -- verified via "
                        "constants.h and required for PDLP warm start per the 26.02 release "
                        "notes ('presolve must now be explicitly disabled by setting "
                        "CUOPT_PRESOLVE=0'). pdlp_solver_mode=Stable2 is one of the two modes "
                        "SolverSettings.set_pdlp_warm_start_data's own installed docstring "
                        "confirms are supported ('Only supported solver modes are Stable2 and "
                        "Fast1') -- kept separate from the PSLP re-test above, not combined.",
        "requires_isolated_venv": False,
    },
    {
        "id": "warm_start_fast1",
        "user_story": "US1",
        "cuopt_kwargs": {"presolve": 0, "pdlp_solver_mode": 3},
        "warm_start": True,
        "source_note": "R4: the other of the two warm-start-supported modes per the "
                        "installed docstring.",
        "requires_isolated_venv": False,
    },
    {
        "id": "barrier_augmented_system",
        "user_story": "US1",
        "cuopt_kwargs": {"method": 3, "augmented": 1},
        "warm_start": False,
        "source_note": "R4-followup: specs/004-s85-solver-mode-experiment/ found cold Barrier "
                        "fails almost immediately with NumericalError (~7s) on S85. Barrier's "
                        "default linear-system formulation (augmented=-1, auto) typically means "
                        "normal equations (ADAT), which SQUARES the condition number of the "
                        "constraint matrix -- S85's raw condition number is ~2e11 (research.md "
                        "R5), so ADAT would face ~4e22, well past float64 factorization limits. "
                        "augmented=1 forces the augmented-system formulation instead, which does "
                        "not square the conditioning -- a concrete, well-motivated hypothesis for "
                        "why cold Barrier failed, never tried.",
        "requires_isolated_venv": False,
    },
    {
        "id": "barrier_ordering_amd",
        "user_story": "US1",
        "cuopt_kwargs": {"method": 3, "ordering": 1},
        "warm_start": False,
        "source_note": "R4-followup: AMD fill-reducing ordering instead of cuDSS's own default "
                        "(ordering=-1/0) for Barrier's sparse factorization -- a different "
                        "ordering can materially change numerical stability on an "
                        "extreme-coefficient-range matrix, untested on this model family.",
        "requires_isolated_venv": False,
    },
    {
        "id": "barrier_dualize",
        "user_story": "US1",
        "cuopt_kwargs": {"method": 3, "dualize": 1},
        "warm_start": False,
        "source_note": "R4-followup: solve S85's dual instead of its primal via Barrier -- the "
                        "dual's conditioning is not identical to the primal's and has never been "
                        "checked on this model family.",
        "requires_isolated_venv": False,
    },
    {
        "id": "dual_simplex_isolated",
        "user_story": "US1",
        "cuopt_kwargs": {"method": 2},
        "warm_start": False,
        "source_note": "R2-followup: pure DualSimplex, isolated -- specs/004-s85-solver-mode-"
                        "experiment/ only ever exercised it indirectly (raced inside "
                        "method=Concurrent, where PDLP won). The 26.06 release notes record "
                        "dual simplex performance work ('16% faster on NETLIB LP') and a new "
                        "right-looking Markowitz LU factorization since whatever version "
                        "informed that Concurrent race -- worth an isolated head-to-head.",
        "requires_isolated_venv": False,
    },
]

# Not fresh-solved -- pointers to an already-published result from a prior feature,
# included in the final comparison for completeness (spec FR-010) without re-spending
# GPU time on a number that already exists.
LINKED_RESULTS = [
    {
        "id": "per_constraint_residual_0",
        "user_story": "US1",
        "result_path": HERE / "results" / "residual_tradeoff" / "S85.json",
        "result_key": "residual_0",
        "source_note": "R2: already quantified exhaustively by "
                        "specs/005-residual-tradeoff-benchmark/ (per_constraint_residual=0 "
                        "vs. the shipped per_constraint_residual=1 default) -- not "
                        "re-litigated here, linked for completeness only.",
    },
]


# The one last-resort preprocessing candidate (User Story 3) -- only meaningful
# once US1/US2 show no cuOpt-native win (spec: explicitly discouraged relative to
# a settings-only win). transform/inverse live in cuopt_tuning_preprocessing.py;
# imported lazily inside the worker (not at module import time) so importing
# this registry never requires numpy/scipy to already be solving anything.
PREPROCESSING_CANDIDATES = [
    {
        "id": "ruiz_equilibration_external",
        "user_story": "US3",
        "source_note": "R8: external row/column Ruiz-style equilibration tuned to S85's "
                        "known [1e-6, 2e5] coefficient range (R5) -- exact, invertible linear "
                        "reformulation, not an approximation. Last resort: cuOpt already "
                        "performs its own internal Ruiz equilibration non-configurably (R5), "
                        "so this is not expected to add much on top of that.",
    },
]


def get_candidate(candidate_id):
    for c in CANDIDATES:
        if c["id"] == candidate_id:
            return c
    for c in PREPROCESSING_CANDIDATES:
        if c["id"] == candidate_id:
            return {**c, "cuopt_kwargs": {}, "warm_start": False,
                     "requires_isolated_venv": False}
    raise KeyError("no such candidate id: %r" % candidate_id)


def select_upgrade_candidates(results_dir):
    """Return the ids to re-run under the cuOpt version-upgrade venv (User Story 2):
    the baseline plus the single fastest verified-correct US1 settings candidate
    already on disk, if any -- data-driven, not a hardcoded guess (spec FR-004)."""
    import json

    best_id = None
    best_solve_s = None
    for c in CANDIDATES:
        if c["user_story"] != "US1" or c["id"] == "baseline":
            continue
        p = Path(results_dir) / (c["id"] + ".json")
        if not p.exists():
            continue
        result = json.loads(p.read_text())
        if not result.get("verified_correct"):
            continue
        solve_s = result.get("solve_s")
        if solve_s is None:
            continue
        if best_solve_s is None or solve_s < best_solve_s:
            best_solve_s = solve_s
            best_id = c["id"]

    ids = ["baseline"]
    if best_id is not None:
        ids.append(best_id)
    return ids
