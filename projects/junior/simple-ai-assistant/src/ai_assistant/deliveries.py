"""Read-only access to the shared (synthetic) deliveries base.

The base is the only external source the assistant may use besides the user's own words. It is
looked up by the code that the model extracted; the model never searches it by itself.
"""

import json
from pathlib import Path

from ai_assistant.library import PROJECT_ROOT

DATA_PATH = PROJECT_ROOT / "data" / "deliveries.json"


class DeliveryDataError(Exception):
    """The deliveries file is missing or invalid."""


def load_deliveries(path: Path = DATA_PATH) -> dict[str, dict[str, str]]:
    """Load the deliveries indexed by upper-case code."""
    try:
        records = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as error:
        raise DeliveryDataError(f"cannot read {Path(path).name}: {error.strerror}") from error
    except ValueError as error:
        raise DeliveryDataError(f"{Path(path).name} is not valid json") from error
    if not isinstance(records, list) or not all(
        isinstance(record, dict) and isinstance(record.get("code"), str) for record in records
    ):
        raise DeliveryDataError(f"{Path(path).name} must be a list of records with a 'code'")
    return {
        record["code"].strip().upper(): {k: str(v) for k, v in record.items()} for record in records
    }


def find_delivery(deliveries: dict[str, dict[str, str]], code: str | None) -> dict[str, str] | None:
    """Exact lookup by code, ignoring case and surrounding spaces."""
    if not code:
        return None
    return deliveries.get(code.strip().upper())
