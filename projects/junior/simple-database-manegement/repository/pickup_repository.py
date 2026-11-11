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
