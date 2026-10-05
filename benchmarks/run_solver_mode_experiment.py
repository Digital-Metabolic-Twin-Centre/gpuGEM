"""Run the S85 alternative solver-mode experiment.

Solves S85's whole-body-objective LP with cuOpt under the current baseline
settings and under three untested variants (pdlp_solver_mode=Methodical1,
method=Concurrent, method=Barrier cold) -- see benchmarks/solver_mode_variants.py
-- to check whether any of them closes the ~9-10x cuOpt/Gurobi gap established as
structural (not objective-specific) by benchmarks/run_objective_sweep.py. Each
variant runs in its own subprocess (research.md R1) so an untested setting hanging
or crashing cannot take down the rest of the experiment.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from benchmarks import aggregate_solver_modes as AG
from benchmarks import residual as R
from benchmarks import s85_objectives as O
from benchmarks import solve as SV
from benchmarks import solver_mode_variants as V

RESULTS = HERE / "results" / "s85_solver_modes"
RESULTS.mkdir(parents=True, exist_ok=True)


def _solve_gurobi_reference(time_limit):
    """Solve S85's whole-body objective once with Gurobi -- the shared correctness
    reference for every cuOpt variant (research R6: not re-solved per variant,
    since Gurobi's result doesn't depend on cuOpt's settings)."""
    lp, _ = O.build_lp_for_objective("whole_body")
    print("[gurobi] reference solve (time_limit=%ss)..." % time_limit, flush=True)
    r = SV.solve_gurobi(lp, time_limit=time_limit)
    print("[gurobi] reference solve: %.1fs  objective=%s  status=%s" % (
        r["solve_s"], r["objective"], r["status"]), flush=True)
    return r["objective"]


def _run_variant_subprocess(variant, time_limit, subprocess_timeout):
    """Launch the worker subprocess for one variant.

    Returns (returncode, stdout, stderr, timed_out). On a timeout, subprocess.run
    kills the process itself; returncode is None and timed_out is True (research
    R3/R4 -- distinct from a clean crash so the two are never conflated)."""
    cmd = [sys.executable, "-m", "benchmarks._solver_mode_worker", variant["id"],
           "--time-limit", str(time_limit)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False,
                               timeout=subprocess_timeout)
        return proc.returncode, proc.stdout, proc.stderr, False
    except subprocess.TimeoutExpired as e:
        stdout = e.stdout or ""
        stderr = e.stderr or ""
        return None, stdout, stderr, True


def run_variant(variant, time_limit, gurobi_objective, obj_tol, res_tol):
    subprocess_timeout = time_limit + 60.0
    returncode, stdout, stderr, timed_out = _run_variant_subprocess(
        variant, time_limit, subprocess_timeout)
    from benchmarks._deps import propagate_dependency_exit
    propagate_dependency_exit(returncode, stderr)

    worker_result = None
    if returncode == 0:
        lines = [ln for ln in stdout.splitlines() if ln.strip()]
        if lines:
            try:
                worker_result = json.loads(lines[-1])
            except json.JSONDecodeError:
                worker_result = None

    if worker_result is None:
        reason = "timeout" if timed_out else "crashed"
        result = {
            "variant": variant,
            "provenance": None,
            "outcome": "DidNotComplete",
            "outcome_reason": reason,
            "subprocess_exit_code": returncode,
            "solve_s": None, "status": None, "solved_by": None, "iters": None,
            "objective": None, "residual_inf": None,
            "gurobi_objective": gurobi_objective, "obj_rel_diff": None,
            "verified_correct": False,
            "time_limit": time_limit, "subprocess_timeout": subprocess_timeout,
        }
        print("[%s] DidNotComplete (%s, exit=%s) -- see stderr below" % (
            variant["id"], reason, returncode), flush=True)
        if stderr.strip():
            print(stderr.strip()[-2000:], file=sys.stderr)
        return result

    obj = worker_result["objective"]
    obj_rel_diff = (None if obj is None
                     else abs(obj - gurobi_objective) / max(1.0, abs(obj), abs(gurobi_objective)))
    resid = worker_result["residual_inf"]
    obj_agree = R.objectives_agree(obj, gurobi_objective, tol=obj_tol)
    verified_correct = bool(
        worker_result["status"] == "Optimal"
        and resid is not None and resid <= res_tol
        and obj_agree
    )

    result = {
        "variant": variant,
        "provenance": worker_result.get("provenance"),
        "outcome": "Completed",
        "outcome_reason": None,
        "subprocess_exit_code": returncode,
        "solve_s": worker_result["solve_s"],
        "status": worker_result["status"],
        "solved_by": worker_result["solved_by"],
        "iters": worker_result["iters"],
        "objective": obj,
        "residual_inf": resid,
        "gurobi_objective": gurobi_objective,
        "obj_rel_diff": obj_rel_diff,
        "verified_correct": verified_correct,
        "time_limit": time_limit,
        "subprocess_timeout": subprocess_timeout,
    }
    tag = "OK" if verified_correct else "UNVERIFIED"
    print("[%s] %s  solve_s=%.3fs  status=%s  solved_by=%s" % (
        tag, variant["id"], result["solve_s"], result["status"], result["solved_by"]), flush=True)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--time-limit", type=float, default=900.0)
    ap.add_argument("--res-tol", type=float, default=1e-4)
    ap.add_argument("--obj-tol", type=float, default=1e-6)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    from benchmarks._deps import require_or_exit
    require_or_exit("cuopt", "gurobipy")

    V.validate_variants()
    gurobi_objective = _solve_gurobi_reference(args.time_limit)

    total = len(V.SOLVER_MODE_VARIANTS)
    baseline_failed = False
    for i, variant in enumerate(V.SOLVER_MODE_VARIANTS, start=1):
        out = RESULTS / (variant["id"] + ".json")
        if out.exists() and not args.force:
            prior = json.loads(out.read_text())
            print("[skip] %s (exists; --force to rerun)  outcome=%s" % (
                variant["id"], prior.get("outcome")))
            if variant["is_baseline"] and not prior.get("verified_correct"):
                baseline_failed = True
            continue

        print("[%d/%d] %s -- launching subprocess (time_limit=%ss)..." % (
            i, total, variant["id"], args.time_limit), flush=True)
        t0 = time.perf_counter()
        result = run_variant(variant, args.time_limit, gurobi_objective, args.obj_tol, args.res_tol)
        print("[%d/%d] %s -- done in %.1fs wall" % (
            i, total, variant["id"], time.perf_counter() - t0), flush=True)

        out.write_text(json.dumps(result, indent=2))
        if variant["is_baseline"] and not result["verified_correct"]:
            baseline_failed = True

    all_results = AG.load_results()
    summary = AG.summarize(all_results)
    AG.write_summary(all_results, summary)
    print("wrote %s (%d/%d variants present)" % (
        AG.SUMMARY_JSON, len(all_results), total))
    if summary["best_candidate_id"]:
        print("best candidate: %s  (%.2fx speedup vs baseline)" % (
            summary["best_candidate_id"], summary["best_candidate_speedup"]))
    else:
        print("no candidate beat the baseline while remaining verified-correct")

    if baseline_failed:
        print("ERROR: baseline variant did not complete/verify -- something is wrong with the "
              "experiment setup itself (not just a candidate not panning out).")
        sys.exit(1)


if __name__ == "__main__":
    from benchmarks._deps import run_main
    run_main(main)
