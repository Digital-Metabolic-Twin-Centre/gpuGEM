"""External-dependency registry and guided errors.

Every external package or executable gpuGEM, its benchmarks and its examples rely on is listed in
:data:`REGISTRY`. :func:`require` / :func:`require_tool` turn "missing", "fails to load", "too
old" and "no usable GPU" into one catchable :class:`DependencyError` that says what is wrong, why
it is needed and how to fix it (specs/016-missing-dependency-errors/contracts/).

This module is standard-library only so it can be imported when numpy/scipy/cuOpt are absent.
"""

from __future__ import annotations

import glob
import importlib
import importlib.metadata
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional

KINDS = ("not_installed", "broken", "version", "no_gpu", "license", "tool_missing", "network")

_CUOPT_DOCS = "https://docs.nvidia.com/cuopt/user-guide/latest/introduction.html"

_STATE_TEXT = {
    "not_installed": "is not installed",
    "broken": "is installed but fails to load",
    "version": "is not a supported version",
    "no_gpu": "cannot be used: a GPU or driver problem is suspected",
    "license": "is installed but its licence is missing or invalid",
    "tool_missing": "was not found on PATH",
    "network": "could not be reached",
}


class DependencyError(RuntimeError):
    """A required dependency is missing, broken, too old, or has no usable GPU/licence/network.

    Attributes
    ----------
    dependency : str
        Registry name, e.g. ``"cuopt"``.
    kind : str
        One of ``not_installed, broken, version, no_gpu, license, tool_missing, network``.
    detected, required : str or None
        Installed and minimum versions (``kind == "version"``).
    remedy : str
        What the user should do.

    The original exception, when there is one, is available as ``__cause__``.
    """

    def __init__(self, dependency: str, kind: str, remedy: str, *, purpose: Optional[str] = None,
                 detected: Optional[str] = None, required: Optional[str] = None,
                 detail: Optional[str] = None, problem: Optional[str] = None):
        if kind not in KINDS:
            raise ValueError("unknown DependencyError kind %r" % (kind,))
        self.dependency = dependency
        self.kind = kind
        self.remedy = remedy
        self.purpose = purpose
        self.detected = detected
        self.required = required
        self.detail = detail
        self.problem = problem
        state = problem or _STATE_TEXT[kind]
        if kind == "version" and not problem:
            state = "is too old (installed %s, required >= %s)" % (detected, required)
        lines = ["gpuGEM cannot run: %s %s." % (dependency, state)]
        if purpose:
            lines.append("  Needed for: %s" % purpose)
        lines.append("  Fix: %s" % remedy)
        if detail:
            lines.append("  (details: %s)" % detail)
        super().__init__("\n".join(lines))

    def __reduce__(self):
        return (_rebuild, (self.dependency, self.kind, self.remedy, self.purpose,
                           self.detected, self.required, self.detail, self.problem))


def _rebuild(dependency, kind, remedy, purpose, detected, required, detail, problem):
    return DependencyError(dependency, kind, remedy, purpose=purpose, detected=detected,
                           required=required, detail=detail, problem=problem)


@dataclass(frozen=True)
class DependencySpec:
    name: str                      # import name, or executable name for tools
    role: str                      # required | optional | benchmark | tool | dev
    purpose: str
    install: str
    distributions: tuple = ()      # pip distribution names to read the version from
    min_version: Optional[str] = None
    extra: Optional[str] = None
    tool: bool = False


# Minimum versions are mirrored in pyproject.toml; tests/test_dependency_inventory.py fails if
# the two drift apart.
MIN_VERSIONS = {
    "numpy": "1.24",
    "scipy": "1.10",
    "cuopt": "26.6.0",
    "cobra": "0.29",
}

_SPECS = [
    DependencySpec(
        "numpy", "required", "array maths used by every gpuGEM function",
        'pip install "numpy>=%s"' % MIN_VERSIONS["numpy"], ("numpy",), MIN_VERSIONS["numpy"]),
    DependencySpec(
        "scipy", "required", "sparse matrices and .mat file reading",
        'pip install "scipy>=%s"' % MIN_VERSIONS["scipy"], ("scipy",), MIN_VERSIONS["scipy"]),
    DependencySpec(
        "cuopt", "required", "the GPU linear-programming solver that gpuGEM wraps",
        'pip install "cuopt-cu12>=%s"  (other CUDA versions: see %s)'
        % (MIN_VERSIONS["cuopt"], _CUOPT_DOCS),
        ("cuopt-cu12", "cuopt-cu13", "cuopt"), MIN_VERSIONS["cuopt"]),
    DependencySpec(
        "cobra", "optional", "reading COBRApy models (gpugem.solve_cobra, loaders.from_cobra)",
        'pip install "gpugem[cobra]"  (or: pip install "cobra>=%s")' % MIN_VERSIONS["cobra"],
        ("cobra",), MIN_VERSIONS["cobra"], extra="cobra"),
    DependencySpec(
        "gurobipy", "benchmark", "the Gurobi baseline in the benchmarks (needs a Gurobi licence)",
        "pip install gurobipy  (a licence is required to solve large models: "
        "https://www.gurobi.com/academia/academic-program-and-licenses/)", ("gurobipy",)),
    DependencySpec(
        "highspy", "benchmark", "the HiGHS CPU baseline in the benchmarks",
        "pip install highspy", ("highspy",)),
    DependencySpec(
        "pandas", "benchmark", "result tables in the benchmark aggregation and figure scripts",
        "pip install pandas", ("pandas",)),
    DependencySpec(
        "matplotlib", "benchmark", "drawing the benchmark figures",
        "pip install matplotlib", ("matplotlib",)),
    DependencySpec(
        "pytest", "dev", "running the test suite",
        'pip install -e ".[dev]"', ("pytest",)),
    DependencySpec(
        "nvidia-smi", "tool", "reading the GPU name for benchmark metadata and diagnosing "
        "GPU problems", "install the NVIDIA driver (https://www.nvidia.com/drivers); "
        "nvidia-smi ships with it", tool=True),
]

REGISTRY = {s.name: s for s in _SPECS}

_version_ok = set()


def _spec(name):
    try:
        return REGISTRY[name]
    except KeyError:
        raise KeyError("%r is not in gpugem._deps.REGISTRY; add it there" % (name,)) from None


def parse_version(text):
    """Leading integer components of a version string: ``"26.06.00rc1"`` -> ``(26, 6, 0)``."""
    parts = []
    for piece in str(text).split("."):
        m = re.match(r"\d+", piece)
        if not m:
            break
        parts.append(int(m.group()))
        if m.end() != len(piece):
            break
    return tuple(parts)


def _installed_version(spec, module):
    for dist in spec.distributions:
        try:
            return importlib.metadata.version(dist)
        except importlib.metadata.PackageNotFoundError:
            continue
    v = getattr(module, "__version__", None)
    return str(v) if v is not None else None


def gpu_evidence():
    """Return ``(problem, detail)``: whether there is evidence the NVIDIA GPU/driver is unusable.

    ``problem`` is True only on positive evidence (``nvidia-smi`` fails or lists no GPU, or it is
    absent and no ``/dev/nvidia<N>`` device exists). An absent ``nvidia-smi`` alone is not proof
    (containers can have a working GPU without it) so with a device node present this returns False.
    """
    exe = shutil.which("nvidia-smi")
    if exe is None:
        if glob.glob("/dev/nvidia[0-9]*"):
            return False, "nvidia-smi not found, but /dev/nvidia* exists"
        return True, "nvidia-smi not found and no /dev/nvidia* device exists"
    try:
        out = subprocess.run([exe, "-L"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as exc:
        return True, "nvidia-smi could not be run: %s" % exc
    if out.returncode != 0:
        msg = (out.stderr or out.stdout).strip().splitlines()
        return True, "nvidia-smi exited %d: %s" % (out.returncode, msg[0] if msg else "")
    if "GPU" not in out.stdout:
        return True, "nvidia-smi lists no GPU"
    return False, out.stdout.strip().splitlines()[0]


def _no_gpu_error(cause_text, evidence_detail):
    spec = REGISTRY["cuopt"]
    return DependencyError(
        "cuopt", "no_gpu",
        "check that an NVIDIA GPU is visible (run `nvidia-smi`), that the driver supports the CUDA "
        "version of your cuopt build, and that you are not inside a container without GPU access",
        purpose=spec.purpose,
        detail="%s; %s" % (evidence_detail, cause_text))


def require(name):
    """Import and return the registered module ``name``, or raise :class:`DependencyError`."""
    spec = _spec(name)
    if spec.tool:
        return require_tool(name)
    try:
        module = importlib.import_module(name)
    except ModuleNotFoundError as exc:
        if (exc.name or "").split(".")[0] != name:
            # the package is there but one of ITS imports is not
            raise _broken(spec, exc) from exc
        raise DependencyError(name, "not_installed", spec.install, purpose=spec.purpose) from exc
    except Exception as exc:  # ImportError, OSError (shared library), RuntimeError, ...
        raise _broken(spec, exc) from exc

    if spec.min_version and name not in _version_ok:
        detected = _installed_version(spec, module)
        if detected is not None and parse_version(detected) < parse_version(spec.min_version):
            raise DependencyError(
                name, "version", spec.install.replace("pip install", "pip install --upgrade", 1),
                purpose=spec.purpose, detected=detected, required=spec.min_version)
        _version_ok.add(name)
    return module


def _broken(spec, exc):
    detail = "%s: %s" % (type(exc).__name__, exc)
    if spec.name == "cuopt":
        problem, evidence = gpu_evidence()
        if problem:
            return _no_gpu_error(detail, evidence)
    return DependencyError(
        spec.name, "broken",
        "reinstall it (%s); if the problem persists the installed build does not match this "
        "machine (Python, CUDA runtime or driver version)" % spec.install.split("  (")[0],
        purpose=spec.purpose, detail=detail)


def require_tool(name):
    """Return the path of registered executable ``name``, or raise :class:`DependencyError`."""
    spec = _spec(name)
    path = shutil.which(name)
    if path is None:
        raise DependencyError(name, "tool_missing", spec.install, purpose=spec.purpose)
    return path


def diagnose_solver_failure(exc):
    """Re-raise ``exc`` as a ``no_gpu`` :class:`DependencyError` if the GPU is demonstrably unusable.

    Called when cuOpt raises while building or solving a model. If there is no positive evidence
    of a GPU/driver problem this returns, and the caller re-raises the original exception.
    """
    problem, evidence = gpu_evidence()
    if problem:
        raise _no_gpu_error("%s: %s" % (type(exc).__name__, exc), evidence) from exc
