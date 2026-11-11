"""Service de coletas: regras de negócio e validações."""

from models.pickup import PRIORITIES, STATUSES, Pickup
from repository.pickup_repository import PickupRepository

ORDER_OPTIONS = ("id", "date")


class PickupService:
    """Valida os dados e delega a persistência ao repository."""

    def __init__(self, repository: PickupRepository) -> None:
        """Recebe o repository usado para acessar o banco."""
        self.repository = repository

    def register(
        self,
        customer_name: str,
        address: str,
        package_count: int,
        priority: str,
        status: str = "pending",
    ) -> Pickup:
        """Valida os dados e cadastra uma nova coleta."""
        customer_name = customer_name.strip()
        address = address.strip()
        if not customer_name:
            raise ValueError("O nome do cliente é obrigatório.")
        if not address:
            raise ValueError("O endereço é obrigatório.")
        if (
            isinstance(package_count, bool)
            or not isinstance(package_count, int)
            or package_count <= 0
        ):
            raise ValueError("A quantidade de pacotes deve ser um número inteiro maior que 0.")

        priority = priority.strip().lower()
        status = status.strip().lower()
        if priority not in PRIORITIES:
            raise ValueError(f"Prioridade inválida. Use: {', '.join(PRIORITIES)}.")
        if status not in STATUSES:
            raise ValueError(f"Status inválido. Use: {', '.join(STATUSES)}.")

        return self.repository.create(customer_name, address, package_count, priority, status)

    def list_all(self, order_by: str = "id") -> list[Pickup]:
        """Lista as coletas, ordenadas por 'id' ou 'date'."""
        if order_by not in ORDER_OPTIONS:
            raise ValueError("Ordenação inválida. Use 'id' ou 'date'.")
        return self.repository.list_all(order_by)
