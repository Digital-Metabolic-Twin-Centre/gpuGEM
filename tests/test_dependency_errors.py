"""Guided errors for missing / broken / old dependencies (specs/016-missing-dependency-errors).

Absence is simulated by blocking imports, so none of these tests need a GPU or cuOpt.
"""

import pickle
import sys
import types

import numpy as np
import pytest
import scipy.sparse as sp

import gpugem
from gpugem import _deps
from gpugem._deps import DependencyError, require, require_tool


@pytest.fixture(autouse=True)
def _fresh_version_cache():
    _deps._version_ok.clear()
    yield
    _deps._version_ok.clear()


def _block(monkeypatch, *names):
    for n in names:
        monkeypatch.setitem(sys.modules, n, None)


def _stub(monkeypatch, name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    monkeypatch.setitem(sys.modules, name, mod)
    return mod


def _no_metadata(monkeypatch):
    """Pretend no pip distribution is installed, so the stub module's __version__ is used."""
    missing = _deps.importlib.metadata.PackageNotFoundError

    def version(dist):
        raise missing(dist)

    monkeypatch.setattr(_deps.importlib.metadata, "version", version)


def _tiny_lp():
    S = sp.csr_matrix(np.array([[1, -1, 0, 0], [0, 1, -1, 0], [0, 0, 1, -1]], dtype=float))
    return dict(S=S, b=np.zeros(3), lb=np.zeros(4), ub=np.full(4, 10.0),
                c=np.array([0., 0., 0., 1.]), maximize=True)


def _assert_guided(err, dependency, kind):
    text = str(err.value)
    assert err.value.dependency == dependency
    assert err.value.kind == kind
    assert dependency in text
    assert "Fix:" in text
    assert "Needed for:" in text or kind == "broken"
    return text


# --- the error object -------------------------------------------------------------------------

def test_error_message_shape_and_pickle():
    e = DependencyError("cuopt", "version", "pip install --upgrade cuopt-cu12",
                        purpose="the solver", detected="1.0", required="26.6.0")
    text = str(e)
    assert "installed 1.0" in text and "required >= 26.6.0" in text
    assert "Needed for: the solver" in text
    assert "Fix: pip install --upgrade cuopt-cu12" in text
    e2 = pickle.loads(pickle.dumps(e))
    assert str(e2) == text and e2.kind == "version"


def test_unknown_kind_rejected():
    with pytest.raises(ValueError):
        DependencyError("x", "nope", "y")


def test_every_registry_entry_has_remedy_and_purpose():
    for spec in _deps.REGISTRY.values():
        assert spec.install and spec.purpose, spec.name
    assert gpugem.DependencyError is DependencyError


# --- require(): the four failure kinds ------------------------------------------------------

def test_require_not_installed(monkeypatch):
    _block(monkeypatch, "cuopt")
    with pytest.raises(DependencyError) as err:
        require("cuopt")
    text = _assert_guided(err, "cuopt", "not_installed")
    assert "pip install" in text
    assert isinstance(err.value.__cause__, ModuleNotFoundError)


def test_require_broken_import_keeps_cause(monkeypatch):
    monkeypatch.setattr(_deps, "gpu_evidence", lambda: (False, "ok"))

    class Boom(types.ModuleType):
        pass

    def fail(name, *a, **k):
        raise OSError("libcudart.so.12: cannot open shared object file")

    monkeypatch.delitem(sys.modules, "cuopt", raising=False)
    real = _deps.importlib.import_module
    monkeypatch.setattr(_deps.importlib, "import_module",
                        lambda n: fail(n) if n == "cuopt" else real(n))
    with pytest.raises(DependencyError) as err:
        require("cuopt")
    _assert_guided(err, "cuopt", "broken")
    assert "libcudart" in str(err.value)
    assert isinstance(err.value.__cause__, OSError)


def test_require_inner_missing_module_is_broken_not_not_installed(monkeypatch):
    real = _deps.importlib.import_module

    def imp(n):
        if n == "cuopt":
            raise ModuleNotFoundError("No module named 'libfoo'", name="libfoo")
        return real(n)

    monkeypatch.setattr(_deps, "gpu_evidence", lambda: (False, "ok"))
    monkeypatch.setattr(_deps.importlib, "import_module", imp)
    with pytest.raises(DependencyError) as err:
        require("cuopt")
    assert err.value.kind == "broken"
    assert "libfoo" in str(err.value)


def test_require_version_too_old(monkeypatch):
    _stub(monkeypatch, "cuopt", __version__="0.0.1")
    _no_metadata(monkeypatch)
    with pytest.raises(DependencyError) as err:
        require("cuopt")
    text = _assert_guided(err, "cuopt", "version")
    assert err.value.detected == "0.0.1" and err.value.required == _deps.MIN_VERSIONS["cuopt"]
    assert "--upgrade" in text


def test_require_version_ok_and_block_after_success_is_seen(monkeypatch):
    _stub(monkeypatch, "cuopt", __version__="99.0.0")
    assert require("cuopt").__version__ == "99.0.0"
    _block(monkeypatch, "cuopt")            # a later block must not be masked by an earlier success
    with pytest.raises(DependencyError):
        require("cuopt")


def test_cuopt_import_failure_with_no_gpu_evidence_is_no_gpu(monkeypatch):
    real = _deps.importlib.import_module

    def imp(n):
        if n == "cuopt":
            raise ImportError("libcuda.so.1: cannot open shared object file")
        return real(n)

    monkeypatch.setattr(_deps, "gpu_evidence", lambda: (True, "nvidia-smi not found"))
    monkeypatch.setattr(_deps.importlib, "import_module", imp)
    with pytest.raises(DependencyError) as err:
        require("cuopt")
    _assert_guided(err, "cuopt", "no_gpu")
    assert "nvidia-smi" in str(err.value) and "libcuda" in str(err.value)


def test_require_unregistered_name_is_a_programming_error():
    with pytest.raises(KeyError):
        require("not_in_registry")


def test_require_tool_missing(monkeypatch):
    monkeypatch.setattr(_deps.shutil, "which", lambda n: None)
    with pytest.raises(DependencyError) as err:
        require_tool("nvidia-smi")
    _assert_guided(err, "nvidia-smi", "tool_missing")
    with pytest.raises(DependencyError):
        require("nvidia-smi")              # tools route through require_tool


def test_parse_version():
    assert _deps.parse_version("26.06.00") == (26, 6, 0)
    assert _deps.parse_version("1.24.0rc1") == (1, 24, 0)
    assert _deps.parse_version("26.6") < _deps.parse_version("26.6.1")


# --- gpu_evidence ---------------------------------------------------------------------------

def test_gpu_evidence_absent_tool_and_no_device(monkeypatch):
    monkeypatch.setattr(_deps.shutil, "which", lambda n: None)
    monkeypatch.setattr(_deps.glob, "glob", lambda p: [])
    assert _deps.gpu_evidence()[0] is True


def test_gpu_evidence_absent_tool_but_device_node_is_not_proof(monkeypatch):
    monkeypatch.setattr(_deps.shutil, "which", lambda n: None)
    monkeypatch.setattr(_deps.glob, "glob", lambda p: ["/dev/nvidia0"])
    assert _deps.gpu_evidence()[0] is False


@pytest.mark.parametrize("rc,out,err,expect", [
    (9, "", "NVIDIA-SMI has failed", True),
    (0, "", "", True),
    (0, "GPU 0: Foo (UUID: x)\n", "", False),
])
def test_gpu_evidence_nvidia_smi_results(monkeypatch, rc, out, err, expect):
    monkeypatch.setattr(_deps.shutil, "which", lambda n: "/usr/bin/nvidia-smi")
    monkeypatch.setattr(_deps.subprocess, "run",
                        lambda *a, **k: types.SimpleNamespace(
                            returncode=rc, stdout=out, stderr=err))
    assert _deps.gpu_evidence()[0] is expect


# --- US1: public entry points ---------------------------------------------------------------

def test_import_gpugem_does_not_need_cuopt(monkeypatch):
    import subprocess
    code = ("import sys; sys.modules['cuopt'] = None; import gpugem; "
            "print('ok', gpugem.DependencyError.__name__)")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert "ok DependencyError" in out.stdout


def test_solve_without_cuopt_is_guided(monkeypatch):
    _block(monkeypatch, "cuopt")
    with pytest.raises(DependencyError) as err:
        gpugem.solve(**_tiny_lp())
    text = _assert_guided(err, "cuopt", "not_installed")
    assert "pip install" in text


def test_fbasolver_without_cuopt_is_guided(monkeypatch):
    _block(monkeypatch, "cuopt")
    lp = _tiny_lp()
    solver = gpugem.FBASolver(lp["S"], lp["b"], lp["lb"], lp["ub"], lp["c"], maximize=True)
    with pytest.raises(DependencyError) as err:
        solver.solve()
    assert err.value.dependency == "cuopt"


def test_solve_with_old_cuopt_is_guided(monkeypatch):
    _stub(monkeypatch, "cuopt", __version__="1.0.0")
    _no_metadata(monkeypatch)
    with pytest.raises(DependencyError) as err:
        gpugem.solve(**_tiny_lp())
    assert err.value.kind == "version"


def test_solve_failure_inside_cuopt_with_no_gpu_evidence(monkeypatch):
    class Settings:
        def set_parameter(self, k, v):
            pass

    class DataModel:
        def __getattr__(self, n):
            return lambda *a, **k: None

    def Solve(dm, settings):
        raise RuntimeError("CUDA error: no CUDA-capable device is detected")

    _stub(monkeypatch, "cuopt", __version__="99.0.0")
    lp_mod = _stub(monkeypatch, "cuopt.linear_programming",
                   DataModel=DataModel, Solve=Solve, SolverSettings=Settings)
    sys.modules["cuopt"].linear_programming = lp_mod
    monkeypatch.setattr(_deps, "gpu_evidence", lambda: (True, "nvidia-smi not found"))
    with pytest.raises(DependencyError) as err:
        gpugem.solve(**_tiny_lp(), check_feasibility=False)
    _assert_guided(err, "cuopt", "no_gpu")
    assert isinstance(err.value.__cause__, RuntimeError)


def test_solve_failure_with_working_gpu_reraises_original(monkeypatch):
    class Settings:
        def set_parameter(self, k, v):
            pass

    class DataModel:
        def __getattr__(self, n):
            return lambda *a, **k: None

    def Solve(dm, settings):
        raise ValueError("bad model")

    _stub(monkeypatch, "cuopt", __version__="99.0.0")
    lp_mod = _stub(monkeypatch, "cuopt.linear_programming",
                   DataModel=DataModel, Solve=Solve, SolverSettings=Settings)
    sys.modules["cuopt"].linear_programming = lp_mod
    monkeypatch.setattr(_deps, "gpu_evidence", lambda: (False, "GPU 0"))
    with pytest.raises(ValueError, match="bad model"):
        gpugem.solve(**_tiny_lp(), check_feasibility=False)


# --- US2: optional dependencies / file formats ----------------------------------------------

def test_from_cobra_without_cobra_is_guided(monkeypatch):
    _block(monkeypatch, "cobra")
    with pytest.raises(DependencyError) as err:
        gpugem.loaders.from_cobra(None)
    text = _assert_guided(err, "cobra", "not_installed")
    assert "gpugem[cobra]" in text


def test_solve_cobra_without_cobra_is_guided(monkeypatch):
    _block(monkeypatch, "cobra")
    with pytest.raises(DependencyError) as err:
        gpugem.solve_cobra(None)
    assert err.value.dependency == "cobra"


def test_from_mat_corrupt_file_is_guided(tmp_path):
    f = tmp_path / "bad.mat"
    f.write_bytes(b"this is not a mat file at all" * 10)
    with pytest.raises(DependencyError) as err:
        gpugem.loaders.from_mat(f)
    assert err.value.kind == "broken"
    assert "bad.mat" in str(err.value) and "Fix:" in str(err.value)
    assert err.value.__cause__ is not None


def test_from_mat_v73_file_is_guided(tmp_path, monkeypatch):
    import scipy.io

    def fake(*a, **k):
        raise NotImplementedError("Please use HDF reader for matlab v7.3 files, e.g. h5py")

    monkeypatch.setattr(scipy.io, "loadmat", fake)
    with pytest.raises(DependencyError) as err:
        gpugem.loaders.from_mat(tmp_path / "m.mat")
    assert "-v7" in str(err.value)


def test_from_mat_missing_file_stays_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        gpugem.loaders.from_mat(tmp_path / "nope.mat")


# --- US3: benchmark and tooling helpers -----------------------------------------------------

def test_environment_info_records_reason_when_probes_fail(monkeypatch):
    from benchmarks import _deps as BD
    _block(monkeypatch, "cuopt", "gurobipy")
    monkeypatch.setattr(_deps.shutil, "which", lambda n: None)
    info = BD.environment_info()
    for field in ("cuopt_version", "gurobi_version", "gpu_name"):
        assert info[field] is None
        assert info[field + "_unavailable_reason"], field
    assert "not_installed" in info["cuopt_version_unavailable_reason"]
    assert "tool_missing" in info["gpu_name_unavailable_reason"]
    assert info["python"]


def test_environment_info_reports_values_when_available(monkeypatch):
    from benchmarks import _deps as BD
    _stub(monkeypatch, "cuopt", __version__="99.1.0")
    monkeypatch.setattr(_deps.importlib.metadata, "version",
                        lambda d: "99.1.0" if d.startswith("cuopt") else "0")
    monkeypatch.setattr(BD, "gpu_name", lambda: ("Test GPU", None))
    info = BD.environment_info(gurobi=False)
    assert info["cuopt_version"] == "99.1.0" and info["gpu_name"] == "Test GPU"
    assert "cuopt_version_unavailable_reason" not in info


def test_gpu_name_nonzero_exit_has_reason(monkeypatch):
    from benchmarks import _deps as BD
    monkeypatch.setattr(_deps.shutil, "which", lambda n: "/usr/bin/nvidia-smi")
    monkeypatch.setattr(BD.subprocess, "run", lambda *a, **k: types.SimpleNamespace(
        returncode=9, stdout="", stderr="NVIDIA-SMI has failed"))
    name, reason = BD.gpu_name()
    assert name is None and "NVIDIA-SMI has failed" in reason


def test_require_or_exit_exits_3_with_guidance(monkeypatch, capsys):
    from benchmarks import _deps as BD
    _block(monkeypatch, "highspy")
    with pytest.raises(SystemExit) as exit_info:
        BD.require_or_exit("numpy", "highspy")
    assert exit_info.value.code == BD.EXIT_DEPENDENCY == 3
    err = capsys.readouterr().err
    assert "highspy" in err and "pip install highspy" in err


def test_run_main_converts_escaping_dependency_error(capsys):
    from benchmarks import _deps as BD

    def main():
        raise DependencyError("x", "not_installed", "pip install x", purpose="testing")

    with pytest.raises(SystemExit) as exit_info:
        BD.run_main(main)
    assert exit_info.value.code == 3 and "pip install x" in capsys.readouterr().err


def test_propagate_dependency_exit(capsys):
    from benchmarks import _deps as BD
    BD.propagate_dependency_exit(0, "ignored")
    BD.propagate_dependency_exit(1, "ignored")          # an ordinary crash is not a dependency exit
    with pytest.raises(SystemExit) as exit_info:
        BD.propagate_dependency_exit(3, "gpuGEM cannot run: cuopt is not installed.\n  Fix: x")
    assert exit_info.value.code == 3
    assert "cuopt is not installed" in capsys.readouterr().err


def test_gurobi_licence_error_is_distinct_from_not_installed(monkeypatch):
    class GurobiError(Exception):
        def __init__(self, msg, errno):
            super().__init__(msg)
            self.errno = errno

    class Env:
        def __init__(self, empty=False):
            pass

        def setParam(self, *a):
            pass

        def start(self):
            raise GurobiError("No Gurobi license found", 10009)

    _stub(monkeypatch, "gurobipy", GurobiError=GurobiError, Env=Env, GRB=types.SimpleNamespace())
    from benchmarks import solve as SV
    with pytest.raises(DependencyError) as err:
        SV.solve_gurobi({})
    text = _assert_guided(err, "gurobipy", "license")
    assert "licen" in text and isinstance(err.value.__cause__, GurobiError)


def test_gurobi_unrelated_error_is_not_relabelled(monkeypatch):
    class GurobiError(Exception):
        errno = 10003

    class Env:
        def __init__(self, empty=False):
            pass

        def setParam(self, *a):
            pass

        def start(self):
            raise GurobiError("Invalid argument")

    _stub(monkeypatch, "gurobipy", GurobiError=GurobiError, Env=Env, GRB=types.SimpleNamespace())
    from benchmarks import solve as SV
    with pytest.raises(GurobiError):
        SV.solve_gurobi({})


def test_model_download_failure_is_network_error(monkeypatch):
    from benchmarks import models as M

    def load_model(name):
        raise ConnectionError("Max retries exceeded")

    cobra = _stub(monkeypatch, "cobra", __version__="99.0.0")
    cobra.io = types.SimpleNamespace(load_model=load_model)
    _no_metadata(monkeypatch)
    with pytest.raises(DependencyError) as err:
        M._load_cobra("no_such_model_for_test")
    text = _assert_guided(err, "BiGG model server", "network")
    assert "model_cache" in text and "no_such_model_for_test.xml" in text


def test_venv_provisioning_failure_is_guided():
    from benchmarks import run_version_lifting_comparison as RV
    with pytest.raises(DependencyError) as err:
        RV._run_provisioning([sys.executable, "-c", "import sys; sys.exit(1)"],
                             "install it by hand", "cuopt")
    assert err.value.kind == "broken" and "install it by hand" in str(err.value)
    with pytest.raises(DependencyError):
        RV._run_provisioning(["/nonexistent/python-binary"], "install it by hand", "venv")


def test_solver_mode_variants_validation_without_cuopt_is_guided(monkeypatch):
    from benchmarks import solver_mode_variants as V
    _block(monkeypatch, "cuopt")
    with pytest.raises(DependencyError) as err:
        V.validate_variants()
    assert err.value.dependency == "cuopt"
