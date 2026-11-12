"""Smoke test: run the real app with scripted input and compare the terminal output.

The expected output (smoke_expected.txt) was recorded from the Module 1 code, so a
match proves the layered refactor kept the behavior. The app runs from a temporary
copy of the code, so the real pickups.json and filafacil.log are never touched.

Usage:
    python smoke_test.py            # compare with smoke_expected.txt
    python smoke_test.py --record   # (re)write smoke_expected.txt
    python smoke_test.py <dir>      # run against another project folder
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
EXPECTED = HERE / "smoke_expected.txt"

FIRST_SESSION = [
    "1", "Ana Souza", "Rua A, 10", "abc", "3", "3",
    "1", "", "Bruno Lima", "Av. Central, 500 - Sala 12 - Edifício Comercial Grande",
    "-1", "2", "9", "2",
    "1", "Carla Dias", "Rua C, 3", "5", "1",
    "2", "3", "1", "4", "3",
    "5", "99", "5", "1", "2", "5", "2", "3", "5", "1", "2",
    "6", "7", "0",
]
SECOND_SESSION = ["2", "6", "0"]
CORRUPTED_SESSION = ["2", "0"]
INTERRUPTED_SESSION = ["2"]  # input ends without "0": exercises the EOF path


def run_app(workdir: Path, lines: list[str]) -> str:
    """Run main.py in workdir feeding the lines as input; return stdout."""
    result = subprocess.run(
        [sys.executable, "main.py"],
        cwd=workdir,
        input="\n".join(lines) + "\n",
        capture_output=True,
        text=True,
        timeout=30,
    )
    return f"--- exit code {result.returncode}\n{result.stdout}{result.stderr}"


def run_all(project: Path) -> str:
    """Run every scripted session against a temporary copy of the project."""
    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        for file in project.glob("*.py"):
            shutil.copy(file, workdir)
        for folder in project.iterdir():
            if folder.is_dir() and (folder / "__init__.py").exists():
                shutil.copytree(folder, workdir / folder.name)
        outputs = [run_app(workdir, FIRST_SESSION), run_app(workdir, SECOND_SESSION)]
        (workdir / "pickups.json").write_text("{ not json", encoding="utf-8")
        outputs.append(run_app(workdir, CORRUPTED_SESSION))
        outputs.append(run_app(workdir, INTERRUPTED_SESSION))
    return "\n".join(outputs)


def main() -> int:
    args = sys.argv[1:]
    record = "--record" in args
    folders = [arg for arg in args if not arg.startswith("--")]
    project = Path(folders[0]).resolve() if folders else HERE
    actual = run_all(project)
    if record:
        EXPECTED.write_text(actual, encoding="utf-8")
        print(f"Saída de referência gravada em {EXPECTED.name}")
        return 0
    if actual == EXPECTED.read_text(encoding="utf-8"):
        print("OK: a saída do terminal é idêntica à referência do Módulo 1.")
        return 0
    print("FALHOU: a saída difere da referência. Diferenças:")
    import difflib

    expected = EXPECTED.read_text(encoding="utf-8").splitlines()
    for line in difflib.unified_diff(expected, actual.splitlines(), "esperado", "atual", lineterm=""):
        print(line)
    return 1


if __name__ == "__main__":
    sys.exit(main())
