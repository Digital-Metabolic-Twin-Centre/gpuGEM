"""Run the cross-model objective-panel credibility benchmark.

For every model already covered by the main cross-scale benchmark, solves
every objective reaction listed in that model's already-curated
benchmarks/objective_candidates/<model>.csv panel, with both solvers exactly
as already published for that model (never a different setting), repeated
and reported as medians. Answers: is the one number already published per
model (its single shipped/whole-body objective) representative of that
model's broader, biologically diverse objective panel, or an outlier?

See specs/011-objective-panel-benchmark/.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import platform
import statistics
import sys
import threading
import time
from pathlib import Path

import numpy as np
import scipy.sparse as sp

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from benchmarks import aggregate_objective_panel as AG
from benchmarks import models as M
from benchmarks import objective_panel as OP
from benchmarks import residual as R
from benchmarks import solve as SV

RESULTS = HERE / "results" / "objective_panel"
RESULTS.mkdir(parents=True, exist_ok=True)


def _median(xs):
    return statistics.median(xs) if xs else float("nan")


def _versions():
    return environment_info(gpu=False)


def _with_heartbeat(label, heartbeat_s, fn, *args, **kwargs):
    """Run a blocking call, printing an elapsed-time line every heartbeat_s
    seconds while it runs, so a long solve is distinguishable from a hang."""
    stop = threading.Event()
    t0 = time.perf_counter()

    def _beat():
        while not stop.wait(heartbeat_s):
            print("    ...%s still solving, %ds elapsed" % (label, int(time.perf_counter() - t0)),
                  flush=True)

    thread = threading.Thread(target=_beat, daemon=True)
    thread.start()
    try:
        return fn(*args, **kwargs)
    finally:
        stop.set()
        thread.join(timeout=1.0)


def _run_solver(fn, lp, reps, time_limit, S_eq, b_eq, res_tol):
    reps_out = []
    for i in range(reps):
        r = fn(lp, time_limit=time_limit)
        resid = R.feasibility_residual(S_eq, b_eq, r.get("fluxes"))
        feasible = (r["status"] == "Optimal" and r["objective"] is not None and resid <= res_tol)
        reps_out.append({
            "repeat": i,
            "solve_s": r["solve_s"],
            "objective": r["objective"],
            "status": r["status"],
            "iters": r["iters"],
            "residual_inf": resid,
            "feasible": bool(feasible),
        })
    return reps_out


def _summarize_solver(reps_out):
    objs = [r["objective"] for r in reps_out if r["objective"] is not None]
    return {
        "repeats": reps_out,
        "solve_s_median": _median([r["solve_s"] for r in reps_out]),
        "objective_median": _median(objs) if objs else None,
        "residual_inf_median": _median([r["residual_inf"] for r in reps_out]),
        "iters_median": _median([r["iters"] for r in reps_out if r["iters"] is not None]),
        "status": reps_out[0]["status"],
        # correctness gate: every individual repeat must pass, never the
        # median alone (research R7) -- a good median residual does not
        # excuse one bad repeat.
        "feasible": all(r["feasible"] for r in reps_out),
    }


def solve_one_objective(model, reaction_id, category, settings, reps, versions,
                         index=1, total=1, heartbeat_s=30.0):
    """Solve `model` with both solvers for one objective reaction; return its
    ObjectivePanelResult dict (data-model.md)."""
    label = "[%d/%d] %s/%s" % (index, total, model, reaction_id)

    t0 = time.perf_counter()
    lp, prov = OP._build_lp_with_objective(model, reaction_id)
    build_s = time.perf_counter() - t0

    S_eq = sp.csr_matrix(lp["S"])
    b_eq = np.asarray(lp["b"], dtype=np.float64)
    time_limit, res_tol, obj_tol = settings["time_limit"], settings["res_tol"], settings["obj_tol"]

    print("%s -- gurobi solving..." % label, flush=True)
    gurobi_reps = _with_heartbeat(label + " -- gurobi", heartbeat_s, _run_solver,
                                   SV.solve_gurobi, lp, reps, time_limit, S_eq, b_eq, res_tol)
    print("%s -- gurobi done  status=%s" % (label, gurobi_reps[0]["status"]), flush=True)

    print("%s -- cuopt solving..." % label, flush=True)
    cuopt_reps = _with_heartbeat(label + " -- cuopt", heartbeat_s, _run_solver,
                                  SV.solve_cuopt, lp, reps, time_limit, S_eq, b_eq, res_tol)
    print("%s -- cuopt done  status=%s" % (label, cuopt_reps[0]["status"]), flush=True)

    gurobi = _summarize_solver(gurobi_reps)
    cuopt = _summarize_solver(cuopt_reps)

    obj_agree = R.objectives_agree(gurobi["objective_median"], cuopt["objective_median"], tol=obj_tol)
    both_feasible = bool(gurobi["feasible"] and cuopt["feasible"] and obj_agree)

    result = {
        "model": model,
        "objective_id": reaction_id,
        "reaction_id": reaction_id,
        "category": category,
        "build_s": build_s,
        "reps": reps,
        "time_limit": time_limit,
        "res_tol": res_tol,
        "obj_tol": obj_tol,
        "versions": versions,
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        "gurobi": gurobi,
        "cuopt": cuopt,
        "obj_agree_with_cuopt": obj_agree,
        "both_feasible": both_feasible,
    }
    tag = "OK" if both_feasible else "FAILED"
    print("[%s] %s  gurobi=%.3fs  cuopt=%.3fs" % (
        tag, label, gurobi["solve_s_median"], cuopt["solve_s_median"]))
    return result


def run_model(model, reps, force, heartbeat_s, versions):
    out_dir = RESULTS / model
    out_dir.mkdir(parents=True, exist_ok=True)

    panel = OP._load_panel(model)
    settings = OP._load_settings(model)
    total = len(panel)

    for i, entry in enumerate(panel, start=1):
        objective_id = entry["reaction_id"]
        out = out_dir / (objective_id + ".json")
        if out.exists() and not force:
            print("[skip] %s/%s (exists; --force to rerun)" % (model, objective_id))
            continue
        result = solve_one_objective(model, objective_id, entry["category"], settings, reps,
                                      versions, index=i, total=total, heartbeat_s=heartbeat_s)
        out.write_text(json.dumps(result, indent=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=M.ALL_MODELS)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--heartbeat-s", type=float, default=30.0)
    args = ap.parse_args()
    from benchmarks._deps import require_or_exit
    require_or_exit("cuopt", "gurobipy")

    names = M.ALL_MODELS if args.all else ([args.model] if args.model else [])
    if not names:
        ap.error("give --model NAME or --all")

    versions = _versions()
    for name in names:
        run_model(name, args.reps, args.force, args.heartbeat_s, versions)

    AG.main()


if __name__ == "__main__":
    from benchmarks._deps import run_main
    run_main(main)
