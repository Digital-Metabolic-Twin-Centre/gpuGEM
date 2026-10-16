"""The release gate in .github/scripts/check_release_version.py must be able to fail.

publish.yml refuses to upload to PyPI unless the release tag matches every version string in
the repository. A gate that cannot fail is not a gate, so each source is tested on its own.
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / ".github" / "scripts" / "check_release_version.py"

spec = importlib.util.spec_from_file_location("check_release_version", SCRIPT)
crv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(crv)


def _make_repo(tmp_path, pyproject="0.1.3", init="0.1.3", cff="0.1.3", zenodo="0.1.3"):
    (tmp_path / "gpugem").mkdir()
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "gpugem"\nversion = "%s"\n' % pyproject)
    (tmp_path / "gpugem" / "__init__.py").write_text('__version__ = "%s"\n' % init)
    (tmp_path / "CITATION.cff").write_text("cff-version: 1.2.0\nversion: %s\n" % cff)
    (tmp_path / ".zenodo.json").write_text(json.dumps({"version": zenodo}))
    return tmp_path


def test_consistent_release_passes(tmp_path):
    assert crv.check("v0.1.3", _make_repo(tmp_path)) == []


@pytest.mark.parametrize("field", ["pyproject", "init", "cff", "zenodo"])
def test_each_stale_version_file_blocks_the_release(tmp_path, field):
    repo = _make_repo(tmp_path, **{field: "0.1.2"})
    problems = crv.check("v0.1.3", repo)
    assert len(problems) == 1 and "0.1.2" in problems[0] and "0.1.3" in problems[0]


def test_all_files_stale_reports_every_one(tmp_path):
    repo = _make_repo(tmp_path, pyproject="0.1.2", init="0.1.2", cff="0.1.2", zenodo="0.1.2")
    assert len(crv.check("v0.1.3", repo)) == 4


@pytest.mark.parametrize("tag", ["0.1.3", "v0.1", "v0.1.3-rc1", "release-1", "v1.2.3.4", ""])
def test_malformed_tags_are_rejected(tmp_path, tag):
    assert crv.check(tag, _make_repo(tmp_path))


def test_missing_version_in_a_file_is_a_problem(tmp_path):
    repo = _make_repo(tmp_path)
    (repo / "gpugem" / "__init__.py").write_text("# no version here\n")
    problems = crv.check("v0.1.3", repo)
    assert any("__init__.py" in p and "no version" in p for p in problems)


def test_cli_exit_codes(tmp_path):
    repo = _make_repo(tmp_path)
    ok = subprocess.run([sys.executable, str(SCRIPT), "v0.1.3", str(repo)],
                        capture_output=True, text=True, check=False)
    assert ok.returncode == 0, ok.stderr
    bad = subprocess.run([sys.executable, str(SCRIPT), "v0.9.9", str(repo)],
                         capture_output=True, text=True, check=False)
    assert bad.returncode == 1 and "NOT consistent" in bad.stderr
    usage = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True,
                           check=False)
    assert usage.returncode == 2


def test_this_repository_is_internally_consistent():
    """All four version strings in the real repo agree with each other."""
    versions = set(crv.read_versions(ROOT).values())
    assert len(versions) == 1 and None not in versions, crv.read_versions(ROOT)


def test_this_repository_fails_for_a_different_tag():
    """Negative control on the real files: a tag that is not the current version is refused."""
    current = next(iter(crv.read_versions(ROOT).values()))
    major, minor, patch = (int(x) for x in current.split("."))
    wrong = "v%d.%d.%d" % (major, minor, patch + 1)
    assert crv.check(wrong, ROOT)
    assert crv.check("v" + current, ROOT) == []
