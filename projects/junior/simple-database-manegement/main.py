"""Ponto de entrada: cria a tabela e abre o menu."""

from controller.pickup_controller import PickupController
from database import create_tables
from repository.pickup_repository import PickupRepository
from service.pickup_service import PickupService


def main() -> None:
    """Monta as camadas (repository -> service -> controller) e inicia o menu."""
    create_tables()
    controller = PickupController(PickupService(PickupRepository()))
    controller.run()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nEncerrado pelo usuário. Até logo!")
