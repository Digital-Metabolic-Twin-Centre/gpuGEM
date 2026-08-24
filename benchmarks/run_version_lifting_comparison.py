"""Run the version x lifting runtime comparison.

For six models (e_coli_core, iML1515, Harvey, Harvetta, S84, S85), measures
cuOpt's runtime under all four combinations of {current version, newer
version} x {unlifted, lifted}, reusing already-published results wherever
they exist (specs/002-benchmark-cuopt-gurobi/'s benchmark.csv for
current-version-unlifted; specs/013-cobra-model-lifting/'s model_lifting/
results for e_coli_core/S85's current-version-lifted) and solving only the
combinations that don't already exist.

See specs/014-version-lifting-runtime-comparison/.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from benchmarks import aggregate_version_lifting_comparison as AG
from benchmarks._version_lifting_worker import IN_SCOPE_MODELS

RESULTS = HERE / "results" / "version_lifting"
RESULTS.mkdir(parents=True, exist_ok=True)

BENCHMARK_CSV = HERE / "results" / "benchmark.csv"
# specs/013-cobra-model-lifting/'s own run_model_lifting_validation.py wrote
# its results under this repo's benchmarks/results/model_lifting/ directly
# (not nested under specs/013-.../) -- confirmed directly (research.md R3).
MODEL_LIFTING_DIR = HERE / "results" / "model_lifting"

DEFAULT_VENV = Path("/tmp/cuopt-26.8-venv")
NEW_VERSION_PIN = "cuopt-cu12==26.8.0"


def _old_version_unlifted_exists(model):
    if not BENCHMARK_CSV.exists():
        return False
    df = pd.read_csv(BENCHMARK_CSV)
    return (df["model"] == model).any()


def _old_version_lifted_exists(model):
    return (MODEL_LIFTING_DIR / (model + ".json")).exists()


def missing_combinations(model):
    """Return the list of (version, lifted) tags this model still needs
    solving, per research.md R3's exact accounting."""
    missing = []
    # current-version-unlifted: always already exists (benchmark.csv covers
    # every model in the registry) -- never re-solved (spec FR-007).
    if not _old_version_unlifted_exists(model):
        missing.append(("old", False))
    missing.append(("new", False))
    if not _old_version_lifted_exists(model):
        missing.append(("old", True))
    missing.append(("new", True))
    return missing


def ensure_venv(venv_path=DEFAULT_VENV):
    python_exe = venv_path / "bin" / "python"
    needs_create = not python_exe.exists()
    if not needs_create:
        out = subprocess.run(
            [str(python_exe), "-c", "import cuopt; print(cuopt.__version__)"],
            capture_output=True, text=True, check=False,
        )
        if out.returncode != 0 or not out.stdout.strip():
            needs_create = True
    if needs_create:
        print("provisioning isolated venv at %s (research.md R4)..." % venv_path, flush=True)
        subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
        subprocess.run(
            [str(python_exe), "-m", "pip", "install", "--quiet",
             NEW_VERSION_PIN, "numpy", "scipy"],
            check=True,
        )
    # This feature also needs cobra for the two BiGG-format in-scope models
    # (e_coli_core, iML1515) -- specs/012-cuopt-native-tuning/'s original
    # provisioning only needed numpy/scipy since it was S85-only (.mat
    # format). Installed idempotently; a no-op if already present.
    out = subprocess.run([str(python_exe), "-c", "import cobra"],
                          capture_output=True, text=True, check=False)
    if out.returncode != 0:
        print("installing cobra into the isolated venv...", flush=True)
        subprocess.run([str(python_exe), "-m", "pip", "install", "--quiet", "cobra"],
                        check=True)
    return str(python_exe)


def _launch_worker(python_exe, model, lift, time_limit):
    cmd = [python_exe, "-m", "benchmarks._version_lifting_worker",
           "--model", model, "--lift" if lift else "--no-lift",
           "--time-limit", str(time_limit)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False,
                               timeout=time_limit + 60.0, cwd=str(HERE.parent))
        return proc.returncode, proc.stdout, proc.stderr, False
    except subprocess.TimeoutExpired as e:
        return None, (e.stdout or ""), (e.stderr or ""), True


def solve_combination(model, version_tag, lift, python_exe, time_limit):
    returncode, stdout, stderr, timed_out = _launch_worker(python_exe, model, lift, time_limit)
    if returncode == 0:
        lines = [ln for ln in stdout.splitlines() if ln.strip()]
        if lines:
            try:
                result = json.loads(lines[-1])
                result["version_tag"] = version_tag
                return result
            except json.JSONDecodeError:
                pass
    reason = "timeout" if timed_out else "crashed"
    print("[%s/%s/%s] DidNotComplete (%s, exit=%s)" % (
        model, version_tag, "lifted" if lift else "unlifted", reason, returncode), flush=True)
    if stderr.strip():
        print(stderr.strip()[-2000:], file=sys.stderr)
    return {
        "model": model, "version_tag": version_tag, "lifted": lift,
        "cuopt_version": None, "solve_s": None, "status": None,
        "objective": None, "residual_inf": None, "iterations": None,
        "error": reason,
    }


def run_model(model, force, time_limit, venv_path=DEFAULT_VENV):
    out_path = RESULTS / (model + ".json")
    existing = json.loads(out_path.read_text()) if out_path.exists() else {}

    missing = missing_combinations(model)
    if not missing:
        print("[skip] %s (nothing new needed -- current-version-unlifted and "
              "current-version-lifted both already published)" % model, flush=True)
        return existing

    needs_new_version = any(v == "new" for v, _ in missing)
    python_exe_new = ensure_venv(venv_path) if needs_new_version else None

    for version_tag, lift in missing:
        key = "%s_%s" % (version_tag, "lifted" if lift else "unlifted")
        if key in existing and not force:
            print("[skip] %s/%s (exists; --force to rerun)" % (model, key), flush=True)
            continue
        python_exe = python_exe_new if version_tag == "new" else sys.executable
        print("[%s/%s] solving (time_limit=%ss)..." % (model, key, time_limit), flush=True)
        t0 = time.perf_counter()
        result = solve_combination(model, version_tag, lift, python_exe, time_limit)
        print("[%s/%s] done in %.1fs wall  status=%s" % (
            model, key, time.perf_counter() - t0, result.get("status")), flush=True)
        existing[key] = result
        out_path.write_text(json.dumps(existing, indent=2))

    return existing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", action="append", choices=IN_SCOPE_MODELS,
                     help="repeatable; default: all six in-scope models")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--time-limit", type=float, default=900.0)
    ap.add_argument("--venv", default=str(DEFAULT_VENV))
    args = ap.parse_args()

    models = args.model or IN_SCOPE_MODELS
    for model in models:
        run_model(model, args.force, args.time_limit, venv_path=Path(args.venv))

    AG.main()


if __name__ == "__main__":
    main()
