"""Controller de coletas: menu e interação com o usuário no terminal."""

from models.pickup import PRIORITIES, PRIORITY_LABELS, STATUS_LABELS, Pickup
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
            print("3. Filtrar coletas (Em breve)")
            print("4. Atualizar status (Em breve)")
            print("5. Deletar coleta (Em breve)")
            print("0. Sair")
            option = input("Escolha uma opção: ").strip()

            if option == "1":
                self.register()
            elif option == "2":
                self.list_pickups()
            elif option in ("3", "4", "5"):
                print("Em breve.")
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

        print("Prioridade:")
        for number, value in enumerate(PRIORITIES, start=1):
            print(f"  {number}. {PRIORITY_LABELS[value]}")
        choice = input("Escolha a prioridade: ").strip()
        if not choice.isdigit() or not 1 <= int(choice) <= len(PRIORITIES):
            print("Prioridade inválida: escolha um dos números listados.")
            return
        priority = PRIORITIES[int(choice) - 1]

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
