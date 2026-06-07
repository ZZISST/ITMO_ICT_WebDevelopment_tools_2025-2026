from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.core.db.models.user import User


class CategoryType(str, Enum):
    """типы категорий"""

    NEEDS = "needs"
    WANTS = "wants"
    CULTURE = "culture"
    UNEXPECTED = "unexpected"
    INCOME = "income"


class TransactionType(str, Enum):
    """Типы транзакций"""

    EXPENSE = "expense"  # Расход
    INCOME = "income"  # Доход


class AnalysisStatus(str, Enum):
    """Статус финансового анализа"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Category(Base):
    """Категории расходов и доходов"""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category_type: Mapped[CategoryType] = mapped_column(
        SAEnum(CategoryType), nullable=False
    )
    color: Mapped[Optional[str]] = mapped_column(
        String(7), nullable=True
    )  # Hex color code
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    budgets: Mapped[list["Budget"]] = relationship("Budget", back_populates="category")
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="category"
    )

    def __repr__(self) -> str:
        return f"Category(id={self.id}, name={self.name}, type={self.category_type})"


class Budget(Base):
    """Бюджет пользователя по категориям"""

    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE")
    )
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="CASCADE")
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="budgets")
    category: Mapped["Category"] = relationship("Category", back_populates="budgets")

    def __repr__(self) -> str:
        return f"Budget(id={self.id}, user_id={self.user_id}, amount={self.amount})"


class Transaction(Base):
    """Транзакции (доходы и расходы)"""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE")
    )
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="CASCADE")
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    transaction_type: Mapped[TransactionType] = mapped_column(
        SAEnum(TransactionType), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    transaction_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_planned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="transactions")
    category: Mapped["Category"] = relationship(
        "Category", back_populates="transactions"
    )

    def __repr__(self) -> str:
        return f"Transaction(id={self.id}, amount={self.amount}, type={self.transaction_type})"


class FinancialGoal(Base):
    """Финансовые цели пользователя"""

    __tablename__ = "financial_goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE")
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    target_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    current_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    target_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_achieved: Mapped[bool] = mapped_column(Boolean, default=False)
    priority: Mapped[int] = mapped_column(
        Integer, default=1
    )  # 1-5, где 1 - низкий приоритет
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="financial_goals")

    def __repr__(self) -> str:
        return f"FinancialGoal(id={self.id}, title={self.title}, target={self.target_amount})"


class FinancialAnalysis(Base):
    """Результаты финансового анализа пользователя"""

    __tablename__ = "financial_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE")
    )
    analysis_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    period_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    status: Mapped[AnalysisStatus] = mapped_column(
        SAEnum(AnalysisStatus), default=AnalysisStatus.PENDING, nullable=False
    )

    # Показатели анализа
    total_income: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    total_expenses: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    savings_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=0
    )  # Процент сбережений

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="financial_analyses")

    def __repr__(self) -> str:
        return f"FinancialAnalysis(id={self.id}, user_id={self.user_id}, status={self.status})"
