"""Read a cargo manifest and report what is wrong with it."""

import csv
import json
from pathlib import Path

FIELDS = ("package", "route", "vehicle", "responsible", "status")


class ManifestError(Exception):
    """The manifest file cannot be read."""


def load_manifest(path: Path) -> list[dict]:
    """Read a JSON or CSV manifest. Raise ManifestError when the file is unusable."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ManifestError(f"Could not read {path}: {error.strerror}") from error
    suffix = path.suffix.lower()
    if suffix == ".json":
        return _load_json(text, path)
    if suffix == ".csv":
        return _load_csv(text, path)
    raise ManifestError(f"Unsupported file type: {path.name}")


def _load_json(text: str, path: Path) -> list[dict]:
    try:
        records = json.loads(text)
    except ValueError as error:
        raise ManifestError(f"Invalid JSON in {path}") from error
    if not isinstance(records, list) or not all(isinstance(item, dict) for item in records):
        raise ManifestError(f"Manifest must be a list of objects in {path}")
    return records


def _load_csv(text: str, path: Path) -> list[dict]:
    reader = csv.DictReader(text.splitlines())
    if not reader.fieldnames:
        raise ManifestError(f"CSV header missing in {path}")
    header = [(name or "").strip() for name in reader.fieldnames]
    reader.fieldnames = header
    missing = [field for field in FIELDS if field not in header]
    if missing:
        raise ManifestError(f"CSV header missing columns in {path}: {', '.join(missing)}")
    return [{field: (row.get(field) or "").strip() for field in FIELDS} for row in reader]


def _text(record: dict, field: str) -> str:
    """Return the stripped field, or an empty string when it is absent or not text."""
    value = record.get(field)
    if not isinstance(value, str):
        return ""
    return value.strip()


def validate(records: list[dict]) -> list[dict]:
    """Return one problem per broken field. The first copy of a package is kept."""
    problems: list[dict] = []
    seen: set[str] = set()
    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            problems.append({"record": index, "message": "invalid record"})
            continue
        package = _text(record, "package")
        if not package:
            problems.append({"record": index, "message": "missing package"})
        elif package in seen:
            problems.append({"record": index, "message": f"duplicate package {package}"})
        else:
            seen.add(package)
        if not _text(record, "route"):
            problems.append({"record": index, "message": "empty route"})
        if not _text(record, "vehicle"):
            problems.append({"record": index, "message": "missing vehicle"})
        if not _text(record, "responsible"):
            problems.append({"record": index, "message": "missing responsible"})
        if not _text(record, "status"):
            problems.append({"record": index, "message": "missing status"})
    return problems


def build_report(records: list[dict]) -> dict:
    """Build the validation report. Status is approved only when there are no problems."""
    problems = validate(records)
    return {
        "total_records": len(records),
        "total_errors": len(problems),
        "problems": problems,
        "status": "approved" if not problems else "rejected",
    }
