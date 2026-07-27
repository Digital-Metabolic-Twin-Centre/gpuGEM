"""Run the cuOpt-vs-Gurobi FBA benchmark and write JSON + aggregated CSV.

Correctness gate (constitution Principle I/II): a solve time is only reported
for a cell that reached a verified-feasible optimal solution -- status optimal,
stoichiometric residual <= --res-tol, and the two solvers' objectives agree.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import platform
import statistics
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from benchmarks import models as M
from benchmarks import solve as SV
from benchmarks import residual as R

RESULTS = HERE / "results"
FIGURES = HERE / "figures"
RESULTS.mkdir(exist_ok=True)
FIGURES.mkdir(exist_ok=True)


def _versions():
    info = {"gpu_name": None, "gurobi_version": None, "cuopt_version": None,
            "python": platform.python_version()}
    try:
        import gurobipy
        info["gurobi_version"] = ".".join(str(x) for x in gurobipy.gurobi.version())
    except Exception:
        pass
    try:
        import cuopt
        info["cuopt_version"] = getattr(cuopt, "__version__", None)
    except Exception:
        pass
    try:
        import subprocess
        out = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                             capture_output=True, text=True, timeout=20)
        info["gpu_name"] = out.stdout.strip().splitlines()[0] if out.stdout.strip() else None
    except Exception:
        pass
    return info


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


def _median(xs):
    return statistics.median(xs) if xs else float("nan")


def run_one(name, reps, time_limit, res_tol, obj_tol, versions):
    t0 = time.perf_counter()
    lp, prov = M.build_lp(name)
    build_s = time.perf_counter() - t0

    import scipy.sparse as sp
    S_eq = sp.csr_matrix(lp["S"])
    b_eq = np.asarray(lp["b"], dtype=np.float64)

    gurobi_reps = _run_solver(SV.solve_gurobi, lp, reps, time_limit, S_eq, b_eq, res_tol)
    cuopt_reps = _run_solver(SV.solve_cuopt, lp, reps, time_limit, S_eq, b_eq, res_tol)

    g_obj = next((r["objective"] for r in gurobi_reps if r["objective"] is not None), None)
    c_obj = next((r["objective"] for r in cuopt_reps if r["objective"] is not None), None)
    obj_agree = R.objectives_agree(g_obj, c_obj, tol=obj_tol)

    g_feas = all(r["feasible"] for r in gurobi_reps)
    c_feas = all(r["feasible"] for r in cuopt_reps)
    both_ok = g_feas and c_feas and obj_agree

    result = {
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
    out = RESULTS / (name + ".json")
    out.write_text(json.dumps(result, indent=2))
    tag = "OK" if both_ok else "FAILED"
    print("[%s] %s  gurobi=%.3fs (%s)  cuopt=%.3fs (%s)  obj g=%s c=%s  resid g=%.1e c=%.1e" % (
        tag, name, result["gurobi"]["solve_s_median"], gurobi_reps[0]["status"],
        result["cuopt"]["solve_s_median"], cuopt_reps[0]["status"], g_obj, c_obj,
        max(r["residual_inf"] for r in gurobi_reps), max(r["residual_inf"] for r in cuopt_reps)))
    return result


CSV_COLUMNS = ["model", "scale", "kind", "n_cols", "n_total_rows", "nnz",
               "gurobi_solve_s_median", "gurobi_solve_s_min", "gurobi_solve_s_max",
               "gurobi_obj", "gurobi_status", "gurobi_iters", "gurobi_residual_inf",
               "cuopt_solve_s_median", "cuopt_solve_s_min", "cuopt_solve_s_max",
               "cuopt_obj", "cuopt_status", "cuopt_iters", "cuopt_residual_inf",
               "obj_rel_diff", "both_feasible",
               "gurobi_version", "cuopt_version", "gpu_name"]


def aggregate_csv():
    rows = []
    for name in M.ALL_MODELS:
        p = RESULTS / (name + ".json")
        if not p.exists():
            continue
        d = json.loads(p.read_text())
        prov = d["provenance"]
        g = d["gurobi"]; cu = d["cuopt"]
        rows.append({
            "model": name, "scale": prov["scale"], "kind": prov["kind"],
            "n_cols": prov["n_cols"], "n_total_rows": prov["n_total_rows"], "nnz": prov["nnz"],
            "gurobi_solve_s_median": round(g["solve_s_median"], 4),
            "gurobi_solve_s_min": round(g["solve_s_min"], 4),
            "gurobi_solve_s_max": round(g["solve_s_max"], 4),
            "gurobi_obj": g["objective"], "gurobi_status": g["repeats"][0]["status"],
            "gurobi_iters": g["repeats"][0]["iters"],
            "gurobi_residual_inf": max(r["residual_inf"] for r in g["repeats"]),
            "cuopt_solve_s_median": round(cu["solve_s_median"], 4),
            "cuopt_solve_s_min": round(cu["solve_s_min"], 4),
            "cuopt_solve_s_max": round(cu["solve_s_max"], 4),
            "cuopt_obj": cu["objective"], "cuopt_status": cu["repeats"][0]["status"],
            "cuopt_iters": cu["repeats"][0]["iters"],
            "cuopt_residual_inf": max(r["residual_inf"] for r in cu["repeats"]),
            "obj_rel_diff": d["obj_rel_diff"], "both_feasible": d["both_feasible"],
            "gurobi_version": d["versions"]["gurobi_version"],
            "cuopt_version": d["versions"]["cuopt_version"],
            "gpu_name": d["versions"]["gpu_name"],
        })
    csv_path = RESULTS / "benchmark.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print("wrote", csv_path, "with", len(rows), "rows")
    return csv_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=M.ALL_MODELS)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--time-limit", type=float, default=900.0)
    ap.add_argument("--res-tol", type=float, default=1e-4)
    ap.add_argument("--obj-tol", type=float, default=1e-6)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    versions = _versions()
    names = M.ALL_MODELS if args.all else ([args.model] if args.model else [])
    if not names:
        ap.error("give --model NAME or --all")

    any_failed = False
    for name in names:
        p = RESULTS / (name + ".json")
        if p.exists() and not args.force:
            d = json.loads(p.read_text())
            print("[skip] %s (exists; --force to rerun)  both_feasible=%s" % (name, d.get("both_feasible")))
            any_failed = any_failed or (not d.get("both_feasible", False))
            continue
        res = run_one(name, args.reps, args.time_limit, args.res_tol, args.obj_tol, versions)
        any_failed = any_failed or (not res["both_feasible"])

    aggregate_csv()
    if any_failed:
        print("WARNING: at least one cell failed the correctness gate.")
        sys.exit(2)


if __name__ == "__main__":
    main()
