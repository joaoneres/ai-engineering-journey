"""Run integration and build on this machine, in the same order as the workflow.

Usage: python scripts/run_local.py [--stage integration|build] [--install]
The run stops at the first failure and reports the next stage as skipped.
Exit code: that of the first failing command, or 0.
The GitHub Release is created only by the workflow, on a version tag.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
PREFIX = "simple-manifest-validator"


def build_stages(install: bool) -> dict[str, list[tuple[str, list[str]]]]:
    """Return {stage: [(step label, command)]}, mirroring the GitHub workflow jobs."""
    setup = [
        ("Install dependencies", [PY, "-m", "pip", "install", "-q", "-r", "requirements-dev.txt"]),
        ("Install the package", [PY, "-m", "pip", "install", "-q", "-e", "."]),
    ]
    return {
        "integration": (setup if install else [])
        + [
            ("Check formatting", [PY, "-m", "ruff", "format", "--check", "."]),
            ("Lint", [PY, "-m", "ruff", "check", "."]),
            ("Static check", [PY, "-m", "compileall", "-q", "src", "tests", "scripts"]),
            ("Unit tests", [PY, "-m", "unittest", "discover", "-s", "tests", "-t", "."]),
            (
                "Run the CLI on the JSON sample",
                [PY, "-m", "simple_manifest_validator", "samples/manifest.json"],
            ),
            (
                "Run the CLI on the CSV sample",
                [PY, "-m", "simple_manifest_validator", "samples/manifest.csv"],
            ),
        ],
        "build": [
            ("Check version", [PY, "scripts/check_version.py"]),
            (
                "Clean dist/",
                [PY, "-c", "import shutil; shutil.rmtree('dist', ignore_errors=True)"],
            ),
            ("Build wheel and sdist", [PY, "-m", "build"]),
            (
                "Check metadata",
                ["bash", "-c", f"{PY} -m twine check --strict dist/*.whl dist/*.tar.gz"],
            ),
        ],
    }


def run_command(command: list[str]) -> int:
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    return subprocess.run(command, cwd=ROOT, env=env, check=False).returncode


def run_stages(stages: dict, runner=run_command) -> tuple[list[tuple[str, str]], int]:
    """Run stages in order and stop at the first failure. Returns (results, exit code)."""
    results, code = [], 0
    for name, steps in stages.items():
        title = f"{PREFIX} · {name}"
        if code:
            results.append((title, "SKIPPED"))
            continue
        print(f"\n=== {title} ===", flush=True)
        for label, command in steps:
            print(f"--- {label}", flush=True)
            code = runner(command)
            if code:
                print(f"*** FAILED: {label} (exit {code})", flush=True)
                break
        results.append((title, "FAILED" if code else "OK"))
    return results, code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--stage", choices=("integration", "build"))
    parser.add_argument("--install", action="store_true", help="pip install the dev tools first")
    args = parser.parse_args(argv)
    stages = build_stages(args.install)
    if args.stage:
        stages = {args.stage: stages[args.stage]}
    results, code = run_stages(stages)
    print("\n=== Result ===")
    for title, status in results:
        print(f"{status:<7} {title}")
    return code


if __name__ == "__main__":
    sys.exit(main())
