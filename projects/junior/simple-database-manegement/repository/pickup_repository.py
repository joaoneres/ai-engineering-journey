"""Repository de coletas: único ponto de acesso ao banco via SQLAlchemy."""

from sqlalchemy import select

from database import SessionLocal
from models.pickup import Pickup


class PickupRepository:
    """Operações de persistência da tabela pickups."""

    def create(
        self,
        customer_name: str,
        address: str,
        package_count: int,
        priority: str,
        status: str,
    ) -> Pickup:
        """Insere uma nova coleta e a retorna com o id preenchido."""
        pickup = Pickup(
            customer_name=customer_name,
            address=address,
            package_count=package_count,
            priority=priority,
            status=status,
        )
        with SessionLocal() as session:
            session.add(pickup)
            session.commit()
            session.refresh(pickup)
        return pickup

    def list_all(self, order_by: str = "id") -> list[Pickup]:
        """Lista todas as coletas, por id (crescente) ou por data (mais recente primeiro)."""
        if order_by == "date":
            statement = select(Pickup).order_by(Pickup.created_at.desc())
        else:
            statement = select(Pickup).order_by(Pickup.id)
        with SessionLocal() as session:
            return list(session.scalars(statement).all())

    def get_by_id(self, pickup_id: int) -> Pickup | None:
        """Busca uma coleta pelo id; retorna None se não existir."""
        # SQL equivalente: SELECT * FROM pickups WHERE id = ?
        with SessionLocal() as session:
            return session.get(Pickup, pickup_id)

    def filter_by_status(self, status: str) -> list[Pickup]:
        """Lista as coletas com o status informado."""
        # SQL equivalente: SELECT * FROM pickups WHERE status = ? ORDER BY id
        statement = select(Pickup).where(Pickup.status == status).order_by(Pickup.id)
        with SessionLocal() as session:
            return list(session.scalars(statement).all())

    def filter_by_priority(self, priority: str) -> list[Pickup]:
        """Lista as coletas com a prioridade informada."""
        # SQL equivalente: SELECT * FROM pickups WHERE priority = ? ORDER BY id
        statement = select(Pickup).where(Pickup.priority == priority).order_by(Pickup.id)
        with SessionLocal() as session:
            return list(session.scalars(statement).all())

    def filter_by_name(self, term: str) -> list[Pickup]:
        """Lista as coletas cujo cliente contém o termo (sem diferenciar maiúsculas)."""
        # SQL equivalente:
        # SELECT * FROM pickups WHERE customer_name LIKE '%' || ? || '%' ORDER BY id
        # (no SQLite, LIKE já ignora maiúsculas/minúsculas em texto ASCII)
        statement = (
            select(Pickup)
            .where(Pickup.customer_name.ilike(f"%{term}%"))
            .order_by(Pickup.id)
        )
        with SessionLocal() as session:
            return list(session.scalars(statement).all())

    def update_status(self, pickup_id: int, new_status: str) -> Pickup | None:
        """Altera o status da coleta; retorna None se ela não existir."""
        # SQL equivalente: UPDATE pickups SET status = ? WHERE id = ?
        with SessionLocal() as session:
            pickup = session.get(Pickup, pickup_id)
            if pickup is None:
                return None
            pickup.status = new_status
            session.commit()
            session.refresh(pickup)
            return pickup

    def delete(self, pickup_id: int) -> bool:
        """Remove a coleta; retorna False se ela não existir."""
        # SQL equivalente: DELETE FROM pickups WHERE id = ?
        with SessionLocal() as session:
            pickup = session.get(Pickup, pickup_id)
            if pickup is None:
                return False
            session.delete(pickup)
            session.commit()
            return True
