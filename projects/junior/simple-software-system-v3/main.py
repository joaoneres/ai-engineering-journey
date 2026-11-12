"""Entry point for FilaFácil Logística."""

import logging

import controller
from constants import LOG_FILE


def main() -> None:
    """Configure logging and start the menu."""
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logging.info("Sistema iniciado")
    try:
        controller.run()
    finally:
        logging.info("Sistema encerrado")


if __name__ == "__main__":
    main()
