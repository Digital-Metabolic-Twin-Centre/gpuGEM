"""Run the S85 multi-objective cuOpt-vs-Gurobi sweep.

Solves mWBM S85 with both solvers across the ~20 biologically distinct
objectives in benchmarks.s85_objectives.OBJECTIVES (instead of just the one
whole-body objective the 002 cross-scale benchmark used), so the ~10x
cuOpt/Gurobi runtime gap observed there can be judged as representative or
objective-specific. Reuses the same LP builder pattern, solver wrappers, and
correctness gate as benchmarks/run_benchmark.py.
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

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from benchmarks import s85_objectives as O
from benchmarks import solve as SV
from benchmarks import residual as R
from benchmarks import aggregate_sweep as AG

RESULTS = O.RESULTS_DIR
RESULTS.mkdir(parents=True, exist_ok=True)


def _versions():
    return environment_info(gpu=True)


def _median(xs):
    return statistics.median(xs) if xs else float("nan")


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
        feasible = (r["status"] in ("Optimal",) and r["objective"] is not None and resid <= res_tol)
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


def solve_objective(objective, reps, time_limit, res_tol, obj_tol, versions,
                     index=1, total=1, heartbeat_s=30.0):
    """Solve S85 with both solvers for one ObjectiveDefinition; write its JSON."""
    label = "[%d/%d] %s (%s)" % (index, total, objective["id"], objective["reaction"])

    t0 = time.perf_counter()
    lp, prov = O.build_lp_for_objective(objective["id"])
    build_s = time.perf_counter() - t0

    import scipy.sparse as sp
    S_eq = sp.csr_matrix(lp["S"])
    b_eq = np.asarray(lp["b"], dtype=np.float64)

    print("%s -- gurobi solving..." % label, flush=True)
    t_g0 = time.perf_counter()
    gurobi_reps = _with_heartbeat(label + " -- gurobi", heartbeat_s, _run_solver,
                                   SV.solve_gurobi, lp, reps, time_limit, S_eq, b_eq, res_tol)
    print("%s -- gurobi done in %.1fs  status=%s" % (
        label, time.perf_counter() - t_g0, gurobi_reps[0]["status"]), flush=True)

    print("%s -- cuopt solving..." % label, flush=True)
    t_c0 = time.perf_counter()
    cuopt_reps = _with_heartbeat(label + " -- cuopt", heartbeat_s, _run_solver,
                                  SV.solve_cuopt, lp, reps, time_limit, S_eq, b_eq, res_tol)
    print("%s -- cuopt done in %.1fs  status=%s" % (
        label, time.perf_counter() - t_c0, cuopt_reps[0]["status"]), flush=True)

    g_obj = next((r["objective"] for r in gurobi_reps if r["objective"] is not None), None)
    c_obj = next((r["objective"] for r in cuopt_reps if r["objective"] is not None), None)
    obj_agree = R.objectives_agree(g_obj, c_obj, tol=obj_tol)

    g_feas = all(r["feasible"] for r in gurobi_reps)
    c_feas = all(r["feasible"] for r in cuopt_reps)
    both_ok = g_feas and c_feas and obj_agree

    result = {
        "objective": objective,
        "provenance": prov,
        "build_s": build_s,
        "reps": reps,
        "time_limit": time_limit,
        "res_tol": res_tol,
        "obj_tol": obj_tol,
        "versions": versions,
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        "gurobi": {"repeats": gurobi_reps,
                   "solve_s_median": _median([r["solve_s"] for r in gurobi_reps]),
                   "solve_s_min": min(r["solve_s"] for r in gurobi_reps),
                   "solve_s_max": max(r["solve_s"] for r in gurobi_reps),
                   "objective": g_obj, "feasible": g_feas},
        "cuopt": {"repeats": cuopt_reps,
                  "solve_s_median": _median([r["solve_s"] for r in cuopt_reps]),
                  "solve_s_min": min(r["solve_s"] for r in cuopt_reps),
                  "solve_s_max": max(r["solve_s"] for r in cuopt_reps),
                  "objective": c_obj, "feasible": c_feas},
        "obj_rel_diff": (None if (g_obj is None or c_obj is None)
                          else abs(g_obj - c_obj) / max(1.0, abs(g_obj), abs(c_obj))),
        "both_feasible": bool(both_ok),
    }
    out = RESULTS / (objective["id"] + ".json")
    out.write_text(json.dumps(result, indent=2))
    tag = "OK" if both_ok else "FAILED"
    g_s, c_s = result["gurobi"]["solve_s_median"], result["cuopt"]["solve_s_median"]
    ratio = (c_s / g_s) if g_s else float("nan")
    print("[%s] %s  gurobi=%.3fs  cuopt=%.3fs  ratio=%.2f  obj g=%s c=%s" % (
        tag, objective["id"], g_s, c_s, ratio, g_obj, c_obj))
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--objective", choices=[o["id"] for o in O.OBJECTIVES])
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--time-limit", type=float, default=900.0)
    ap.add_argument("--res-tol", type=float, default=1e-4)
    ap.add_argument("--obj-tol", type=float, default=1e-6)
    ap.add_argument("--heartbeat-s", type=float, default=30.0)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    from benchmarks._deps import require_or_exit
    require_or_exit("cuopt", "gurobipy")

    O.validate_objectives()
    O.write_objectives_json()

    objectives = O.OBJECTIVES if args.all else (
        [O.get_objective(args.objective)] if args.objective else [])
    if not objectives:
        ap.error("give --objective ID or --all")

    versions = _versions()
    any_failed = False
    total = len(objectives)
    for i, obj in enumerate(objectives, start=1):
        out = RESULTS / (obj["id"] + ".json")
        if out.exists() and not args.force:
            prior = json.loads(out.read_text())
            print("[skip] %s (exists; --force to rerun)  both_feasible=%s" % (
                obj["id"], prior.get("both_feasible")))
            continue
        res = solve_objective(obj, args.reps, args.time_limit, args.res_tol, args.obj_tol,
                               versions, index=i, total=total, heartbeat_s=args.heartbeat_s)
        any_failed = any_failed or (not res["both_feasible"])

    if args.all:
        all_results = AG.load_results()
        summary = AG.summarize(all_results)
        AG.write_summary(all_results, summary)
        print("wrote %s (%d/%d objectives gated)" % (
            AG.SUMMARY_JSON, summary["n_objectives_gated"], summary["n_objectives_total"]))

    if any_failed:
        print("WARNING: at least one objective failed the correctness gate.")
        sys.exit(2)


if __name__ == "__main__":
    from benchmarks._deps import run_main
    run_main(main)
