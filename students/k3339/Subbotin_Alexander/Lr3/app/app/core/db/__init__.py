from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

metadata = MetaData()


class Base(DeclarativeBase):
    metadata = metadata


# Импортируем все модели для их регистрации в metadata
# Это необходимо для корректной работы Alembic миграций
# Экспорт CRUD операций
from app.core.db import crud
from app.core.db.models.finance import (  # noqa: F401
    Budget,
    Category,
    FinancialAnalysis,
    FinancialGoal,
    Transaction,
)
from app.core.db.models.user import User  # noqa: F401

__all__ = ["Base", "metadata", "crud"]
