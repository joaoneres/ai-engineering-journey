"""Helpers shared by the release scripts (stdlib only)."""

import hashlib
import os
import re
import subprocess
import tomllib
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TAG_PREFIX = "simple-report-v"
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
ENVIRONMENTS = ("dev", "homolog", "prod")
ARTIFACT_SUFFIXES = (".whl", ".tar.gz")


def read_project(root: Path = ROOT) -> dict:
    """Return the [project] table of pyproject.toml."""
    with open(root / "pyproject.toml", "rb") as file:
        return tomllib.load(file)["project"]


def sha256_file(path: Path) -> str:
    """Return the SHA-256 of a file."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git_commit(root: Path = ROOT) -> str:
    """Return the full commit SHA (CI variable first, then git)."""
    if os.environ.get("GITHUB_SHA"):
        return os.environ["GITHUB_SHA"]
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return result.stdout.strip()


def utc_now() -> str:
    """Return the current UTC time as ISO 8601."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_config(environment: str, root: Path = ROOT) -> dict[str, str]:
    """Read config/<environment>.env as a dict."""
    config = {}
    for line in (root / "config" / f"{environment}.env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            config[key.strip()] = value.strip()
    return config


def tag_from_environment() -> str | None:
    """Return the tag name when the CI run was triggered by a tag."""
    if os.environ.get("GITHUB_REF_TYPE") == "tag":
        return os.environ.get("GITHUB_REF_NAME")
    return None


def project_version() -> str:
    """Return the project version from pyproject.toml."""
    return read_project()["version"]
