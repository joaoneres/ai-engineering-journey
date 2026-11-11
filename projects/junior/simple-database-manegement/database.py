"""Configuração do banco: engine, fábrica de sessões e criação da tabela."""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = "sqlite:///filafacil.db"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Classe base de todos os models do ORM."""


def create_tables() -> None:
    """Cria as tabelas no banco, caso ainda não existam."""
    import models.pickup  # noqa: F401  (registra o model na Base)

    Base.metadata.create_all(engine)
