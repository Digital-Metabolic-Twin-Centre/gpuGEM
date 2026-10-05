"""Solver-mode variant registry for the S85 alternative-settings experiment.

Answers: does any currently-unused cuOpt solver-mode setting close the ~9-10x
cuOpt/Gurobi runtime gap on S85 (established structural, not objective-specific,
by benchmarks/s85_objectives.py)? Every variant is expressed purely as
**cuopt_kwargs overrides through gpugem.solve's existing per-call override
mechanism -- gpugem/_defaults.py is never touched (spec FR-007).
"""
from __future__ import annotations

from gpugem._deps import require

# id, cuopt_kwargs (empty for baseline -- see research.md R5), rationale, is_baseline
SOLVER_MODE_VARIANTS = [
    {
        "id": "baseline",
        "cuopt_kwargs": {},
        "is_baseline": True,
        "rationale": "gpugem's current shipped large-model defaults (method=PDLP, "
                     "presolve=PaPILO, per_constraint_residual=1), applied by giving no "
                     "overrides at all so this can never silently drift from what "
                     "gpugem._defaults.default_settings actually ships.",
    },
    {
        "id": "methodical1",
        "cuopt_kwargs": {"pdlp_solver_mode": 2},
        "is_baseline": False,
        "rationale": "pdlp_solver_mode=Methodical1: cuOpt describes this PDHG variant as "
                     "'more thorough, better on hard problems, slower per step but fewer "
                     "steps needed' than the default Stable3. Explicitly flagged as "
                     "untested on these microbiome whole-body models in prior "
                     "investigation notes (cuGEM's CUOPT_SETTINGS_REFERENCE.md).",
    },
    {
        "id": "concurrent",
        "cuopt_kwargs": {"method": 0},
        "is_baseline": False,
        "rationale": "method=Concurrent is cuOpt's own actual default (races PDLP, "
                     "DualSimplex, and Barrier in parallel, returns whichever finishes "
                     "first) -- gpugem currently hardcodes method=PDLP-only for large "
                     "models, foreclosing this. If Barrier/DualSimplex would handle S85 "
                     "fine while PDLP struggles, forcing PDLP-only may itself be the "
                     "cause of the slowdown.",
    },
    {
        "id": "barrier_cold",
        "cuopt_kwargs": {"method": 3},
        "is_baseline": False,
        "rationale": "method=Barrier (GPU interior-point via cuDSS), run cold with no "
                     "warm start since warm-starting is confirmed broken in cuOpt 26.6.0. "
                     "Theoretically more tolerant of ill-conditioning than PDLP -- "
                     "plausibly why Gurobi's own barrier method doesn't suffer the same "
                     "slowdown -- but never explicitly tested on these models.",
    },
]


def validate_variants():
    """Raise ValueError if SOLVER_MODE_VARIANTS violates data-model.md's rules."""
    ids = [v["id"] for v in SOLVER_MODE_VARIANTS]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate variant id(s) in SOLVER_MODE_VARIANTS: %s" % ids)

    baselines = [v for v in SOLVER_MODE_VARIANTS if v["is_baseline"]]
    if len(baselines) != 1:
        raise ValueError("expected exactly one is_baseline=True entry, found %d" % len(baselines))

    require("cuopt")   # guided DependencyError instead of a bare ImportError when it is absent
    from cuopt.linear_programming.solver_settings.solver_settings import (
        get_solver_parameter_names,
    )
    real_names = set(get_solver_parameter_names())
    for v in SOLVER_MODE_VARIANTS:
        bad = [k for k in v["cuopt_kwargs"] if k not in real_names]
        if bad:
            raise ValueError("variant %r uses unknown cuOpt parameter(s): %s" % (v["id"], bad))


def get_variant(variant_id):
    for v in SOLVER_MODE_VARIANTS:
        if v["id"] == variant_id:
            return v
    raise KeyError("unknown solver-mode variant id %r" % variant_id)


if __name__ == "__main__":
    validate_variants()
    print("validated %d solver-mode variants" % len(SOLVER_MODE_VARIANTS))
