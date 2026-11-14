"""Publish the built artifacts to an environment, safely and without duplicating.

Steps: read manifest -> verify checksums -> check secrets -> skip if already published
-> write the registry entry (and a GitHub Release when building a tag).

Usage: python scripts/publish.py --environment homolog [--destination local|github] [--tag T]
Exit codes: 0 published or already published, 2 bad manifest, 3 secret missing,
4 checksum mismatch, 5 publication failed.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from _common import ENVIRONMENTS, ROOT, load_config, sha256_file, tag_from_environment, utc_now

EXIT_MANIFEST, EXIT_SECRET, EXIT_CHECKSUM, EXIT_PUBLISH = 2, 3, 4, 5


class PublishError(Exception):
    """A publication step failed; carries the process exit code."""

    def __init__(self, message: str, code: int) -> None:
        super().__init__(message)
        self.code = code


def log(message: str) -> None:
    print(f"[publicar] {message}", flush=True)


def load_manifest(dist: Path) -> dict:
    try:
        manifest = json.loads((dist / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise PublishError(f"manifest.json ausente ou inválido em {dist}", EXIT_MANIFEST) from error
    if manifest.get("status") != "built" or not manifest.get("files"):
        raise PublishError("manifest sem status 'built' ou sem arquivos", EXIT_MANIFEST)
    return manifest


def verify_checksums(dist: Path, manifest: dict) -> None:
    for name, expected in manifest["files"].items():
        path = dist / name
        if not path.exists() or sha256_file(path) != expected:
            raise PublishError(f"checksum diverge ou arquivo ausente: {name}", EXIT_CHECKSUM)
    log(f"checksums ok ({len(manifest['files'])} arquivos)")


def check_secrets(config: dict, environment: str, destination: str, environ=os.environ) -> None:
    """Fail naming the missing secrets. Values are never printed."""
    required = []
    if config.get("REQUIRE_PUBLISH_TOKEN") == "true":
        required.append(("PUBLISH_TOKEN", ("PUBLISH_TOKEN",)))
    if destination == "github":
        required.append(("GITHUB_TOKEN", ("GH_TOKEN", "GITHUB_TOKEN")))
    for label, names in required:
        if not any(environ.get(name) for name in names):
            raise PublishError(
                f"secret ausente: {label} (obrigatório no ambiente {environment})", EXIT_SECRET
            )
        log(f"secret {label}: presente (valor oculto)")


def publication_id(manifest: dict, environment: str) -> str:
    return f"{environment}-{manifest['version']}-{manifest['commit'][:7]}"


def gh(args: list[str], runner=subprocess.run) -> subprocess.CompletedProcess:
    return runner(["gh", *args], capture_output=True, text=True)


def already_published(
    pub_id: str,
    registry: Path,
    destination: str,
    tag: str | None,
    environment: str,
    runner=subprocess.run,
) -> bool:
    if (registry / environment / pub_id).exists():
        return True
    if destination != "github":
        return False
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    found = gh(
        ["api", f"repos/{repo}/actions/artifacts?name=registry-{pub_id}", "--jq", ".total_count"],
        runner,
    )
    if found.returncode == 0 and found.stdout.strip() not in ("", "0"):
        return True
    return bool(tag) and gh(["release", "view", tag], runner).returncode == 0


def write_registry_entry(dist: Path, manifest: dict, target: Path) -> Path:
    target.mkdir(parents=True, exist_ok=False)
    for name in manifest["files"]:
        shutil.copy2(dist / name, target / name)
    published = {**manifest, "status": "published", "published_at": utc_now()}
    (target / "manifest.json").write_text(json.dumps(published, indent=2) + "\n", encoding="utf-8")
    return target


def create_release(tag: str, entry: Path, runner=subprocess.run) -> None:
    files = [str(path) for path in sorted(entry.iterdir())]
    result = gh(["release", "create", tag, *files, "--title", tag, "--generate-notes"], runner)
    if result.returncode != 0:
        raise PublishError(f"falha ao criar a Release {tag}: {result.stderr.strip()}", EXIT_PUBLISH)


def set_output(name: str, value: str) -> None:
    """Expose a value to later workflow steps when running in GitHub Actions."""
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as file:
            file.write(f"{name}={value}\n")


def publish(dist: Path, registry: Path, environment: str, destination: str, tag: str | None) -> int:
    manifest = load_manifest(dist)
    verify_checksums(dist, manifest)
    check_secrets(load_config(environment), environment, destination)
    pub_id = publication_id(manifest, environment)
    set_output("publication_id", pub_id)
    if already_published(pub_id, registry, destination, tag, environment):
        log(f"{pub_id} já publicado; nada a fazer (sem duplicar)")
        set_output("already_published", "true")
        return 0
    entry = write_registry_entry(dist, manifest, registry / environment / pub_id)
    if destination == "github" and tag:
        create_release(tag, entry)
        log(f"Release {tag} criada")
    set_output("already_published", "false")
    set_output("registry_dir", str(entry))
    log(f"{pub_id} publicado em {entry}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dist", type=Path, default=ROOT / "dist")
    parser.add_argument("--registry", type=Path, default=ROOT / "registry")
    parser.add_argument("--environment", choices=ENVIRONMENTS, required=True)
    parser.add_argument("--destination", choices=("local", "github"), default="local")
    parser.add_argument("--tag", default=None)
    args = parser.parse_args(argv)
    try:
        return publish(
            args.dist,
            args.registry,
            args.environment,
            args.destination,
            args.tag or tag_from_environment(),
        )
    except PublishError as error:
        print(f"[publicar] ERRO: {error}", file=sys.stderr)
        return error.code


if __name__ == "__main__":
    sys.exit(main())
