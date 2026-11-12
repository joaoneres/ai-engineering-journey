"""Data access: the only module that reads and writes the pickups file."""

import json
import logging
from pathlib import Path

from constants import DATA_FILE

DATA_PATH = Path(__file__).parent / DATA_FILE


class RepositoryError(Exception):
    """The pickups could not be written to the data file."""


def find_all() -> list:
    """Read the raw records; return an empty list if the file is missing or unreadable."""
    if not DATA_PATH.exists():
        logging.info("Arquivo %s não encontrado; iniciando sem coletas", DATA_PATH.name)
        return []
    try:
        with open(DATA_PATH, encoding="utf-8") as file:
            records = json.load(file)
    except (OSError, ValueError):
        logging.warning("Arquivo %s ilegível, vazio ou com JSON inválido", DATA_PATH.name)
        return []
    if not isinstance(records, list):
        logging.warning("Arquivo %s não contém uma lista de coletas", DATA_PATH.name)
        return []
    return records


def save_all(pickups: list[dict]) -> None:
    """Write all pickups to the file; raise RepositoryError if it fails."""
    try:
        with open(DATA_PATH, "w", encoding="utf-8") as file:
            json.dump(pickups, file, indent=2, ensure_ascii=False)
    except OSError as error:
        logging.error("Falha ao gravar %s", DATA_PATH.name, exc_info=True)
        raise RepositoryError(f"Falha ao gravar {DATA_PATH.name}") from error
    logging.info("%d coleta(s) salva(s)", len(pickups))
