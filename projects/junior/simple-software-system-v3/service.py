"""Business rules for pickups. Uses the repository; knows nothing about the terminal."""

import logging
from functools import reduce

import repository
from constants import DATA_FILE, INITIAL_STATUS, PRIORITIES, STATUSES

class SaveError(Exception):
    """The pickups could not be saved."""


FILTER_OPTIONS = {
    "status": (STATUSES, "Status inválido."),
    "priority": (PRIORITIES, "Prioridade inválida."),
}


# --- Pure rules (no I/O) ---------------------------------------------------


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


def with_new_pickup(
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


def with_new_status(pickups: list[dict], pickup_id: int, new_status: str) -> list[dict]:
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


def find_by_id(pickups: list[dict], pickup_id: int) -> dict | None:
    """Return the pickup with the given id, or None if it does not exist."""
    return next(filter(lambda p: p["id"] == pickup_id, pickups), None)


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


# --- Use cases (what the controller calls) ---------------------------------


def save_pickups(pickups: list[dict]) -> None:
    """Save through the repository; raise SaveError if it fails."""
    try:
        repository.save_all(pickups)
    except repository.RepositoryError as error:
        raise SaveError("Não foi possível salvar as coletas.") from error


def load_pickups() -> list[dict]:
    """Read the pickups; discard everything if any stored record is invalid."""
    records = repository.find_all()
    if not all(map(is_valid_pickup, records)):
        logging.warning("Arquivo %s com coletas em formato inválido", DATA_FILE)
        return []
    return records


def list_pickups() -> list[dict]:
    """Return all pickups sorted by id."""
    return sorted(load_pickups(), key=lambda pickup: pickup["id"])


def filter_by(field: str, value: str) -> list[dict]:
    """Return the pickups whose field ("status" or "priority") equals value."""
    allowed, message = FILTER_OPTIONS[field]
    if value not in allowed:
        raise ValueError(message)
    return list(filter(lambda p: p[field] == value, load_pickups()))


def find_pickup(pickup_id: int) -> dict | None:
    """Return the pickup with the given id, or None if it does not exist."""
    return find_by_id(load_pickups(), pickup_id)


def register_pickup(
    customer_name: str, address: str, package_count: int, priority: str
) -> dict:
    """Validate, save and return the new pickup."""
    updated = with_new_pickup(
        load_pickups(), customer_name, address, package_count, priority
    )
    save_pickups(updated)
    new_pickup = updated[-1]
    logging.info(
        "Coleta cadastrada: id=%s cliente=%s", new_pickup["id"], new_pickup["customer_name"]
    )
    return new_pickup


def change_status(pickup_id: int, new_status: str) -> None:
    """Update and save the status of a pickup."""
    pickups = load_pickups()
    updated = with_new_status(pickups, pickup_id, new_status)
    save_pickups(updated)
    logging.info(
        "Status atualizado: id=%s de %s para %s",
        pickup_id,
        find_by_id(pickups, pickup_id)["status"],
        new_status,
    )


def get_summary() -> dict:
    """Return the operational summary of all pickups."""
    return build_summary(load_pickups())
