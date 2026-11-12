"""Terminal input and output."""

from constants import PRIORITY_LABELS, STATUS_LABELS
from domain.pickups import normalize_cep
from errors import InputError

MAX_DIGITS = 9
ROW_FORMAT = "{:<4} | {:<20} | {:<30} | {:<16} | {:>7} | {:<10} | {:<10}"
HEADERS = ("ID", "Cliente", "Endereço", "Cidade/UF", "Pacotes", "Prioridade", "Status")


def print_message(text: str) -> None:
    """Print a formatted message."""
    print(f">> {text}")


def read_text(prompt: str) -> str:
    """Ask again until a non-empty text is received."""
    while True:
        value = input(f"{prompt}: ").strip()
        if value:
            return value
        print_message("O campo não pode ficar vazio.")


def read_int(prompt: str, min_value: int = 1) -> int:
    """Ask again until an integer >= min_value is received."""
    while True:
        raw = input(f"{prompt}: ").strip()
        if not raw.removeprefix("-").isdecimal():
            print_message("Digite apenas números inteiros.")
        elif len(raw) > MAX_DIGITS:
            print_message("Número muito grande.")
        elif int(raw) < min_value:
            print_message(f"O valor deve ser maior ou igual a {min_value}.")
        else:
            return int(raw)


def read_option(prompt: str, options: dict[str, str]) -> str:
    """Show the numbered options and return the chosen key."""
    keys = list(options)
    while True:
        print(prompt)
        for number, key in enumerate(keys, start=1):
            print(f"{number}. {options[key]}")
        raw = input("Escolha uma opção: ").strip()
        if not raw.isdecimal() or len(raw) > MAX_DIGITS:
            print_message("Digite o número de uma das opções.")
        elif not 1 <= int(raw) <= len(keys):
            print_message("Opção inexistente.")
        else:
            return keys[int(raw) - 1]


def fit(text: str, width: int) -> str:
    """Cut the text with an ellipsis if it exceeds the column width."""
    return text if len(text) <= width else text[: width - 1] + "…"


def format_city(pickup: dict) -> str:
    """Return 'City/UF' from the API data, or '-' when the pickup was not enriched."""
    city, state = pickup.get("city"), pickup.get("state")
    return f"{city}/{state}" if city and state else "-"


def read_cep() -> str | None:
    """Ask for an optional CEP; Enter skips it. Ask again while the format is wrong."""
    while True:
        raw = input("CEP (Enter para pular): ").strip()
        if not raw:
            return None
        try:
            return normalize_cep(raw)
        except InputError as error:
            print_message(str(error))


def confirm(prompt: str) -> bool:
    """Ask a yes/no question; anything other than s/sim means no."""
    return input(f"{prompt} (s/n): ").strip().lower() in ("s", "sim")


def to_display_row(pickup: dict) -> str:
    """Turn a pickup into an aligned table row."""
    return ROW_FORMAT.format(
        pickup["id"],
        fit(pickup["customer_name"], 20),
        fit(pickup["address"], 30),
        fit(format_city(pickup), 16),
        pickup["package_count"],
        PRIORITY_LABELS[pickup["priority"]],
        STATUS_LABELS[pickup["status"]],
    )


def print_table(pickups: list[dict]) -> None:
    """Print the pickup table, or a notice if the list is empty."""
    if not pickups:
        print_message("Nenhuma coleta encontrada")
        return
    header = ROW_FORMAT.format(*HEADERS)
    print(header)
    print("-" * len(header))
    print("\n".join(map(to_display_row, pickups)))


def format_counts(counts: dict, labels: dict[str, str], order: list[str]) -> str:
    """Format counts as 'Label N | Label N'."""
    return " | ".join(f"{labels[key]} {counts[key]}" for key in order)


def print_summary(summary: dict) -> None:
    """Print the operational summary."""
    print("===== Resumo operacional =====")
    print(
        f"Total de coletas: {summary['total_pickups']} | "
        f"Total de pacotes: {summary['total_packages']}"
    )
    priority_order = ["high", "medium", "low"]
    print("Por prioridade: " + format_counts(summary["by_priority"], PRIORITY_LABELS, priority_order))
    print("Por status: " + format_counts(summary["by_status"], STATUS_LABELS, list(STATUS_LABELS)))
