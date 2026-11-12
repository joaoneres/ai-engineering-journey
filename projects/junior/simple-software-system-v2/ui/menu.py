"""Interactive menu: reads input, calls the services and keeps the AppState updated."""

import asyncio
import logging
from collections.abc import Awaitable, Callable

from constants import LOG_FILE, PRIORITY_LABELS, STATUS_LABELS
from domain import pickups as rules
from errors import ApiError, FilaFacilError, NotFoundError
from services import pickup_service
from state import app_state as app
from state.app_state import AppState
from storage import json_storage
from ui import cli

MENU_OPTIONS = (
    "1. Cadastrar coleta",
    "2. Listar coletas",
    "3. Filtrar por status",
    "4. Filtrar por prioridade",
    "5. Atualizar status",
    "6. Resumo operacional",
    "7. Limpar filtros",
    "0. Sair",
)
FILTER_LABELS = {"status": STATUS_LABELS, "priority": PRIORITY_LABELS}
FILTER_TITLES = {"status": "Status", "priority": "Prioridade"}


def show_menu() -> None:
    """Print the main menu."""
    print("\n=== FilaFácil Logística ===")
    print("\n".join(MENU_OPTIONS))


def describe_filters(filters: dict) -> str:
    """Describe the active filters, e.g. 'Status: Pendente | Prioridade: Alta'."""
    return " | ".join(
        f"{FILTER_TITLES[name]}: {FILTER_LABELS[name][value]}" for name, value in filters.items()
    )


async def ask_location(cep: str | None) -> tuple[bool, dict | None]:
    """Query the CEP API; return (continue?, location). On failure ask what to do."""
    if cep is None:
        return True, None
    cli.print_message("Consultando CEP...")
    try:
        return True, await pickup_service.lookup_location(cep)
    except ApiError as error:
        cli.print_message(str(error))
        return cli.confirm("Cadastrar a coleta sem os dados do CEP?"), None


async def create_pickup(state: AppState) -> AppState:
    """Read the data, enrich it with the CEP API and register the pickup."""
    customer_name = cli.read_text("Nome do cliente")
    address = cli.read_text("Endereço")
    cep = cli.read_cep()
    package_count = cli.read_int("Quantidade de pacotes")
    priority = cli.read_option("Prioridade:", PRIORITY_LABELS)
    proceed, location = await ask_location(cep)
    if not proceed:
        cli.print_message("Cadastro cancelado")
        return state
    updated = await pickup_service.create_pickup(
        state.pickups, customer_name, address, package_count, priority, location
    )
    cli.print_message(f"Coleta #{updated[-1]['id']} cadastrada")
    return app.set_pickups(state, updated)


async def show_all(state: AppState) -> AppState:
    """Show the pickups that match the active filters, sorted by id."""
    if state.filters:
        cli.print_message(f"Filtros ativos: {describe_filters(state.filters)}")
    cli.print_table(rules.list_pickups(app.visible_pickups(state)))
    return state


async def apply_filter(state: AppState, field_name: str) -> AppState:
    """Ask for a value, activate the filter and show the result."""
    value = cli.read_option(f"{FILTER_TITLES[field_name]}:", FILTER_LABELS[field_name])
    return await show_all(app.set_filter(state, field_name, value))


async def clear_filters(state: AppState) -> AppState:
    """Remove every active filter."""
    cli.print_message("Filtros removidos")
    return app.clear_filters(state)


async def change_status(state: AppState) -> AppState:
    """Ask for the pickup and the new status, then update it."""
    pickup_id = cli.read_int("ID da coleta")
    pickup = rules.find_by_id(state.pickups, pickup_id)
    if pickup is None:
        raise NotFoundError(f"Coleta #{pickup_id} não encontrada")
    cli.print_table([pickup])
    new_status = cli.read_option("Novo status:", STATUS_LABELS)
    updated = await pickup_service.change_status(state.pickups, pickup_id, new_status)
    cli.print_message(
        f"Status da coleta #{pickup_id} atualizado para {STATUS_LABELS[new_status]}"
    )
    return app.set_pickups(state, updated)


async def show_summary(state: AppState) -> AppState:
    """Show the operational summary of all pickups."""
    cli.print_summary(rules.build_summary(state.pickups))
    return state


Action = Callable[[AppState], Awaitable[AppState]]

ACTIONS: dict[str, Action] = {
    "1": create_pickup,
    "2": show_all,
    "3": lambda s: apply_filter(s, "status"),
    "4": lambda s: apply_filter(s, "priority"),
    "5": change_status,
    "6": show_summary,
    "7": clear_filters,
}


async def run_action(action: Action, state: AppState) -> AppState:
    """Run an action tracking loading and errors; never let an expected error escape."""
    state = app.set_loading(app.clear_error(state), True)
    try:
        return app.set_loading(await action(state), False)
    except FilaFacilError as error:
        logging.warning("Erro (%s): %s", error.kind, error)
        cli.print_message(str(error))
        return app.set_loading(app.set_error(state, error), False)


def run() -> None:
    """Run the menu loop until the user quits."""
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logging.info("Sistema iniciado")
    state = app.initial_state(asyncio.run(json_storage.load_pickups()))
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
                state = asyncio.run(run_action(action, state))
    except (KeyboardInterrupt, EOFError):
        print()
        cli.print_message("Encerrado pelo usuário. Até logo!")
    finally:
        logging.info("Sistema encerrado")
