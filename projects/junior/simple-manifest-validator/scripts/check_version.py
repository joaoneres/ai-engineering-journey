"""Fail when the version is not semantic, or when a tag does not match it.

Local runs have no tag, so they only check the version in pyproject.toml.
On GitHub, a tag build must be named simple-manifest-vX.Y.Z for that version.
"""

import os
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
TAG_PREFIX = "simple-manifest-v"


def read_version(root: Path = ROOT) -> str:
    """Return the project version from pyproject.toml."""
    with (root / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)["project"]["version"]


def expected_tag(version: str) -> str:
    """Return the git tag that marks this version."""
    return f"{TAG_PREFIX}{version}"


def main() -> int:
    """Check the version, and the tag when this run was started by one."""
    version = read_version()
    if not SEMVER.fullmatch(version):
        print(f"invalid version: {version}", file=sys.stderr)
        return 1
    if os.environ.get("GITHUB_REF_TYPE") == "tag":
        tag = os.environ.get("GITHUB_REF_NAME", "")
        if tag != expected_tag(version):
            print(f"tag {tag} does not match {expected_tag(version)}", file=sys.stderr)
            return 1
    print(f"version {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
