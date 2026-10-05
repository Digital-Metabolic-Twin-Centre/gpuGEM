"""Measure feasibility residuals RESOLVED BY CONSTRAINT BLOCK for every solver.

Why this exists
---------------
The residuals reported in the manuscript's solver comparison are not measured
over the same rows for every solver:

  * ``residual.feasibility_residual(S, b, v)`` -- used for the cuOpt/gpuGEM and
    Gurobi columns -- sees ONLY the mass-balance rows.
  * ``run_highs_baseline.py`` stacks S and C and measures over ALL rows, so the
    HiGHS column includes the coupling block.

Measured on Harvey, the coupling block dominates HiGHS's error by ~44x
(eq 1.565e-09 vs coupling 6.857e-08) and by ~95x on Harvetta, so the two
columns are not comparable and the published ordering is an artefact of the
row-set mismatch rather than a property of the solvers.

The coupling residual cannot be backfilled from the committed results: no run
has ever persisted a primal vector, and the one configuration that does carry
constraint-block data (``residual_0``'s violation histogram) is binned, is not
the configuration reported in the table, and covers neither the shipped default
nor Gurobi. Hence a fresh solve per configuration.

This runner therefore solves each configuration fresh, records BOTH blocks via
``residual.block_residuals``, and -- unlike every previous runner -- PERSISTS
THE FLUX VECTOR, so any future residual definition can be evaluated offline
without occupying the GPU again.

Requires a GPU for the cuOpt configurations and a Gurobi licence for ``gurobi``.
Pass ``--configs`` to run a subset on machines that have only one of the two.

Usage
-----
    python run_block_residuals.py --models Harvey Harvetta
    python run_block_residuals.py --models S84 --configs shipped_default gurobi
    python run_block_residuals.py --all --time-limit 900
"""
from __future__ import annotations

import argparse
import datetime
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from benchmarks import models as M
from benchmarks import residual as R
from benchmarks import solve as SV
from gpugem._deps import DependencyError

RESULTS = HERE / "results" / "block_residuals"
RESULTS.mkdir(parents=True, exist_ok=True)

CONFIGS = ("shipped_default", "residual_0", "gurobi")


def _solve(model, config, lp, time_limit):
    """Return the solver dict for one configuration. Fluxes included."""
    if config == "shipped_default":
        return SV.solve_cuopt(lp, time_limit=time_limit)
    if config == "gurobi":
        return SV.solve_gurobi(lp, time_limit=time_limit, method=2)
    if config == "residual_0":
        # cuOpt's own default per-row check, overriding gpugem's shipped setting.
        # NOT a recommended configuration -- measured only for the trade-off.
        import gpugem
        res = gpugem.solve(time_limit=time_limit, check_feasibility=True,
                           per_constraint_residual=0, **SV._solver_args(lp))
        return {
            "solver": "cuopt", "solve_s": float(res.wall_time_s),
            "objective": None if res.objective is None else float(res.objective),
            "status": res.status, "iters": res.n_iterations,
            "fluxes": None if res.fluxes is None else np.asarray(res.fluxes, float),
            "settings": dict(res.solver_settings),
            "feasibility": dict(res.feasibility),
        }
    raise ValueError(f"unknown config {config!r}")


def run_one(model, config, lp, prov, time_limit):
    t0 = time.time()
    out = _solve(model, config, lp, time_limit)
    wall = time.time() - t0

    rec = {
        "model": model,
        "configuration": config,
        "solver": out["solver"],
        "status": out["status"],
        "solve_s": out["solve_s"],
        "wall_s": round(wall, 3),
        "iterations": out.get("iters"),
        "objective": out["objective"],
        "time_limit": time_limit,
        "n_cols": int(prov["n_cols"]),
        "n_total_rows": int(prov["n_total_rows"]),
        "objective_pinned": R.objective_pinned_by_bounds(lp),
        "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(
            timespec="seconds"),
    }
    for k in ("settings", "feasibility", "method", "bar_iters", "simplex_iters"):
        if k in out:
            rec[k] = out[k]

    v = out.get("fluxes")
    if v is None:
        rec["residual_blocks"] = None
        rec["residual_inf_eq_only"] = None
        rec["fluxes_file"] = None
        return rec, None

    v = np.asarray(v, dtype=np.float64)
    rec["residual_blocks"] = R.block_residuals(lp, v)

    # Continuity with every published number: the legacy mass-balance-only
    # residual, recomputed here from the same vector. The block split must
    # reproduce it exactly, otherwise the new table cannot be reconciled with
    # the old one and BOTH are suspect -- so this is a hard check, not a log line.
    import scipy.sparse as sp
    legacy = R.feasibility_residual(sp.csr_matrix(lp["S"]),
                                    np.asarray(lp["b"], dtype=np.float64), v)
    rec["residual_inf_eq_only"] = legacy
    blk = rec["residual_blocks"]["eq_max_abs"]
    if not np.isclose(legacy, blk, rtol=1e-12, atol=0.0):
        raise AssertionError(
            f"{model}/{config}: legacy feasibility_residual {legacy:.17e} != "
            f"block-resolved eq_max_abs {blk:.17e}")
    return rec, v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", choices=M.ALL_MODELS)
    ap.add_argument("--all", action="store_true", help="every model in models.ALL_MODELS")
    ap.add_argument("--configs", nargs="+", default=list(CONFIGS), choices=CONFIGS)
    ap.add_argument("--time-limit", type=float, default=900.0)
    ap.add_argument("--force", action="store_true", help="re-solve even if recorded")
    a = ap.parse_args()
    from benchmarks._deps import require_or_exit
    require_or_exit("cuopt", "gurobipy")

    models = list(M.ALL_MODELS) if a.all else (a.models or [])
    if not models:
        ap.error("pass --models or --all")

    env = dict(platform=platform.platform(), python=platform.python_version(),
               time_limit=a.time_limit, configs=list(a.configs))

    for model in models:
        path = RESULTS / f"{model}.json"
        recs = {}
        if path.exists() and not a.force:
            recs = {r["configuration"]: r
                    for r in json.loads(path.read_text()).get("results", [])}

        todo = [c for c in a.configs if c not in recs]
        if not todo:
            print(f"[skip] {model}: all of {a.configs} recorded", flush=True)
            continue

        lp, prov = M.build_lp(model)
        for config in todo:
            print(f"[run ] {model} / {config} (cap {a.time_limit:.0f}s)", flush=True)
            try:
                rec, v = run_one(model, config, lp, prov, a.time_limit)
            except DependencyError:
                raise   # a missing/unlicensed dependency aborts the run; it is not a per-model result
            except Exception as exc:
                # Recorded, not hidden: a missing licence or an OOM must be
                # visibly distinct from a solved-but-inaccurate run.
                recs[config] = dict(model=model, configuration=config,
                                    status="ERROR",
                                    error=f"{type(exc).__name__}: {exc}")
                print(f"[FAIL] {model} / {config}: {type(exc).__name__}: {exc}",
                      flush=True)
                path.write_text(json.dumps(
                    dict(environment=env, results=list(recs.values())), indent=1))
                continue

            if v is not None:
                # Persist the primal vector so no future residual definition
                # needs the GPU again.
                fp = RESULTS / f"fluxes_{model}_{config}.npz"
                np.savez_compressed(fp, fluxes=v)
                rec["fluxes_file"] = fp.name
            recs[config] = rec

            b = rec["residual_blocks"]
            if b is None:
                print(f"[done] {model} / {config}: {rec['status']} -- no primal vector",
                      flush=True)
            else:
                cpl = ("absent" if b["coupling_max_viol"] is None
                       else f"{b['coupling_max_viol']:.3e} ({b['coupling_rows_violated']} rows)")
                print(f"[done] {model} / {config}: {rec['status']} "
                      f"{rec['solve_s']:.3f}s  eq={b['eq_max_abs']:.3e} "
                      f"({b['eq_rows_violated']} rows)  coupling={cpl}", flush=True)

            path.write_text(json.dumps(
                dict(environment=env, results=list(recs.values())), indent=1))

    # Flat CSV for the manuscript table.
    import csv
    rows = []
    for model in models:
        path = RESULTS / f"{model}.json"
        if not path.exists():
            continue
        for r in json.loads(path.read_text())["results"]:
            b = r.get("residual_blocks") or {}
            rows.append({
                "model": r["model"], "configuration": r["configuration"],
                "solver": r.get("solver"), "status": r["status"],
                "solve_s": r.get("solve_s"), "iterations": r.get("iterations"),
                "objective": r.get("objective"),
                "eq_max_abs": b.get("eq_max_abs"),
                "eq_rows_violated": b.get("eq_rows_violated"),
                "coupling_max_viol": b.get("coupling_max_viol"),
                "coupling_rows_violated": b.get("coupling_rows_violated"),
                "all_rows_max_viol": b.get("all_rows_max_viol"),
                "bound_max_viol": b.get("bound_max_viol"),
                "n_eq_rows": b.get("n_eq_rows"),
                "n_coupling_rows": b.get("n_coupling_rows"),
                "objective_pinned": (r.get("objective_pinned") or {}).get("pinned"),
                "fluxes_file": r.get("fluxes_file"),
                "error": r.get("error"),
            })
    if rows:
        csv_path = RESULTS / "block_residuals.csv"
        with csv_path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        print(f"\nwrote {csv_path}", flush=True)


if __name__ == "__main__":
    from benchmarks._deps import run_main
    run_main(main)
