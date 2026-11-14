"""Logistics label formatting, reusable by other teams."""

PRIORITY_LABELS = {"low": "Baixa", "medium": "Média", "high": "Alta"}
STATUS_LABELS = {"pending": "Pendente", "in_transit": "Em rota", "completed": "Concluída"}
PRIORITY_ORDER = ("high", "medium", "low")


def format_status(status: str) -> str:
    """Return the Portuguese label of a status; raise ValueError if unknown."""
    if status not in STATUS_LABELS:
        raise ValueError(f"Status inválido: {status!r}")
    return STATUS_LABELS[status]


def format_priority(priority: str) -> str:
    """Return the Portuguese label of a priority; raise ValueError if unknown."""
    if priority not in PRIORITY_LABELS:
        raise ValueError(f"Prioridade inválida: {priority!r}")
    return PRIORITY_LABELS[priority]


def format_counts(counts: dict, labels: dict[str, str], order: tuple[str, ...]) -> str:
    """Format counts as 'Label N | Label N'."""
    return " | ".join(f"{labels[key]} {counts[key]}" for key in order)


def format_summary(summary: dict) -> str:
    """Render the operational summary as text."""
    return "\n".join(
        [
            "===== Resumo operacional =====",
            f"Total de coletas: {summary['total_pickups']} | "
            f"Total de pacotes: {summary['total_packages']}",
            "Por prioridade: "
            + format_counts(summary["by_priority"], PRIORITY_LABELS, PRIORITY_ORDER),
            "Por status: "
            + format_counts(summary["by_status"], STATUS_LABELS, tuple(STATUS_LABELS)),
        ]
    )
