"""Repository-wide pytest configuration.

A test that cannot run because an *optional* backend is absent is reported as a
SKIP rather than a FAILURE. gpuGEM's solving path needs cuOpt (NVIDIA GPU, CUDA
12) and its reference baseline needs a licensed gurobipy; neither is installable
on an ordinary CPU-only machine. Without this hook a reviewer who clones the
repository and runs `pytest` sees 16 red failures that say nothing about the
health of the code, which is exactly the impression we do not want to give.

The skip is deliberately narrow. It fires only on gpuGEM's own DependencyError,
and on ModuleNotFoundError for the three names registered as optional. A real
bug -- an AssertionError, or an import error for a *required* package such as
numpy -- still fails, so this cannot quietly hide a broken release.
"""

import pytest

try:
    from gpugem._deps import DependencyError
except Exception:  # pragma: no cover - gpugem itself is unimportable
    DependencyError = ()

# Optional backends. numpy/scipy are hard dependencies and are NOT listed here:
# if they are missing the suite should fail loudly.
_OPTIONAL_BACKENDS = {"cuopt", "gurobipy", "cobra"}


def _skip_reason(exc):
    if DependencyError and isinstance(exc, DependencyError):
        return getattr(exc, "dependency", None) or "optional backend"
    if isinstance(exc, ModuleNotFoundError):
        root = (exc.name or "").split(".")[0]
        if root in _OPTIONAL_BACKENDS:
            return root
    return None


@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item):
    try:
        return (yield)
    except BaseException as exc:
        reason = _skip_reason(exc)
        if reason is None:
            raise
        pytest.skip(f"backend unavailable (not installed, or no usable GPU/licence): {reason}")
