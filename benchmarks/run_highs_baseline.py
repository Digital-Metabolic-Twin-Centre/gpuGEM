#!/usr/bin/env python3
"""HiGHS open-source CPU baseline for gpuGEM, under the project's correctness gate.

Builds each LP with the repo's own loader (gpugem.loaders via benchmarks.models.build_lp)
so the problem solved is byte-identical to the one given to cuOpt and Gurobi:
native two-sided row bounds, objective overridden to the registry's named reaction,
sense forced to maximise where the registry says so.

Usage:
    python run_highs_baseline.py --repo /path/to/gpuGEM --models S23 S83 \
        --time-limit 14400 --threads 1 --out highs_baseline.json
"""
import datetime
import argparse, json, os, pathlib, platform, sys, time
import numpy as np
import scipy.sparse as sp


def build_arrays(lp):
    """Return (A, row_lower, row_upper, col_lower, col_upper, cost, maximize)."""
    import highspy
    INF = highspy.kHighsInf
    S = sp.csr_matrix(lp["S"])
    b = np.asarray(lp["b"], float).ravel()
    rows, rlo, rhi = [S], [b.copy()], [b.copy()]
    if lp.get("C") is not None:
        C = sp.csr_matrix(lp["C"])
        dlo = np.asarray(lp["d_lb"], float).ravel()
        dhi = np.asarray(lp["d_ub"], float).ravel()
        rows.append(C)
        rlo.append(np.where(np.isfinite(dlo), dlo, -INF))
        rhi.append(np.where(np.isfinite(dhi), dhi, INF))
    A = sp.csr_matrix(sp.vstack(rows, format="csr"))
    lo = np.asarray(lp["lb"], float).ravel()
    hi = np.asarray(lp["ub"], float).ravel()
    return (A, np.concatenate(rlo), np.concatenate(rhi),
            np.where(np.isfinite(lo), lo, -INF), np.where(np.isfinite(hi), hi, INF),
            np.asarray(lp["c"], float).ravel(), bool(lp["maximize"]))


def residual_inf(A, rlo, rhi, x):
    """Max violation of the two-sided row system (0 where within bounds)."""
    Ax = A @ x
    lo_v = np.where(np.isfinite(rlo), rlo - Ax, -np.inf)
    hi_v = np.where(np.isfinite(rhi), Ax - rhi, -np.inf)
    return float(max(np.max(lo_v), np.max(hi_v), 0.0))


def _highs_version():
    """highspy exposes no __version__; ask a Highs instance."""
    import highspy
    h = highspy.Highs()
    for attr in ("version", "versionMajor"):
        if hasattr(h, attr):
            try:
                if attr == "version":
                    v = h.version()
                    if v:
                        return str(v)
                else:
                    return ".".join(str(getattr(h, a)())
                                    for a in ("versionMajor", "versionMinor", "versionPatch")
                                    if hasattr(h, a))
            except Exception:
                pass
    return "unknown"


def _load_snapshot():
    """Machine load at this instant -- this host is shared."""
    import os
    try:
        l1, l5, l15 = os.getloadavg()
        return {"load1": round(l1, 2), "load5": round(l5, 2), "load15": round(l15, 2),
                "cpu_count": os.cpu_count()}
    except Exception:
        return {}


def run_one(name, time_limit, threads, log_dir):
    import highspy
    from models import build_lp

    t0 = time.time()
    lp, prov = build_lp(name)
    t_build = time.time() - t0

    A, rlo, rhi, clo, chi, cost, maximize = build_arrays(lp)
    h = highspy.Highs()
    h.setOptionValue("time_limit", float(time_limit))
    h.setOptionValue("output_flag", True)
    h.setOptionValue("log_file", str(pathlib.Path(log_dir) / f"highs_{name}.log"))
    h.setOptionValue("log_to_console", False)
    if threads:
        h.setOptionValue("threads", int(threads))

    h.addVars(A.shape[1], clo, chi)
    h.changeColsCost(A.shape[1], np.arange(A.shape[1], dtype=np.int32), cost)
    h.addRows(A.shape[0], rlo, rhi, A.nnz,
              A.indptr.astype(np.int32), A.indices.astype(np.int32), A.data)
    h.changeObjectiveSense(
        highspy.ObjSense.kMaximize if maximize else highspy.ObjSense.kMinimize)

    t0 = time.time()
    h.run()
    t_solve = time.time() - t0

    status = str(h.getModelStatus()).split(".")[-1]
    info = h.getInfo()
    rec = dict(model=name, n_cols=int(prov["n_cols"]),
               n_total_rows=int(prov["n_total_rows"]), maximize=maximize,
               build_s=round(t_build, 3), solve_s=round(t_solve, 3),
               status=status, time_limit_s=time_limit, threads=threads,
               simplex_iterations=int(getattr(info, "simplex_iteration_count", -1)))
    if status == "kOptimal":
        x = np.asarray(h.getSolution().col_value, float)
        rec["objective"] = float(h.getObjectiveValue())
        rec["residual_inf"] = residual_inf(A, rlo, rhi, x)
    else:
        rec["objective"] = None
        rec["residual_inf"] = None
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--time-limit", type=float, default=14400.0)
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--out", default="highs_baseline.json")
    ap.add_argument("--log-dir", default=".")
    a = ap.parse_args()

    sys.path.insert(0, a.repo)
    sys.path.insert(0, os.path.join(a.repo, "benchmarks"))
    pathlib.Path(a.log_dir).mkdir(parents=True, exist_ok=True)

    import highspy
    env = dict(platform=platform.platform(), processor=platform.processor(),
               python=platform.python_version(),
               highs_version=_highs_version(),
               cpu_count=os.cpu_count(), threads_requested=a.threads)

    out_path = pathlib.Path(a.out)
    results = []
    if out_path.exists():                      # resume-safe
        prev = json.loads(out_path.read_text())
        results = prev.get("results", [])
        done = {r["model"] for r in results}
    else:
        done = set()

    for nm in a.models:
        if nm in done:
            print(f"[skip] {nm} already recorded", flush=True)
            continue
        print(f"[run ] {nm} (cap {a.time_limit:.0f}s, {a.threads} thread(s))", flush=True)
        _load_before = _load_snapshot()
        _t_wall0 = time.time()
        try:
            rec = run_one(nm, a.time_limit, a.threads, a.log_dir)
        except Exception as exc:                # OOM / loader failure recorded, not hidden
            rec = dict(model=nm, status="ERROR", error=f"{type(exc).__name__}: {exc}")
        rec["load_before"] = _load_before
        rec["load_after"] = _load_snapshot()
        rec["wall_s"] = round(time.time() - _t_wall0, 3)
        rec["started_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat(
            timespec="seconds")
        results.append(rec)
        # sidecar: a kill loses at most the model in flight
        (pathlib.Path(a.log_dir) / f"result_{nm}.json").write_text(
            json.dumps(rec, indent=1))
        print(f"[done] {rec.get('model')}: {rec.get('status')} "
              f"{rec.get('solve_s')}s obj={rec.get('objective')}", flush=True)
        out_path.write_text(json.dumps(dict(environment=env, results=results), indent=1))

    print(json.dumps(dict(environment=env, results=results), indent=1))


if __name__ == "__main__":
    main()

