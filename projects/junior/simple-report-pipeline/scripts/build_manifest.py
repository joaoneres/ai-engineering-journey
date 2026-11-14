"""Write dist/manifest.json: what was built, from which commit, and for which environment.

Usage: python scripts/build_manifest.py --environment dev [--dist dist] [--status built]
Exit codes: 0 ok, 2 no artifacts found.
"""

import argparse
import json
import sys
from pathlib import Path

from _common import (
    ARTIFACT_SUFFIXES,
    ENVIRONMENTS,
    ROOT,
    git_commit,
    read_project,
    sha256_file,
)


def list_artifacts(dist: Path) -> list[Path]:
    """Return the wheel and the source distribution found in dist/."""
    return sorted(p for p in dist.glob("*") if p.name.endswith(ARTIFACT_SUFFIXES))


def build_manifest(dist: Path, environment: str, status: str, commit: str) -> dict:
    """Build the manifest with the six traceability fields plus the file checksums."""
    project = read_project()
    return {
        "project": project["name"],
        "version": project["version"],
        "commit": commit,
        "environment": environment,
        "published_at": None,
        "status": status,
        "files": {path.name: sha256_file(path) for path in list_artifacts(dist)},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dist", type=Path, default=ROOT / "dist")
    parser.add_argument("--environment", choices=ENVIRONMENTS, required=True)
    parser.add_argument("--status", default="built")
    args = parser.parse_args(argv)
    manifest = build_manifest(args.dist, args.environment, args.status, git_commit())
    if not manifest["files"]:
        print(f"[build] nenhum artefato (.whl/.tar.gz) em {args.dist}", file=sys.stderr)
        return 2
    target = args.dist / "manifest.json"
    target.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        f"[build] manifest gravado: {manifest['project']} {manifest['version']} "
        f"commit {manifest['commit'][:7]} ambiente {manifest['environment']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
