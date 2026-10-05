"""Repo-wide dependency inventory (specs/016-missing-dependency-errors, research.md R8).

Everything here is computed over the WHOLE repository (gpugem/, benchmarks/, examples/, tests/),
including files this feature did not touch, so a new unregistered import or a re-introduced silent
swallow fails the suite.
"""

import ast
import re
import subprocess
import sys
from pathlib import Path

import pytest

from gpugem import _deps

ROOT = Path(__file__).resolve().parent.parent
SCAN_DIRS = ("gpugem", "benchmarks", "examples", "tests")
FIRST_PARTY = {"gpugem", "benchmarks", "tests"} | {
    # sibling-module imports that scripts make after putting their own directory on sys.path
    p.stem for d in SCAN_DIRS for p in (ROOT / d).rglob("*.py")}

# Imported names that are deliberately NOT in the registry, each with a reason.
EXEMPT_IMPORTS = {
    "_pytest": "pytest internals, only reachable when pytest itself is present",
    "setuptools": "build backend named in pyproject.toml only",
}
# Executables run from Python besides the registry's tools and the running interpreter.
EXEMPT_EXECUTABLES = {
    "pip": "invoked as `sys.executable -m pip`, i.e. via the interpreter",
}
# Registry entries that are verified at import time in gpugem/__init__.py.
IMPORT_TIME_CHECKED = {"numpy", "scipy"}


def _py_files():
    for d in SCAN_DIRS:
        for p in sorted((ROOT / d).rglob("*.py")):
            if "model_cache" in p.parts or "__pycache__" in p.parts:
                continue
            yield p


def _parse(p):
    return ast.parse(p.read_text(), filename=str(p))


def _top_names(tree):
    """Top-level module names imported anywhere in the file, plus import_module literals."""
    names, dynamic = set(), []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                names.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call):
            f = node.func
            fname = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)
            if fname == "import_module" and node.args:
                a = node.args[0]
                if isinstance(a, ast.Constant) and isinstance(a.value, str):
                    names.add(a.value.split(".")[0])
                else:
                    dynamic.append(node.lineno)
    return names, dynamic


def test_min_versions_match_pyproject():
    text = (ROOT / "pyproject.toml").read_text()
    deps = re.search(r"^dependencies\s*=\s*\[(.*?)\]", text, re.S | re.M).group(1)
    extras = re.search(r"^cobra\s*=\s*\[(.*?)\]", text, re.S | re.M).group(1)
    declared = {}
    for spec in re.findall(r'"([^"]+)"', deps + extras):
        m = re.match(r"([A-Za-z0-9_.-]+)>=([\w.]+)", spec)
        if m:
            declared[m.group(1)] = m.group(2)
    mapping = {"numpy": "numpy", "scipy": "scipy", "cuopt-cu12": "cuopt", "cobra": "cobra"}
    assert set(declared) == set(mapping), declared
    for dist, name in mapping.items():
        assert declared[dist] == _deps.MIN_VERSIONS[name], (dist, declared[dist])
        assert _deps.REGISTRY[name].min_version == _deps.MIN_VERSIONS[name]


def test_every_external_import_is_registered():
    stdlib = set(sys.stdlib_module_names)
    registered = set(_deps.REGISTRY)
    unregistered, not_analysable = {}, []
    for p in _py_files():
        names, dynamic = _top_names(_parse(p))
        not_analysable += ["%s:%d" % (p.relative_to(ROOT), n) for n in dynamic]
        for n in names - stdlib - FIRST_PARTY - registered - set(EXEMPT_IMPORTS):
            unregistered.setdefault(n, []).append(str(p.relative_to(ROOT)))
    assert not unregistered, (
        "external imports missing from gpugem._deps.REGISTRY (add them, or add a justified entry "
        "to EXEMPT_IMPORTS): %r" % unregistered)
    # reported, not silently ignored (research.md R8): dynamic import names are invisible to AST
    if not_analysable:
        print("NOT ANALYSABLE (dynamic import_module argument):", not_analysable)


def test_scan_actually_sees_imports(tmp_path):
    """The scanner must be able to fail: it finds an unregistered import in a synthetic file."""
    f = tmp_path / "x.py"
    f.write_text("import foo_bar\nfrom baz_qux.sub import y\ndef g():\n    import numpy\n")
    names, _ = _top_names(_parse(f))
    assert names == {"foo_bar", "baz_qux", "numpy"}


def _required_literals(tree):
    """Names passed as literals to require() / require_or_exit() / optional_version()."""
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            fname = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)
            if fname in ("require", "_require", "require_or_exit", "optional_version"):
                out.update(a.value for a in node.args
                           if isinstance(a, ast.Constant) and isinstance(a.value, str))
    return out


def test_every_registered_python_dependency_is_used_somewhere():
    used = set()
    for p in _py_files():
        tree = _parse(p)
        used |= _top_names(tree)[0] | _required_literals(tree)
    unused = [n for n, s in _deps.REGISTRY.items() if not s.tool and n not in used]
    assert not unused, "registry entries nothing imports (remove or use them): %r" % unused


def _executables(tree):
    """First-argument literals of subprocess calls and shutil.which / require_tool calls."""
    found, unknown = set(), []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        fname = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)
        if fname in ("run", "Popen", "check_call", "check_output", "call") and node.args and (
                isinstance(f, ast.Attribute) and getattr(f.value, "id", None) == "subprocess"):
            a = node.args[0]
            if isinstance(a, (ast.List, ast.Tuple)) and a.elts:
                a = a.elts[0]
            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                found.add(a.value)
            elif (isinstance(a, ast.Attribute) and a.attr == "executable") or (
                    isinstance(a, ast.Call) and getattr(a.func, "id", "") == "str") or (
                    isinstance(a, ast.Name) and a.id in ("exe", "python_exe", "cmd")):
                pass   # interpreter / venv python / prebuilt command: interpreter-based
            else:
                unknown.append(node.lineno)
        elif fname in ("which", "require_tool") and node.args:
            a = node.args[0]
            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                found.add(a.value)
    return found, unknown


def test_every_external_executable_is_registered():
    tools = {n for n, s in _deps.REGISTRY.items() if s.tool}
    bad, unknown = {}, []
    for p in _py_files():
        found, unk = _executables(_parse(p))
        unknown += ["%s:%d" % (p.relative_to(ROOT), n) for n in unk]
        for e in found - tools - set(EXEMPT_EXECUTABLES):
            bad.setdefault(e, []).append(str(p.relative_to(ROOT)))
    assert not bad, "executables run from Python but not in the registry: %r" % bad
    if unknown:
        print("NOT ANALYSABLE (non-literal subprocess command):", unknown)


# --- silent swallowing ---------------------------------------------------------------------

def _is_silent(handler):
    """except / except Exception whose body is only pass (or return of an empty literal)."""
    t = handler.type
    broad = t is None or (isinstance(t, ast.Name) and t.id in ("Exception", "BaseException"))
    only_pass = all(isinstance(s, ast.Pass) for s in handler.body)
    return broad and only_pass


def _touches_dependency(try_node):
    """Does the try body import a registered/external module or run a subprocess/require?"""
    stdlib = set(sys.stdlib_module_names)
    for stmt in try_node.body:
        for node in ast.walk(stmt):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                mods = ([a.name for a in node.names] if isinstance(node, ast.Import)
                        else [node.module or ""])
                if any(m.split(".")[0] not in stdlib | FIRST_PARTY for m in mods if m):
                    return True
            if isinstance(node, ast.Call):
                f = node.func
                n = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
                if n in ("require", "require_tool", "which", "run", "Popen", "check_output"):
                    return True
    return False


def silent_dependency_swallows(paths):
    out = []
    for p in paths:
        src = p.read_text().splitlines()
        for node in ast.walk(_parse(p)):
            if isinstance(node, ast.Try) and _touches_dependency(node):
                for h in node.handlers:
                    if _is_silent(h):
                        line = src[h.lineno - 1]
                        if "# optional-dep:" not in line:
                            out.append("%s:%d" % (p.relative_to(ROOT), h.lineno))
    return out


def test_no_silent_swallow_of_dependency_failures():
    bad = silent_dependency_swallows(_py_files())
    assert not bad, (
        "a dependency import/tool call is wrapped in `except Exception: pass`; record the failure "
        "(benchmarks._deps.optional_version / gpu_name) or mark the line "
        "`# optional-dep: <field>_unavailable_reason`: %s" % bad)


def test_swallow_detector_can_fail(tmp_path, monkeypatch):
    """Negative control: the detector flags the exact pattern this feature removed."""
    bad = tmp_path / "bad.py"
    bad.write_text("def f():\n    try:\n        import cuopt\n"
                   "    except Exception:\n        pass\n")
    good = tmp_path / "good.py"
    good.write_text("def f():\n    try:\n        import cuopt\n"
                    "    except Exception:  # optional-dep: cuopt_version_unavailable_reason\n"
                    "        pass\n")
    monkeypatch.setattr(sys.modules[__name__], "ROOT", tmp_path)
    assert silent_dependency_swallows([bad]) == ["bad.py:4"]
    assert silent_dependency_swallows([good]) == []


# --- documentation and package-level guarantees ---------------------------------------------

def test_registry_install_commands_are_documented_in_readme():
    readme = (ROOT / "README.md").read_text()
    missing = [s.install.split("  (")[0] for s in _deps.REGISTRY.values()
               if s.install.split("  (")[0] not in readme]
    assert not missing, "README.md 'Dependencies' section lacks install commands: %r" % missing


def test_import_time_checked_dependencies_are_checked():
    init = (ROOT / "gpugem" / "__init__.py").read_text()
    for name in IMPORT_TIME_CHECKED:
        assert '_require("%s")' % name in init


def test_import_gpugem_reports_missing_numpy():
    code = ("import sys; sys.modules['numpy'] = None\n"
            "try:\n import gpugem\nexcept Exception as e:\n"
            " print(type(e).__name__, e.kind, e.dependency)\n")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         cwd=str(ROOT))
    assert "DependencyError not_installed numpy" in out.stdout, out.stdout + out.stderr


@pytest.mark.parametrize("script", ["run_highs_baseline", "run_benchmark", "make_figure"])
def test_scripts_exit_with_guidance_when_dependency_blocked(script, tmp_path):
    """Representative scripts: exit code 3, named dependency + install command, no output file."""
    dep = {"run_highs_baseline": "highspy", "run_benchmark": "cuopt",
           "make_figure": "matplotlib"}[script]
    runner = ("import sys, runpy\nsys.modules[%r] = None\nsys.argv = %r\n"
              "runpy.run_path(%r, run_name='__main__')\n")
    argv = {"run_highs_baseline": ["x", "--out", str(tmp_path / "out.json"), "--models",
                                   "e_coli_core", "--repo", str(ROOT), "--log-dir", str(tmp_path)],
            "run_benchmark": ["x", "--model", "e_coli_core"],
            "make_figure": ["x"]}[script]
    before = {p for p in ROOT.rglob("*") if "results" in p.parts and p.is_file()}
    out = subprocess.run([sys.executable, "-c",
                          runner % (dep, argv, str(ROOT / "benchmarks" / (script + ".py")))],
                         capture_output=True, text=True, cwd=str(tmp_path))
    assert out.returncode == 3, (out.returncode, out.stdout, out.stderr)
    assert dep in out.stderr and "Fix:" in out.stderr and "pip install" in out.stderr
    assert "Traceback" not in out.stderr
    assert not (tmp_path / "out.json").exists()
    assert {p for p in ROOT.rglob("*") if "results" in p.parts and p.is_file()} == before


def test_every_literal_passed_to_require_is_a_registry_name():
    """A typo in require_or_exit("gurobipi") would only blow up (KeyError) when that script runs."""
    bad = []
    for p in _py_files():
        if "tests" in p.relative_to(ROOT).parts[:1]:
            continue   # tests/test_dependency_errors.py passes an unregistered name on purpose
        for name in _required_literals(_parse(p)):
            if name not in _deps.REGISTRY and "." not in name:
                bad.append("%s: %r" % (p.relative_to(ROOT), name))
    assert not bad, bad
