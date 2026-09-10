"""Run the MATLAB vs Python lifted-model runtime & fidelity comparison.

For each of the six in-scope models (e_coli_core, iML1515, Harvey, Harvetta,
S84, S85), runs (or reuses) this project's own Python-side lift+Gurobi
pipeline (_matlab_python_lifting_worker.py) and reads the corresponding
MATLAB-side result -- produced by a temporary script that lives entirely
outside both repos' tracked trees (research.md R8) and is never run by this
script itself. Builds one CrossLanguageComparisonRow per model
(data-model.md) and writes comparison.csv.

See specs/015-matlab-python-lifting-comparison/.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from benchmarks import models as M
from benchmarks import residual as R
from benchmarks._matlab_python_lifting_worker import IN_SCOPE_MODELS

RESULTS = HERE / "results" / "matlab_python_lifting"
RESULTS.mkdir(parents=True, exist_ok=True)
MATLAB_RESULTS_DEFAULT = RESULTS / "matlab"

OBJ_TOL = 1e-6   # spec 013's established objective tolerance (research.md R5)
RES_TOL = 1e-4   # spec 013's established residual tolerance (research.md R5)


def _python_result_path(model):
    return RESULTS / ("python_%s.json" % model)


def run_python_worker(model, lift_big, time_limit, force):
    """Run (or reuse) this model's Python-side PipelineRun. Launched as a
    subprocess -- same isolation precedent as every prior *_worker.py in this
    project -- so a crash on one model cannot take down the rest of the run."""
    out_path = _python_result_path(model)
    if out_path.exists() and not force:
        print("[skip] %s/python (already exists)" % model, flush=True)
        return json.loads(out_path.read_text())

    print("[%s] running python worker (lift_big=%s)..." % (model, lift_big), flush=True)
    proc = subprocess.run(
        [sys.executable, "-m", "benchmarks._matlab_python_lifting_worker",
         "--model", model, "--lift-big", str(lift_big), "--time-limit", str(time_limit)],
        capture_output=True, text=True, cwd=str(HERE.parent))
    if proc.returncode != 0:
        raise RuntimeError(
            "python worker failed for %r (exit %d):\nstdout:\n%s\nstderr:\n%s" % (
                model, proc.returncode, proc.stdout, proc.stderr))
    lines = [l for l in proc.stdout.splitlines() if l.strip()]
    if not lines:
        raise RuntimeError("python worker for %r produced no stdout" % model)
    result = json.loads(lines[-1])
    out_path.write_text(json.dumps(result, indent=2))
    print("[%s] wrote %s" % (model, out_path), flush=True)
    return result


def load_matlab_result(model, matlab_dir):
    """Read this model's already-produced matlab_<model>.json. Never runs
    MATLAB itself (spec FR-009/research.md R8) -- errors clearly if missing."""
    path = Path(matlab_dir) / ("%s.json" % model)
    if not path.exists():
        raise FileNotFoundError(
            "%s not found -- this feature reuses an already-produced MATLAB-side "
            "result (research.md R8); it never runs MATLAB itself. Produce it with "
            "the temporary MATLAB comparison script and copy it into %s first."
            % (path, matlab_dir))
    return json.loads(path.read_text())


def _flux_agrees(matlab_run, python_run, res_tol=RES_TOL, obj_tol=OBJ_TOL):
    ms = matlab_run.get("flux_summary")
    ps = python_run.get("flux_summary")
    if ms is None or ps is None:
        return False
    if ms["residual_inf"] > res_tol or ps["residual_inf"] > res_tol:
        return False
    denom = max(1.0, abs(ms["l2_norm"]), abs(ps["l2_norm"]))
    return abs(ms["l2_norm"] - ps["l2_norm"]) / denom <= obj_tol


def build_comparison_row(model, matlab_run, python_run, obj_tol=OBJ_TOL, res_tol=RES_TOL,
                          n_cols=None):
    """Pure comparison/gating logic (no solving, no file I/O) -- kept separate
    from the orchestration above so it's unit-testable without a live
    MATLAB/Gurobi run (mirrors run_model_lifting_validation.py::build_comparison)."""
    matlab_excluded = bool(matlab_run.get("excluded"))
    python_excluded = bool(python_run.get("excluded"))
    excluded_sides = []
    if matlab_excluded:
        excluded_sides.append("matlab: %s" % matlab_run.get("excluded_reason"))
    if python_excluded:
        excluded_sides.append("python: %s" % python_run.get("excluded_reason"))
    excluded_models = "; ".join(excluded_sides) if excluded_sides else None

    if matlab_excluded or python_excluded:
        status_agrees = objective_agrees = flux_agrees = False
    else:
        status_agrees = matlab_run["status"] == python_run["status"]
        objective_agrees = R.objectives_agree(
            matlab_run["objective"], python_run["objective"], tol=obj_tol)
        flux_agrees = _flux_agrees(matlab_run, python_run, res_tol=res_tol, obj_tol=obj_tol)

    n_aux_matlab = matlab_run.get("n_aux_vars")
    n_aux_python = python_run.get("n_aux_vars")
    aux_vars_match = (
        n_aux_matlab is not None and n_aux_python is not None
        and n_aux_matlab == n_aux_python
    )

    verified_correct = bool(
        not matlab_excluded and not python_excluded
        and status_agrees and objective_agrees and flux_agrees
    )

    return {
        "model": model,
        "n_cols": n_cols,
        "matlab_solve_s": matlab_run.get("solve_s"),
        "python_solve_s": python_run.get("solve_s"),
        "matlab_status": matlab_run.get("status"),
        "python_status": python_run.get("status"),
        "status_agrees": status_agrees,
        "objective_agrees": objective_agrees,
        "flux_agrees": flux_agrees,
        "n_aux_vars_matlab": n_aux_matlab,
        "n_aux_vars_python": n_aux_python,
        "aux_vars_match": aux_vars_match,
        "verified_correct": verified_correct,
        "excluded_models": excluded_models,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", action="append", choices=IN_SCOPE_MODELS,
                     help="repeatable; default: all six in-scope models")
    ap.add_argument("--matlab-results", default=str(MATLAB_RESULTS_DEFAULT))
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--lift-big", type=float, default=1000.0)
    ap.add_argument("--time-limit", type=float, default=900.0)
    args = ap.parse_args()

    models = args.model or list(IN_SCOPE_MODELS)
    rows = []
    for model in models:
        _lp, prov = M.build_lp(model)
        python_run = run_python_worker(model, args.lift_big, args.time_limit, args.force)
        matlab_run = load_matlab_result(model, args.matlab_results)
        row = build_comparison_row(model, matlab_run, python_run,
                                    n_cols=prov["n_cols"])
        tag = "OK" if row["verified_correct"] else "FAILED"
        print("[%s] %s  matlab_s=%s  python_s=%s  status_agrees=%s  objective_agrees=%s  "
              "flux_agrees=%s" % (
                  tag, model, row["matlab_solve_s"], row["python_solve_s"],
                  row["status_agrees"], row["objective_agrees"], row["flux_agrees"]),
              flush=True)
        rows.append(row)

    df = pd.DataFrame(rows)
    out_path = RESULTS / "comparison.csv"
    df.to_csv(out_path, index=False)
    print("wrote %s" % out_path, flush=True)
    return df


if __name__ == "__main__":
    main()
