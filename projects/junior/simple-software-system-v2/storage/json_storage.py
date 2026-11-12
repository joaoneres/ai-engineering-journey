"""Pickup persistence in a JSON file (the only module that touches the file)."""

import json
import logging
from pathlib import Path

from constants import DATA_FILE
from domain.pickups import is_valid_pickup
from errors import FileError

DATA_PATH = Path(__file__).resolve().parent.parent / DATA_FILE


def load_pickups(path: Path = DATA_PATH) -> list[dict]:
    """Read the pickups from the file; return an empty list if missing or invalid."""
    if not path.exists():
        logging.info("Arquivo %s não encontrado; iniciando sem coletas", path.name)
        return []
    try:
        with open(path, encoding="utf-8") as file:
            pickups = json.load(file)
    except (OSError, ValueError):
        logging.warning("Arquivo %s ilegível, vazio ou com JSON inválido", path.name)
        return []
    if not isinstance(pickups, list) or not all(map(is_valid_pickup, pickups)):
        logging.warning("Arquivo %s com coletas em formato inválido", path.name)
        return []
    return pickups


def save_pickups(pickups: list[dict], path: Path = DATA_PATH) -> None:
    """Write the pickups to the file; raise FileError after logging a failure."""
    try:
        with open(path, "w", encoding="utf-8") as file:
            json.dump(pickups, file, indent=2, ensure_ascii=False)
    except OSError as error:
        logging.error("Falha ao gravar %s", path.name, exc_info=True)
        raise FileError(f"Não foi possível salvar os dados em {path.name}.") from error
    logging.info("%d coleta(s) salva(s)", len(pickups))
