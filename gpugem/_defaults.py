"""
Default cuOpt solver settings derived from systematic benchmarking on whole-body
metabolic models across two scale classes.

Small models (≤ 100K reactions, e.g. Harvey whole-body model):
    - Double precision (pdlp_precision=0) does not converge at tolerances
      tighter than 1e-4 on these models; mixed precision is required.
    - Single precision (pdlp_precision=2) hits the FP32 precision wall.
    - tol=1e-8 + mixed precision → zero stoichiometric violations at max residual 1e-6.
    - per_constraint_residual=1 (max-norm convergence) further reduces violations
      vs tightening tolerances alone.
    - PaPILO presolve adds postsolve reconstruction error on well-conditioned models;
      the default PSLP presolve is correct at this scale.

Large models (> 100K reactions, e.g. personalised microbiome whole-body models):
    - cuOpt's default PSLP presolve incorrectly reports Infeasible on models with
      extreme stoichiometric coefficient ranges ([1e-6, 2e5]); PaPILO is required.
    - per_constraint_residual=1 reduces violations by ~44% and max residual by ~100×.
    - Tight tolerances do not improve accuracy: the bottleneck is a hardcoded feastol
      in cuOpt's PaPILO integration, not PDLP convergence.
"""

# Models at or below this reaction count use the Harvey-tuned settings.
_SMALL_MODEL_THRESHOLD = 100_000


def default_settings(n_vars: int, time_limit: float = 60.0) -> dict:
    """
    Return the recommended cuOpt parameter dict for a model of the given size.

    Parameters
    ----------
    n_vars:
        Number of variables (reactions) in the LP.
    time_limit:
        Wall-clock time limit in seconds passed to cuOpt.

    Returns
    -------
    dict
        Parameter names and values ready to pass to ``SolverSettings.set_parameter``.
    """
    if n_vars <= _SMALL_MODEL_THRESHOLD:
        # Harvey-scale: mixed precision + tight tolerances + max-norm convergence.
        # Double precision (pdlp_precision=0) does not converge on these models at
        # tolerances tighter than 1e-4. PaPILO is not used — PSLP is correct on
        # well-conditioned models and PaPILO postsolve adds reconstruction error.
        return {
            "method": 1,                           # PDLP
            "pdlp_precision": 1,                   # mixed FP32/FP64 — required; double diverges
            "absolute_primal_tolerance": 1e-8,
            "relative_primal_tolerance": 1e-8,
            "absolute_dual_tolerance":   1e-8,
            "relative_dual_tolerance":   1e-8,
            "per_constraint_residual":   1,        # max-norm → better postsolve quality
            "time_limit": time_limit,
        }
    else:
        # Microbiome-scale: PaPILO presolve required + max-norm convergence.
        # Tight tolerances are NOT set — the accuracy floor is PaPILO's hardcoded
        # feastol=1e-5, independent of PDLP tolerance.
        return {
            "method": 1,                           # PDLP
            "presolve": 1,                         # PaPILO — avoids PSLP false-infeasible bug
            "per_constraint_residual": 1,          # max-norm convergence
            "time_limit": time_limit,
        }
