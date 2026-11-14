"""Check that the version is semantic and, for a tag build, that it matches the tag.

Usage: python scripts/check_version.py [--tag simple-report-v1.2.3]
Exit codes: 0 ok, 1 invalid or divergent version.
"""

import argparse
import sys

from _common import SEMVER, TAG_PREFIX, project_version, tag_from_environment


def check(version: str, tag: str | None) -> str | None:
    """Return an error message, or None if the version is valid for this build."""
    if not SEMVER.match(version):
        return f"versão {version!r} não é semântica (esperado X.Y.Z)"
    if tag is None:
        return None
    if not tag.startswith(TAG_PREFIX):
        return f"tag {tag!r} não começa com {TAG_PREFIX!r}"
    if tag.removeprefix(TAG_PREFIX) != version:
        return f"tag {tag!r} diverge da versão {version!r} do pyproject.toml"
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", default=None)
    args = parser.parse_args(argv)
    version = project_version()
    error = check(version, args.tag or tag_from_environment())
    if error:
        print(f"[build] versão inválida: {error}", file=sys.stderr)
        return 1
    print(f"[build] versão {version} ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
