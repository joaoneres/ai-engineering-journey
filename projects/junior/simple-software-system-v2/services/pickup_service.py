"""Use cases: apply a business rule, persist the result and log it."""

import logging

from domain import pickups as rules
from storage import json_storage as storage


def create_pickup(
    pickups: list[dict], customer_name: str, address: str, package_count: int, priority: str
) -> list[dict]:
    """Register a pickup and save the list; return the updated list."""
    updated = rules.register_pickup(pickups, customer_name, address, package_count, priority)
    storage.save_pickups(updated)
    new_pickup = updated[-1]
    logging.info("Coleta cadastrada: id=%s cliente=%s", new_pickup["id"], new_pickup["customer_name"])
    return updated


def change_status(pickups: list[dict], pickup_id: int, new_status: str) -> list[dict]:
    """Update a pickup status and save the list; return the updated list."""
    previous = rules.find_by_id(pickups, pickup_id)
    updated = rules.update_status(pickups, pickup_id, new_status)
    storage.save_pickups(updated)
    logging.info(
        "Status atualizado: id=%s de %s para %s", pickup_id, previous["status"], new_status
    )
    return updated
