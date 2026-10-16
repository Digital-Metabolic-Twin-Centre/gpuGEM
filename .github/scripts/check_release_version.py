"""Fail unless a release tag matches every version string in the repository.

Used by .github/workflows/publish.yml before anything is uploaded to PyPI. A release
whose tag says v0.1.3 while pyproject.toml still says 0.1.2 would otherwise be rejected
by PyPI with a confusing duplicate-version error, or worse, publish the wrong thing.

Usage: python check_release_version.py <tag> [repo_root]
Exit status 0 when every source agrees with the tag, 1 otherwise.
"""

from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def read_versions(root: Path) -> dict[str, str | None]:
    """Version string found in each file that carries one (None when a file has none)."""
    out: dict[str, str | None] = {}

    pyproject = tomllib.loads((root / "pyproject.toml").read_text())
    out["pyproject.toml"] = pyproject.get("project", {}).get("version")

    init = (root / "gpugem" / "__init__.py").read_text()
    m = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', init, re.M)
    out["gpugem/__init__.py"] = m.group(1) if m else None

    cff = (root / "CITATION.cff").read_text()
    m = re.search(r'^version:\s*["\']?([^\s"\']+)', cff, re.M)
    out["CITATION.cff"] = m.group(1) if m else None

    zenodo = json.loads((root / ".zenodo.json").read_text())
    out[".zenodo.json"] = zenodo.get("version")
    return out


def check(tag: str, root: Path) -> list[str]:
    """Return a list of problems; an empty list means the release is consistent."""
    if not tag.startswith("v"):
        return ["tag %r does not start with 'v' (expected e.g. v0.1.3)" % tag]
    expected = tag[1:]
    if not SEMVER.match(expected):
        return ["tag %r is not of the form vMAJOR.MINOR.PATCH" % tag]
    problems = []
    for name, found in read_versions(root).items():
        if found is None:
            problems.append("%s: no version found" % name)
        elif found != expected:
            problems.append("%s says %s but the tag says %s" % (name, found, expected))
    return problems


def main(argv: list[str]) -> int:
    if len(argv) not in (2, 3):
        print(__doc__, file=sys.stderr)
        return 2
    tag = argv[1]
    root = Path(argv[2]) if len(argv) == 3 else Path(".")
    problems = check(tag, root)
    if problems:
        print("Release %s is NOT consistent; nothing will be published:" % tag, file=sys.stderr)
        for p in problems:
            print("  - " + p, file=sys.stderr)
        return 1
    print("Release %s matches pyproject.toml, __init__.py, CITATION.cff and .zenodo.json." % tag)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
