"""Run the whole pipeline on this machine, in the same order as the GitHub workflow.

Each stage runs the same commands as the matching job and the run stops at the first
failure, so later stages are reported as skipped (like `needs` in the workflow).

Usage: python scripts/run_local.py [--env dev|homolog|prod] [--stage NAME] [--install]
Stages: qualidade, testes, build, publicar.
Exit code: that of the first failing command, or 0.
"""

import argparse
import os
import subprocess
import sys

from _common import ENVIRONMENTS, ROOT

PY = sys.executable
PREFIX = "simple-report-pipeline"


def build_stages(environment: str, install: bool) -> dict[str, list[tuple[str, list[str]]]]:
    """Return {stage: [(step label, command)]}, mirroring the GitHub workflow jobs."""
    setup = [
        ("Instalar dependências", [PY, "-m", "pip", "install", "-q", "-r", "requirements-dev.txt"])
    ]
    editable = [("Instalar o pacote", [PY, "-m", "pip", "install", "-q", "-e", "."])]
    return {
        "qualidade": (setup if install else [])
        + [
            ("Checar formatação (ruff format)", [PY, "-m", "ruff", "format", "--check", "."]),
            ("Lint (ruff check)", [PY, "-m", "ruff", "check", "."]),
            (
                "Análise estática (compileall)",
                [PY, "-m", "compileall", "-q", "src", "tests", "scripts"],
            ),
        ],
        "testes": (editable if install else [])
        + [("Testes unitários", [PY, "-m", "unittest", "discover", "-s", "tests", "-t", "."])],
        "build": [
            ("Checar versão", [PY, "scripts/check_version.py"]),
            (
                "Limpar dist/",
                [PY, "-c", "import shutil; shutil.rmtree('dist', ignore_errors=True)"],
            ),
            ("Build (wheel + sdist)", [PY, "-m", "build"]),
            ("Validar metadados (twine check)", [PY, "-m", "twine", "check", "--strict", "dist/*"]),
            (
                "Gerar manifest.json",
                [PY, "scripts/build_manifest.py", "--environment", environment],
            ),
        ],
        "publicar": [
            (
                "Publicar",
                [PY, "scripts/publish.py", "--environment", environment, "--destination", "local"],
            ),
        ],
    }


def run_command(command: list[str]) -> int:
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    return subprocess.run(command, cwd=ROOT, env=env).returncode


def run_stages(stages: dict, runner=run_command) -> tuple[list[tuple[str, str]], int]:
    """Run stages in order; stop at the first failure. Returns (results, exit code)."""
    results, code = [], 0
    for name, steps in stages.items():
        title = f"{PREFIX} · {name.capitalize()}"
        if code:
            results.append((title, "PULADO"))
            continue
        print(f"\n=== {title} ===", flush=True)
        for label, command in steps:
            print(f"--- {label}", flush=True)
            code = runner(command)
            if code:
                print(f"*** FALHOU: {label} (código {code})", flush=True)
                break
        results.append((title, "FALHOU" if code else "OK"))
    return results, code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--env", choices=ENVIRONMENTS, default="dev")
    parser.add_argument("--stage", choices=("qualidade", "testes", "build", "publicar"))
    parser.add_argument("--install", action="store_true", help="pip install the dev tools first")
    args = parser.parse_args(argv)
    stages = build_stages(args.env, args.install)
    if args.stage:
        stages = {args.stage: stages[args.stage]}
    results, code = run_stages(stages)
    print("\n=== Resultado ===")
    for title, status in results:
        print(f"{status:<7} {title}")
    return code


if __name__ == "__main__":
    sys.exit(main())
