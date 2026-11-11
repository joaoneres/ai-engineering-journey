"""Interactive menu for FilaFácil Logística."""

import logging

import cli
from constants import LOG_FILE, PRIORITY_LABELS, STATUS_LABELS
from pickups import (
    build_summary,
    filter_by_priority,
    filter_by_status,
    find_by_id,
    list_pickups,
    register_pickup,
    update_status,
)
from storage import load_pickups, save_pickups


def show_menu() -> None:
    """Print the main menu."""
    print("\n=== FilaFácil Logística ===")
    print("1. Cadastrar coleta")
    print("2. Listar coletas")
    print("3. Filtrar por status")
    print("4. Filtrar por prioridade")
    print("5. Atualizar status")
    print("6. Resumo operacional")
    print("0. Sair")


def create_pickup(pickups: list[dict]) -> list[dict]:
    """Read the data, register and save the pickup; return the updated list."""
    customer_name = cli.read_text("Nome do cliente")
    address = cli.read_text("Endereço")
    package_count = cli.read_int("Quantidade de pacotes")
    priority = cli.read_option("Prioridade:", PRIORITY_LABELS)
    try:
        updated = register_pickup(pickups, customer_name, address, package_count, priority)
    except ValueError as error:
        cli.print_message(str(error))
        return pickups
    try:
        save_pickups(updated)
    except OSError:
        cli.print_message("Não foi possível salvar a coleta. Tente novamente.")
        return pickups
    new_pickup = updated[-1]
    logging.info("Coleta cadastrada: id=%s cliente=%s", new_pickup["id"], new_pickup["customer_name"])
    cli.print_message(f"Coleta #{new_pickup['id']} cadastrada")
    return updated


def show_by_status(pickups: list[dict]) -> None:
    """Ask for a status and show the matching pickups."""
    status = cli.read_option("Status:", STATUS_LABELS)
    cli.print_table(filter_by_status(pickups, status))


def show_by_priority(pickups: list[dict]) -> None:
    """Ask for a priority and show the matching pickups."""
    priority = cli.read_option("Prioridade:", PRIORITY_LABELS)
    cli.print_table(filter_by_priority(pickups, priority))


def change_status(pickups: list[dict]) -> list[dict]:
    """Update the status of a pickup and save; return the updated list."""
    pickup_id = cli.read_int("ID da coleta")
    pickup = find_by_id(pickups, pickup_id)
    if pickup is None:
        cli.print_message(f"Coleta #{pickup_id} não encontrada")
        return pickups
    cli.print_table([pickup])
    new_status = cli.read_option("Novo status:", STATUS_LABELS)
    try:
        updated = update_status(pickups, pickup_id, new_status)
    except (ValueError, LookupError) as error:
        cli.print_message(str(error))
        return pickups
    try:
        save_pickups(updated)
    except OSError:
        cli.print_message("Não foi possível salvar a alteração. Tente novamente.")
        return pickups
    logging.info(
        "Status atualizado: id=%s de %s para %s", pickup_id, pickup["status"], new_status
    )
    cli.print_message(
        f"Status da coleta #{pickup_id} atualizado para {STATUS_LABELS[new_status]}"
    )
    return updated


def main() -> None:
    """Run the menu loop until the user quits."""
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logging.info("Sistema iniciado")
    pickups = load_pickups()
    try:
        while True:
            show_menu()
            option = input("Escolha uma opção: ").strip()
            if option == "0":
                cli.print_message("Até logo!")
                break
            elif option == "1":
                pickups = create_pickup(pickups)
            elif option == "2":
                cli.print_table(list_pickups(pickups))
            elif option == "3":
                show_by_status(pickups)
            elif option == "4":
                show_by_priority(pickups)
            elif option == "5":
                pickups = change_status(pickups)
            elif option == "6":
                cli.print_summary(build_summary(pickups))
            else:
                cli.print_message("Opção inválida. Tente novamente.")
    except (KeyboardInterrupt, EOFError):
        print()
        cli.print_message("Encerrado pelo usuário. Até logo!")
    finally:
        logging.info("Sistema encerrado")


if __name__ == "__main__":
    main()
