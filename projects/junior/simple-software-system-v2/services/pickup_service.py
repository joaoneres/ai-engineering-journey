"""Use cases: call the API, apply a business rule, persist the result and log it."""

import logging

from domain import pickups as rules
from integrations import cep_client
from storage import json_storage as storage


async def lookup_location(cep: str, transport=cep_client.http_get) -> dict:
    """Query the CEP API; raise ApiError (or InputError for a bad CEP)."""
    location = await cep_client.fetch_address(cep, transport)
    logging.info("CEP %s consultado com sucesso", location["cep"])
    return location


async def create_pickup(
    pickups: list[dict],
    customer_name: str,
    address: str,
    package_count: int,
    priority: str,
    location: dict | None = None,
) -> list[dict]:
    """Register a pickup and save the list; return the updated list."""
    updated = rules.register_pickup(
        pickups, customer_name, address, package_count, priority, location
    )
    await storage.save_pickups(updated)
    new_pickup = updated[-1]
    logging.info(
        "Coleta cadastrada: id=%s cliente=%s enriquecida=%s",
        new_pickup["id"], new_pickup["customer_name"], new_pickup["enriched"],
    )
    return updated


async def change_status(pickups: list[dict], pickup_id: int, new_status: str) -> list[dict]:
    """Update a pickup status and save the list; return the updated list."""
    previous = rules.find_by_id(pickups, pickup_id)
    updated = rules.update_status(pickups, pickup_id, new_status)
    await storage.save_pickups(updated)
    logging.info(
        "Status atualizado: id=%s de %s para %s", pickup_id, previous["status"], new_status
    )
    return updated
