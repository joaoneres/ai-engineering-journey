"""Business rules for pickups."""

from functools import reduce

from constants import INITIAL_STATUS, PRIORITIES, STATUSES


def next_id(pickups: list[dict]) -> int:
    """Return the next available id (highest id + 1, or 1 if empty)."""
    return max((pickup["id"] for pickup in pickups), default=0) + 1


def validate_pickup_data(
    customer_name: str, address: str, package_count: int, priority: str
) -> None:
    """Raise ValueError if any pickup field is invalid."""
    if not isinstance(customer_name, str) or not customer_name.strip():
        raise ValueError("O nome do cliente não pode ficar vazio.")
    if not isinstance(address, str) or not address.strip():
        raise ValueError("O endereço não pode ficar vazio.")
    if (
        not isinstance(package_count, int)
        or isinstance(package_count, bool)
        or package_count <= 0
    ):
        raise ValueError("A quantidade de pacotes deve ser um inteiro maior que zero.")
    if priority not in PRIORITIES:
        raise ValueError("Prioridade inválida.")


def is_valid_pickup(pickup: object) -> bool:
    """Tell whether a record read from the file has the expected format."""
    keys = ("id", "customer_name", "address", "package_count", "priority", "status")
    if not isinstance(pickup, dict) or not all(key in pickup for key in keys):
        return False
    if not isinstance(pickup["id"], int) or pickup["status"] not in STATUSES:
        return False
    try:
        validate_pickup_data(
            pickup["customer_name"],
            pickup["address"],
            pickup["package_count"],
            pickup["priority"],
        )
    except ValueError:
        return False
    return True


def register_pickup(
    pickups: list[dict],
    customer_name: str,
    address: str,
    package_count: int,
    priority: str,
) -> list[dict]:
    """Validate and return a new list with the pickup added."""
    validate_pickup_data(customer_name, address, package_count, priority)
    new_pickup = {
        "id": next_id(pickups),
        "customer_name": customer_name.strip(),
        "address": address.strip(),
        "package_count": package_count,
        "priority": priority,
        "status": INITIAL_STATUS,
    }
    return [*pickups, new_pickup]


def list_pickups(pickups: list[dict]) -> list[dict]:
    """Return the pickups sorted by id."""
    return sorted(pickups, key=lambda pickup: pickup["id"])


def filter_by_status(pickups: list[dict], status: str) -> list[dict]:
    """Return the pickups with the given status."""
    if status not in STATUSES:
        raise ValueError("Status inválido.")
    return list(filter(lambda p: p["status"] == status, pickups))


def filter_by_priority(pickups: list[dict], priority: str) -> list[dict]:
    """Return the pickups with the given priority."""
    if priority not in PRIORITIES:
        raise ValueError("Prioridade inválida.")
    return list(filter(lambda p: p["priority"] == priority, pickups))


def find_by_id(pickups: list[dict], pickup_id: int) -> dict | None:
    """Return the pickup with the given id, or None if it does not exist."""
    return next(filter(lambda p: p["id"] == pickup_id, pickups), None)


def update_status(pickups: list[dict], pickup_id: int, new_status: str) -> list[dict]:
    """Return a new list with the pickup status updated."""
    if new_status not in STATUSES:
        raise ValueError("Status inválido.")
    pickup = find_by_id(pickups, pickup_id)
    if pickup is None:
        raise LookupError(f"Coleta #{pickup_id} não encontrada")
    if pickup["status"] == new_status:
        raise ValueError("A coleta já está com esse status.")
    return list(
        map(
            lambda p: {**p, "status": new_status} if p["id"] == pickup_id else p,
            pickups,
        )
    )


def count_by(pickups: list[dict], field: str, categories: tuple[str, ...]) -> dict:
    """Count pickups per category of a field, including categories with 0."""
    return reduce(
        lambda acc, p: {**acc, p[field]: acc[p[field]] + 1},
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
