"""Controller de coletas: menu e interação com o usuário no terminal."""

from models.pickup import (
    PRIORITIES,
    PRIORITY_LABELS,
    STATUS_LABELS,
    STATUSES,
    Pickup,
)
from service.pickup_service import PickupService

HEADERS = ("ID", "Cliente", "Endereço", "Pacotes", "Prioridade", "Status", "Criado em")


class PickupController:
    """Exibe o menu e encaminha as ações ao service."""

    def __init__(self, service: PickupService) -> None:
        """Recebe o service usado para executar as operações."""
        self.service = service

    def run(self) -> None:
        """Executa o menu principal em loop até o usuário sair."""
        while True:
            print("\n===== FilaFácil Logística =====")
            print("1. Cadastrar coleta")
            print("2. Listar coletas")
            print("3. Filtrar coletas")
            print("4. Atualizar status")
            print("5. Deletar coleta")
            print("0. Sair")
            option = input("Escolha uma opção: ").strip()

            if option == "1":
                self.register()
            elif option == "2":
                self.list_pickups()
            elif option == "3":
                self.filter_pickups()
            elif option == "4":
                self.update_status()
            elif option == "5":
                self.delete_pickup()
            elif option == "0":
                print("Até logo!")
                break
            else:
                print("Opção inválida. Tente novamente.")

    def register(self) -> None:
        """Pede os dados, cadastra a coleta e mostra o resultado."""
        customer_name = input("Nome do cliente: ")
        address = input("Endereço: ")

        try:
            package_count = int(input("Quantidade de pacotes: ").strip())
        except ValueError:
            print("Quantidade inválida: digite um número inteiro.")
            return

        priority = self.choose_option("Prioridade", PRIORITIES, PRIORITY_LABELS)
        if priority is None:
            return

        try:
            pickup = self.service.register(customer_name, address, package_count, priority)
        except ValueError as error:
            print(f"Erro: {error}")
            return
        print(f"Coleta #{pickup.id} cadastrada.")

    def list_pickups(self) -> None:
        """Lista as coletas ordenadas por ID ou por data."""
        choice = input("Ordenar por (1) ID ou (2) Data? ").strip()
        if choice not in ("1", "2"):
            print("Opção inválida.")
            return
        order_by = "id" if choice == "1" else "date"

        try:
            pickups = self.service.list_all(order_by)
        except ValueError as error:
            print(f"Erro: {error}")
            return

        if not pickups:
            print("Nenhuma coleta cadastrada.")
            return
        self.print_table(pickups)

    def filter_pickups(self) -> None:
        """Filtra as coletas por status, prioridade ou nome do cliente."""
        print("Filtrar por:")
        print("  1. Status")
        print("  2. Prioridade")
        print("  3. Nome do cliente")
        print("  0. Voltar")
        choice = input("Escolha uma opção: ").strip()

        if choice == "0":
            return
        if choice == "1":
            field = "status"
            value = self.choose_option("Status", STATUSES, STATUS_LABELS)
        elif choice == "2":
            field = "priority"
            value = self.choose_option("Prioridade", PRIORITIES, PRIORITY_LABELS)
        elif choice == "3":
            field = "name"
            value = input("Nome (ou parte do nome) do cliente: ")
        else:
            print("Opção inválida.")
            return
        if value is None:
            return

        try:
            pickups = self.service.filter(field, value)
        except (ValueError, LookupError) as error:
            print(f"Erro: {error}")
            return

        if not pickups:
            print("Nenhuma coleta encontrada para esse filtro.")
            return
        self.print_table(pickups)

    def update_status(self) -> None:
        """Atualiza o status de uma coleta existente."""
        pickup_id = self.read_id()
        if pickup_id is None:
            return

        try:
            pickup = self.service.get_by_id(pickup_id)
            print("Coleta atual:")
            self.print_table([pickup])
            new_status = self.choose_option("Novo status", STATUSES, STATUS_LABELS)
            if new_status is None:
                return
            updated = self.service.update_status(pickup_id, new_status)
        except (ValueError, LookupError) as error:
            print(f"Erro: {error}")
            return
        print(
            f"Status da coleta #{updated.id} alterado para "
            f"{STATUS_LABELS.get(updated.status, updated.status)}."
        )

    def delete_pickup(self) -> None:
        """Deleta uma coleta existente, após confirmação."""
        pickup_id = self.read_id()
        if pickup_id is None:
            return

        try:
            pickup = self.service.get_by_id(pickup_id)
            print("Coleta encontrada:")
            self.print_table([pickup])
            answer = input("Deseja realmente deletar? (s/n): ").strip().lower()
            if answer != "s":
                print("Operação cancelada.")
                return
            self.service.delete(pickup_id)
        except (ValueError, LookupError) as error:
            print(f"Erro: {error}")
            return
        print(f"Coleta #{pickup_id} deletada.")

    def read_id(self) -> int | None:
        """Pede um ID ao usuário; retorna None (com aviso) se não for número."""
        try:
            return int(input("ID da coleta: ").strip())
        except ValueError:
            print("ID inválido: digite um número inteiro.")
            return None

    def choose_option(
        self, title: str, values: tuple[str, ...], labels: dict[str, str]
    ) -> str | None:
        """Mostra opções numeradas em português e retorna o valor em inglês escolhido."""
        print(f"{title}:")
        for number, value in enumerate(values, start=1):
            print(f"  {number}. {labels[value]}")
        choice = input("Escolha uma opção: ").strip()
        if not choice.isdigit() or not 1 <= int(choice) <= len(values):
            print("Opção inválida: escolha um dos números listados.")
            return None
        return values[int(choice) - 1]

    def print_table(self, pickups: list[Pickup]) -> None:
        """Imprime as coletas em uma tabela alinhada."""
        rows = [
            (
                str(pickup.id),
                pickup.customer_name,
                pickup.address,
                str(pickup.package_count),
                PRIORITY_LABELS.get(pickup.priority, pickup.priority),
                STATUS_LABELS.get(pickup.status, pickup.status),
                pickup.created_at.strftime("%d/%m/%Y %H:%M"),
            )
            for pickup in pickups
        ]
        widths = [max(len(cell) for cell in column) for column in zip(HEADERS, *rows)]

        def format_row(row: tuple[str, ...]) -> str:
            return " | ".join(cell.ljust(width) for cell, width in zip(row, widths))

        print()
        print(format_row(HEADERS))
        print("-+-".join("-" * width for width in widths))
        for row in rows:
            print(format_row(row))
