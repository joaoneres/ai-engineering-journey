"""Model Pickup: solicitação de coleta."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base

PRIORITIES = ("low", "medium", "high")
STATUSES = ("pending", "in_transit", "collected", "canceled")

PRIORITY_LABELS = {"low": "Baixa", "medium": "Média", "high": "Alta"}
STATUS_LABELS = {
    "pending": "Pendente",
    "in_transit": "Em rota",
    "collected": "Coletada",
    "canceled": "Cancelada",
}


class Pickup(Base):
    """Solicitação de coleta de pacotes de um cliente."""

    __tablename__ = "pickups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_name: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str] = mapped_column(String(200), nullable=False)
    package_count: Mapped[int] = mapped_column(Integer, nullable=False)
    priority: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )

    def __repr__(self) -> str:
        """Representação legível da coleta."""
        return (
            f"Pickup(id={self.id}, customer_name={self.customer_name!r}, "
            f"package_count={self.package_count}, priority={self.priority!r}, "
            f"status={self.status!r})"
        )
