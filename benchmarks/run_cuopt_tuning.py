"""Run the cuOpt-native settings-tuning investigation on S85.

Systematically sweeps cuOpt's documented, LP-relevant solver settings
(benchmarks/cuopt_tuning_candidates.py) against S85 to check whether any purely
cuOpt-native configuration -- ideally one that beats Gurobi outright, the
project's real preferred goal for whole-body/microbiome models, not merely one
that improves on cuOpt's own prior baseline -- closes the gap documented in
specs/004-s85-solver-mode-experiment/ and specs/010-gurobi-default-benchmark/.
Every candidate runs in its own subprocess (research.md R6) so an untested
setting hanging or crashing cannot take down the rest of the sweep.

See specs/012-cuopt-native-tuning/.
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

from benchmarks import aggregate_cuopt_tuning as AG
from benchmarks import cuopt_tuning_candidates as C
from benchmarks import residual as R

RESULTS = HERE / "results" / "cuopt_tuning"
RESULTS.mkdir(parents=True, exist_ok=True)
S85_RESULT = HERE / "results" / "S85.json"


def _gurobi_reference():
    """S85's already-published Gurobi result -- read-only correctness oracle,
    never re-solved by this feature (spec FR-003/FR-006)."""
    d = json.loads(S85_RESULT.read_text())
    return {
        "objective": d["gurobi"]["objective"],
        "solve_s": d["gurobi"]["solve_s_median"],
        "res_tol": d["res_tol"],
        "obj_tol": d["obj_tol"],
    }


def _output_path(candidate_id, cuopt_version):
    if cuopt_version is None:
        return RESULTS / (candidate_id + ".json")
    return RESULTS / ("%s_%s.json" % (candidate_id, cuopt_version))


def _launch_worker(python_exe, candidate_id, time_limit, cuopt_version, timeout_s):
    cmd = [python_exe, "-m", "benchmarks._cuopt_tuning_worker", candidate_id,
           "--time-limit", str(time_limit)]
    if cuopt_version is not None:
        cmd += ["--cuopt-version", cuopt_version]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False,
                               timeout=timeout_s, cwd=str(HERE.parent))
        return proc.returncode, proc.stdout, proc.stderr, False
    except subprocess.TimeoutExpired as e:
        return None, (e.stdout or ""), (e.stderr or ""), True


def run_candidate(candidate_id, python_exe, time_limit, gurobi, cuopt_version=None):
    subprocess_timeout = time_limit * (2 if _needs_two_phases(candidate_id) else 1) + 60.0
    returncode, stdout, stderr, timed_out = _launch_worker(
        python_exe, candidate_id, time_limit, cuopt_version, subprocess_timeout)
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

    candidate = C.get_candidate(candidate_id)
    if worker_result is None:
        reason = "timeout" if timed_out else "crashed"
        print("[%s] DidNotComplete (%s, exit=%s)" % (candidate_id, reason, returncode), flush=True)
        if stderr.strip():
            print(stderr.strip()[-2000:], file=sys.stderr)
        return {
            "id": candidate_id, "user_story": candidate["user_story"],
            "cuopt_version": cuopt_version or "unknown",
            "cuopt_kwargs": candidate["cuopt_kwargs"], "phases": [],
            "status": None, "solve_s": None, "iterations": None, "objective": None,
            "residual_inf": None, "objective_agrees_with_gurobi": False,
            "verified_correct": False, "source_note": candidate["source_note"],
            "error": reason,
        }

    obj = worker_result["objective"]
    resid = worker_result["residual_inf"]
    obj_agrees = R.objectives_agree(obj, gurobi["objective"], tol=gurobi["obj_tol"])
    verified_correct = bool(
        worker_result["status"] == "Optimal"
        and resid is not None and resid <= gurobi["res_tol"]
        and obj_agrees
    )
    # A User Story 3 preprocessing candidate is disqualified outright if its
    # reconstruction failed, regardless of what the ordinary gate says -- speed
    # is never even relevant until reconstruction is proven correct (spec
    # FR-008/SC-003, User Story 3 Acceptance Scenario 2).
    if worker_result.get("reconstruction_verified") is False:
        verified_correct = False

    worker_result["objective_agrees_with_gurobi"] = obj_agrees
    worker_result["verified_correct"] = verified_correct
    worker_result["error"] = None

    tag = "OK" if verified_correct else "UNVERIFIED"
    print("[%s] %s  solve_s=%.3fs  status=%s" % (
        tag, candidate_id, worker_result["solve_s"] or float("nan"), worker_result["status"]),
        flush=True)
    if worker_result.get("reconstruction_verified") is not None:
        note = ("this preprocessing candidate IS viable (reconstruction verified)"
                 if worker_result["reconstruction_verified"]
                 else "this preprocessing candidate is NOT viable (reconstruction failed "
                      "the correctness gate) -- disqualified regardless of speed")
        print("    %s" % note, flush=True)
    return worker_result


def _needs_two_phases(candidate_id):
    return C.get_candidate(candidate_id)["warm_start"]


def _run_ids(ids, python_exe, time_limit, gurobi, force, cuopt_version=None):
    total = len(ids)
    for i, cid in enumerate(ids, start=1):
        out = _output_path(cid, cuopt_version)
        if out.exists() and not force:
            print("[skip] %s (exists; --force to rerun)" % out.name)
            continue
        print("[%d/%d] %s -- launching subprocess (time_limit=%ss)..." % (
            i, total, cid, time_limit), flush=True)
        t0 = time.perf_counter()
        result = run_candidate(cid, python_exe, time_limit, gurobi, cuopt_version=cuopt_version)
        print("[%d/%d] %s -- done in %.1fs wall" % (
            i, total, cid, time.perf_counter() - t0), flush=True)
        out.write_text(json.dumps(result, indent=2))


def run_settings_sweep(time_limit, force):
    gurobi = _gurobi_reference()
    ids = [c["id"] for c in C.CANDIDATES if c["user_story"] == "US1"]
    _run_ids(ids, sys.executable, time_limit, gurobi, force)


def run_baseline_only(time_limit, force):
    gurobi = _gurobi_reference()
    _run_ids(["baseline"], sys.executable, time_limit, gurobi, force)


def run_upgrade_venv(venv_path, time_limit, force):
    venv_path = Path(venv_path)
    python_exe = str(venv_path / "bin" / "python")
    if not Path(python_exe).exists():
        print("ERROR: %s not found -- provision the venv first "
              "(see quickstart.md step 5)" % python_exe, file=sys.stderr)
        sys.exit(2)

    gurobi = _gurobi_reference()
    ids = C.select_upgrade_candidates(RESULTS)
    probe = subprocess.run(
        [python_exe, "-c", "import cuopt; print(cuopt.__version__)"],
        capture_output=True, text=True, check=False)
    if probe.returncode != 0:
        from benchmarks._deps import exit_with
        from gpugem._deps import DependencyError
        exit_with(DependencyError(
            "cuopt", "broken",
            'install it into that environment: %s -m pip install "cuopt-cu12>=26.6.0"' % python_exe,
            purpose="running the tuning candidates in the upgrade environment",
            problem="cannot be imported by %s" % python_exe,
            detail=(probe.stderr.strip().splitlines() or ["no output"])[-1]))
    cuopt_version = probe.stdout.strip()
    _run_ids(ids, python_exe, time_limit, gurobi, force, cuopt_version=cuopt_version)


def run_preprocessing(time_limit, force):
    gurobi = _gurobi_reference()
    ids = [c["id"] for c in C.PREPROCESSING_CANDIDATES]
    if not ids:
        print("no US3 preprocessing candidate registered")
        return
    _run_ids(ids, sys.executable, time_limit, gurobi, force)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", action="store_true")
    ap.add_argument("--settings", action="store_true")
    ap.add_argument("--upgrade-venv", default=None)
    ap.add_argument("--preprocessing", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--time-limit", type=float, default=900.0)
    args = ap.parse_args()

    if not (args.baseline or args.settings or args.upgrade_venv or args.preprocessing or args.all):
        ap.error("give --baseline, --settings, --upgrade-venv PATH, --preprocessing, or --all")

    if args.baseline or args.all:
        run_baseline_only(args.time_limit, args.force)
    if args.settings or args.all:
        run_settings_sweep(args.time_limit, args.force)
    if args.upgrade_venv:
        run_upgrade_venv(args.upgrade_venv, args.time_limit, args.force)
    if args.preprocessing or args.all:
        run_preprocessing(args.time_limit, args.force)

    AG.main()


if __name__ == "__main__":
    main()
