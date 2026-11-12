"""Interactive menu: reads input, calls the services and prints the results."""

import logging
from collections.abc import Callable

from constants import LOG_FILE, PRIORITY_LABELS, STATUS_LABELS
from domain import pickups as rules
from errors import FilaFacilError
from services import pickup_service
from storage import json_storage
from ui import cli

MENU_OPTIONS = (
    "1. Cadastrar coleta",
    "2. Listar coletas",
    "3. Filtrar por status",
    "4. Filtrar por prioridade",
    "5. Atualizar status",
    "6. Resumo operacional",
    "0. Sair",
)


def show_menu() -> None:
    """Print the main menu."""
    print("\n=== FilaFácil Logística ===")
    print("\n".join(MENU_OPTIONS))


def create_pickup(pickups: list[dict]) -> list[dict]:
    """Read the data and register the pickup."""
    customer_name = cli.read_text("Nome do cliente")
    address = cli.read_text("Endereço")
    package_count = cli.read_int("Quantidade de pacotes")
    priority = cli.read_option("Prioridade:", PRIORITY_LABELS)
    updated = pickup_service.create_pickup(pickups, customer_name, address, package_count, priority)
    cli.print_message(f"Coleta #{updated[-1]['id']} cadastrada")
    return updated


def show_filtered(pickups: list[dict], field: str, title: str, labels: dict) -> list[dict]:
    """Ask for a value of the field and show the matching pickups."""
    value = cli.read_option(title, labels)
    cli.print_table(rules.filter_by(pickups, field, value))
    return pickups


def change_status(pickups: list[dict]) -> list[dict]:
    """Ask for the pickup and the new status, then update it."""
    pickup_id = cli.read_int("ID da coleta")
    pickup = rules.find_by_id(pickups, pickup_id)
    if pickup is None:
        raise rules.NotFoundError(f"Coleta #{pickup_id} não encontrada")
    cli.print_table([pickup])
    new_status = cli.read_option("Novo status:", STATUS_LABELS)
    updated = pickup_service.change_status(pickups, pickup_id, new_status)
    cli.print_message(
        f"Status da coleta #{pickup_id} atualizado para {STATUS_LABELS[new_status]}"
    )
    return updated


def show_all(pickups: list[dict]) -> list[dict]:
    """Show every pickup sorted by id."""
    cli.print_table(rules.list_pickups(pickups))
    return pickups


def show_summary(pickups: list[dict]) -> list[dict]:
    """Show the operational summary."""
    cli.print_summary(rules.build_summary(pickups))
    return pickups


ACTIONS: dict[str, Callable[[list[dict]], list[dict]]] = {
    "1": create_pickup,
    "2": show_all,
    "3": lambda p: show_filtered(p, "status", "Status:", STATUS_LABELS),
    "4": lambda p: show_filtered(p, "priority", "Prioridade:", PRIORITY_LABELS),
    "5": change_status,
    "6": show_summary,
}


def run_action(action: Callable, pickups: list[dict]) -> list[dict]:
    """Run an action; on an expected error show it and keep the current list."""
    try:
        return action(pickups)
    except FilaFacilError as error:
        cli.print_message(str(error))
        return pickups


def run() -> None:
    """Run the menu loop until the user quits."""
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logging.info("Sistema iniciado")
    pickups = json_storage.load_pickups()
    try:
        while True:
            show_menu()
            option = input("Escolha uma opção: ").strip()
            if option == "0":
                cli.print_message("Até logo!")
                break
            action = ACTIONS.get(option)
            if action is None:
                cli.print_message("Opção inválida. Tente novamente.")
            else:
                pickups = run_action(action, pickups)
    except (KeyboardInterrupt, EOFError):
        print()
        cli.print_message("Encerrado pelo usuário. Até logo!")
    finally:
        logging.info("Sistema encerrado")
