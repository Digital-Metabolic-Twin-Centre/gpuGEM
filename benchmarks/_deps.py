"""Dependency guards for benchmark, figure and example scripts.

``require_or_exit`` is called first thing in a script's ``main()``: a missing dependency then stops
the run with a guided message and exit code 2 *before* any model is read or result written.
``environment_info`` records versions for result metadata; anything unavailable is stored as
``null`` together with ``<field>_unavailable_reason`` instead of being swallowed
(specs/016-missing-dependency-errors/contracts/dependency-errors.md).
"""
from __future__ import annotations

import platform
import subprocess
import sys

from gpugem import _deps
from gpugem._deps import DependencyError

EXIT_DEPENDENCY = 3   # 2 is already used by the benchmarks for a failed correctness gate


def exit_with(err):
    """Print a DependencyError to stderr and exit with EXIT_DEPENDENCY."""
    print(str(err), file=sys.stderr)
    raise SystemExit(EXIT_DEPENDENCY)


def propagate_dependency_exit(returncode, stderr):
    """If a worker subprocess exited because of a missing dependency, stop the whole run.

    Workers exit with EXIT_DEPENDENCY after printing a guided message; recording that as one more
    "crashed" model would repeat the same failure for every remaining model and hide the cause.
    """
    if returncode == EXIT_DEPENDENCY:
        print((stderr or "").strip() or "a worker exited: a required dependency is missing",
              file=sys.stderr)
        raise SystemExit(EXIT_DEPENDENCY)


def require_or_exit(*names):
    """Check every named registry dependency; on the first failure exit(2) with guidance."""
    mods = []
    for name in names:
        try:
            mods.append(_deps.require(name))
        except DependencyError as err:
            exit_with(err)
    return mods[0] if len(mods) == 1 else mods


def run_main(main):
    """Run ``main()``; a DependencyError escaping from it becomes a guided exit(2)."""
    try:
        return main()
    except DependencyError as err:
        exit_with(err)


def optional_version(name):
    """``(version, None)`` or ``(None, reason)`` for a dependency used only as metadata."""
    try:
        module = _deps.require(name)
    except DependencyError as err:
        return None, "%s (%s)" % (err.kind, str(err).splitlines()[0])
    if name == "gurobipy":
        try:
            return ".".join(str(x) for x in module.gurobi.version()), None
        except Exception as exc:  # optional-dep: gurobi_version_unavailable_reason
            return None, "gurobipy.gurobi.version() failed: %s: %s" % (type(exc).__name__, exc)
    version = _deps._installed_version(_deps.REGISTRY[name], module)
    if version is None:
        return None, "%s is installed but reports no version" % name
    return version, None


def gpu_name():
    """``(name, None)`` or ``(None, reason)`` from nvidia-smi."""
    try:
        exe = _deps.require_tool("nvidia-smi")
    except DependencyError as err:
        return None, "%s (%s)" % (err.kind, str(err).splitlines()[0])
    try:
        out = subprocess.run([exe, "--query-gpu=name", "--format=csv,noheader"],
                             capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError) as exc:
        return None, "nvidia-smi could not be run: %s: %s" % (type(exc).__name__, exc)
    lines = out.stdout.strip().splitlines()
    if out.returncode != 0 or not lines:
        why = (out.stderr or out.stdout).strip().splitlines()
        return None, "nvidia-smi exited %d%s" % (out.returncode, ": " + why[0] if why else "")
    return lines[0], None


def environment_info(gurobi=True, gpu=True):
    """Version metadata dict; unavailable fields are null with ``*_unavailable_reason``."""
    info = {"python": platform.python_version()}
    probes = [("cuopt_version", lambda: optional_version("cuopt"))]
    if gurobi:
        probes.append(("gurobi_version", lambda: optional_version("gurobipy")))
    if gpu:
        probes.append(("gpu_name", gpu_name))
    for field, probe in probes:
        value, reason = probe()
        info[field] = value
        if value is None:
            info[field + "_unavailable_reason"] = reason
    return info
