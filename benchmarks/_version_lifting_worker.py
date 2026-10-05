"""Subprocess entry point for one (model, lift-state) combination.

Never invoked directly by a user -- launched by run_version_lifting_comparison.py
under either the shared environment's interpreter (current cuOpt version) or the
isolated venv's interpreter (newer cuOpt version), so a hang or crash on one
combination cannot take down the rest of the run (same subprocess-isolation
precedent as specs/004-, specs/012-, specs/013-).

Model-agnostic (works for any of the six in-scope models, unlike
specs/012-cuopt-native-tuning/'s S85-only worker) -- reuses gpugem.solve's
existing lift/lift_big parameters exactly as specs/013-cobra-model-lifting/
already implemented them, no new gpugem surface.

cuOpt's own logging writes to the OS-level stdout file descriptor directly, so
it cannot be cleanly separated from this script's own output by reassigning
sys.stdout. Instead, this script guarantees its one JSON result is the *last*
line written to stdout; the orchestrator parses only the final non-empty line.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sp

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from benchmarks import models as M
from benchmarks import residual as R

IN_SCOPE_MODELS = ["e_coli_core", "iML1515", "Harvey", "Harvetta", "S84", "S85"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=IN_SCOPE_MODELS)
    ap.add_argument("--lift", dest="lift", action="store_true")
    ap.add_argument("--no-lift", dest="lift", action="store_false")
    ap.set_defaults(lift=False)
    ap.add_argument("--lift-big", type=float, default=1000.0)
    ap.add_argument("--time-limit", type=float, default=900.0)
    args = ap.parse_args()
    from benchmarks._deps import require_or_exit
    require_or_exit("cuopt")

    lp, _prov = M.build_lp(args.model)
    S = sp.csr_matrix(lp["S"])
    b = np.asarray(lp["b"], dtype=np.float64)

    import gpugem

    kwargs = dict(time_limit=args.time_limit)
    if args.lift:
        kwargs.update(lift=True, lift_big=args.lift_big)
    res = gpugem.solve(**lp, **kwargs)

    residual_inf = R.feasibility_residual(S, b, res.fluxes)

    from benchmarks._deps import optional_version
    cuopt_version, _cuopt_reason = optional_version("cuopt")   # cuopt was required above

    result = {
        "model": args.model,
        "cuopt_version": cuopt_version,
        "lifted": args.lift,
        "solve_s": float(res.wall_time_s),
        "status": res.status,
        "objective": None if res.objective is None else float(res.objective),
        "residual_inf": residual_inf,
        "iterations": res.n_iterations,
    }
    print(json.dumps(result))


if __name__ == "__main__":
    from benchmarks._deps import run_main
    run_main(main)
