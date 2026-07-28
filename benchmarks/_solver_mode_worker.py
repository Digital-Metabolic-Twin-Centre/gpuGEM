"""Subprocess entry point for one S85 solver-mode variant.

Never invoked directly by a user -- launched by run_solver_mode_experiment.py as
`python -m benchmarks._solver_mode_worker <variant_id> --time-limit SECONDS` so a
hang, crash, or OOM in cuOpt under an untested setting (Concurrent, cold Barrier)
cannot take down the orchestrator or the other variants (see
specs/004-s85-solver-mode-experiment/research.md R1).

cuOpt's own logging writes to the OS-level stdout file descriptor directly (native
C++ output, bypassing Python's ``sys.stdout``), so it cannot be cleanly separated
from this script's own output by reassigning ``sys.stdout``. Instead, this script
guarantees its one JSON result is the *last* line written to stdout; the
orchestrator parses only the final non-empty line of the subprocess's captured
stdout.
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

from benchmarks import residual as R
from benchmarks import s85_objectives as O
from benchmarks import solver_mode_variants as V


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("variant_id", choices=[v["id"] for v in V.SOLVER_MODE_VARIANTS])
    ap.add_argument("--time-limit", type=float, default=900.0)
    args = ap.parse_args()

    variant = V.get_variant(args.variant_id)
    lp, prov = O.build_lp_for_objective("whole_body")

    S_eq = sp.csr_matrix(lp["S"])
    b_eq = np.asarray(lp["b"], dtype=np.float64)

    import gpugem

    solver_args = {k: lp[k] for k in ("S", "b", "lb", "ub", "c", "maximize") if k in lp}
    for k in ("C", "d_lb", "d_ub"):
        if lp.get(k) is not None:
            solver_args[k] = lp[k]

    res = gpugem.solve(
        time_limit=args.time_limit,
        check_feasibility=True,
        **solver_args,
        **variant["cuopt_kwargs"],
    )

    resid = R.feasibility_residual(S_eq, b_eq, res.fluxes)

    result = {
        "solve_s": float(res.wall_time_s),
        "status": res.status,
        "solved_by": res.solved_by,
        "iters": res.n_iterations,
        "objective": None if res.objective is None else float(res.objective),
        "residual_inf": resid,
        "provenance": prov,
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
