"""Pure rules to read pickups and build the operational summary."""

import json
from functools import reduce
from pathlib import Path

from simple_report_pipeline.formatting import PRIORITY_LABELS, STATUS_LABELS

PRIORITIES = tuple(PRIORITY_LABELS)
STATUSES = tuple(STATUS_LABELS)
REQUIRED_KEYS = ("id", "customer_name", "address", "package_count", "priority", "status")


class ReportError(Exception):
    """The pickups file cannot be turned into a report."""


def is_valid_pickup(pickup: object) -> bool:
    """Tell whether a record has the expected format."""
    if not isinstance(pickup, dict) or not all(key in pickup for key in REQUIRED_KEYS):
        return False
    count = pickup["package_count"]
    return (
        isinstance(pickup["id"], int)
        and isinstance(count, int)
        and not isinstance(count, bool)
        and count > 0
        and pickup["priority"] in PRIORITIES
        and pickup["status"] in STATUSES
    )


def load_pickups(path: Path) -> list[dict]:
    """Read and validate the pickups file; raise ReportError if it is unusable."""
    try:
        records = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as error:
        raise ReportError(f"Não foi possível ler {path}: {error.strerror}") from error
    except ValueError as error:
        raise ReportError(f"JSON inválido em {path}") from error
    if not isinstance(records, list) or not all(map(is_valid_pickup, records)):
        raise ReportError(f"Coletas em formato inválido em {path}")
    return records


def count_by(pickups: list[dict], field: str, categories: tuple[str, ...]) -> dict:
    """Count pickups per category of a field, including categories with 0."""
    return reduce(
        lambda acc, pickup: {**acc, pickup[field]: acc[pickup[field]] + 1},
        pickups,
        {category: 0 for category in categories},
    )


def build_summary(pickups: list[dict]) -> dict:
    """Build the operational summary of the pickups."""
    return {
        "total_pickups": len(pickups),
        "total_packages": reduce(lambda acc, p: acc + p["package_count"], pickups, 0),
        "by_priority": count_by(pickups, "priority", PRIORITIES),
        "by_status": count_by(pickups, "status", STATUSES),
    }
