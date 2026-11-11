"""Service de coletas: regras de negócio e validações."""

from models.pickup import PRIORITIES, STATUSES, Pickup
from repository.pickup_repository import PickupRepository

ORDER_OPTIONS = ("id", "date")
FILTER_FIELDS = ("status", "priority", "name")
MAX_NAME_LENGTH = 100
MAX_ADDRESS_LENGTH = 200
MAX_PACKAGE_COUNT = 1_000_000
MAX_ID = 2**63 - 1  # maior inteiro aceito pelo SQLite


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
        if len(customer_name) > MAX_NAME_LENGTH:
            raise ValueError(f"O nome do cliente deve ter no máximo {MAX_NAME_LENGTH} caracteres.")
        if not address:
            raise ValueError("O endereço é obrigatório.")
        if len(address) > MAX_ADDRESS_LENGTH:
            raise ValueError(f"O endereço deve ter no máximo {MAX_ADDRESS_LENGTH} caracteres.")
        if (
            isinstance(package_count, bool)
            or not isinstance(package_count, int)
            or package_count <= 0
        ):
            raise ValueError("A quantidade de pacotes deve ser um número inteiro maior que 0.")
        if package_count > MAX_PACKAGE_COUNT:
            raise ValueError(f"A quantidade de pacotes deve ser no máximo {MAX_PACKAGE_COUNT}.")

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

    def get_by_id(self, pickup_id: int) -> Pickup:
        """Retorna a coleta ou lança LookupError se ela não existir."""
        if not 0 < pickup_id <= MAX_ID:
            raise LookupError(f"Coleta #{pickup_id} não encontrada")
        pickup = self.repository.get_by_id(pickup_id)
        if pickup is None:
            raise LookupError(f"Coleta #{pickup_id} não encontrada")
        return pickup

    def filter(self, field: str, value: str) -> list[Pickup]:
        """Filtra as coletas por 'status', 'priority' ou 'name'."""
        field = field.strip().lower()
        value = value.strip()
        if field not in FILTER_FIELDS:
            raise ValueError("Filtro inválido. Use 'status', 'priority' ou 'name'.")
        if not value:
            raise ValueError("O valor do filtro é obrigatório.")

        if field == "status":
            value = value.lower()
            if value not in STATUSES:
                raise ValueError(f"Status inválido. Use: {', '.join(STATUSES)}.")
            return self.repository.filter_by_status(value)
        if field == "priority":
            value = value.lower()
            if value not in PRIORITIES:
                raise ValueError(f"Prioridade inválida. Use: {', '.join(PRIORITIES)}.")
            return self.repository.filter_by_priority(value)
        return self.repository.filter_by_name(value)

    def update_status(self, pickup_id: int, new_status: str) -> Pickup:
        """Valida o novo status e atualiza a coleta (que precisa existir)."""
        new_status = new_status.strip().lower()
        if new_status not in STATUSES:
            raise ValueError(f"Status inválido. Use: {', '.join(STATUSES)}.")
        self.get_by_id(pickup_id)
        updated = self.repository.update_status(pickup_id, new_status)
        if updated is None:
            raise LookupError(f"Coleta #{pickup_id} não encontrada")
        return updated

    def delete(self, pickup_id: int) -> None:
        """Remove a coleta (que precisa existir)."""
        self.get_by_id(pickup_id)
        if not self.repository.delete(pickup_id):
            raise LookupError(f"Coleta #{pickup_id} não encontrada")
