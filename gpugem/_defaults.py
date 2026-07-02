"""
Default cuOpt solver settings derived from systematic benchmarking.

References
----------
Harvey whole-body model  (81K vars, 160K constraints):
    Best Optimal config: per_constraint_residual=1, no PaPILO presolve
    → 0.758s, 390 stoich violations at max 1.79e-5

Microbiome whole-body models (789K vars, 1.66M constraints):
    Best Optimal config: presolve=1 (PaPILO) + per_constraint_residual=1
    → 27s, 1441 stoich violations at max 8.4e-5

The threshold between "small" and "large" is set at 100K reactions:
- Small (≤ 100K reactions): per_constraint_residual alone is sufficient;
  PaPILO presolve adds postsolve reconstruction error on well-conditioned models.
- Large (> 100K reactions): PaPILO is required to avoid cuOpt's PSLP
  false-infeasibility bug that triggers on models with extreme coefficient ranges.
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
    base = {
        "method": 1,                    # PDLP (GPU first-order)
        "per_constraint_residual": 1,   # max-norm convergence — better postsolve accuracy
        "time_limit": time_limit,
    }

    if n_vars > _SMALL_MODEL_THRESHOLD:
        # Large / ill-conditioned models: PaPILO presolve is required.
        # Default PSLP (presolve=-1) incorrectly reports infeasibility on models
        # with extreme stoichiometric coefficient ranges (e.g. [1e-6, 2e5]).
        base["presolve"] = 1

    return base
