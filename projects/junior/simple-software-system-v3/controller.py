"""Controller: reads the terminal commands and delegates to the service."""

import cli
import service
from constants import PRIORITY_LABELS, STATUS_LABELS


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


def create_pickup() -> None:
    """Read the data and ask the service to register the pickup."""
    customer_name = cli.read_text("Nome do cliente")
    address = cli.read_text("Endereço")
    package_count = cli.read_int("Quantidade de pacotes")
    priority = cli.read_option("Prioridade:", PRIORITY_LABELS)
    try:
        new_pickup = service.register_pickup(customer_name, address, package_count, priority)
    except ValueError as error:
        cli.print_message(str(error))
    except service.SaveError:
        cli.print_message("Não foi possível salvar a coleta. Tente novamente.")
    else:
        cli.print_message(f"Coleta #{new_pickup['id']} cadastrada")


def show_filtered(field: str, prompt: str, labels: dict[str, str]) -> None:
    """Ask for a value of the field and show the matching pickups."""
    value = cli.read_option(prompt, labels)
    cli.print_table(service.filter_by(field, value))


def change_status() -> None:
    """Ask for a pickup and a new status and ask the service to update it."""
    pickup_id = cli.read_int("ID da coleta")
    pickup = service.find_pickup(pickup_id)
    if pickup is None:
        cli.print_message(f"Coleta #{pickup_id} não encontrada")
        return
    cli.print_table([pickup])
    new_status = cli.read_option("Novo status:", STATUS_LABELS)
    try:
        service.change_status(pickup_id, new_status)
    except (ValueError, LookupError) as error:
        cli.print_message(str(error))
    except service.SaveError:
        cli.print_message("Não foi possível salvar a alteração. Tente novamente.")
    else:
        cli.print_message(
            f"Status da coleta #{pickup_id} atualizado para {STATUS_LABELS[new_status]}"
        )


ACTIONS = {
    "1": create_pickup,
    "2": lambda: cli.print_table(service.list_pickups()),
    "3": lambda: show_filtered("status", "Status:", STATUS_LABELS),
    "4": lambda: show_filtered("priority", "Prioridade:", PRIORITY_LABELS),
    "5": change_status,
    "6": lambda: cli.print_summary(service.get_summary()),
}


def run() -> None:
    """Run the menu loop until the user quits."""
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
                action()
    except (KeyboardInterrupt, EOFError):
        print()
        cli.print_message("Encerrado pelo usuário. Até logo!")
