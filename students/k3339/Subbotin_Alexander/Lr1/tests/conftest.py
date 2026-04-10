import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.core.db.models.finance import (
    Category,
    CategoryType,
    FinancialGoal,
    NotebookType,
    Transaction,
    TransactionType,
)
from app.core.db.models.user import User


@pytest.fixture
def mock_db():
    """
    A lightweight AsyncMock that mimics the subset of AsyncSession methods
    used by our CRUD helpers:  execute, add, commit, refresh, delete.
    """
    db = AsyncMock()
    db.add = MagicMock()  # synchronous in SQLAlchemy
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = MagicMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def fake_user() -> User:
    user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="$2b$12$hashed_password_placeholder",
        is_active=True,
        is_admin=False,
        created_at=datetime(2026, 1, 1, 12, 0, 0),
    )
    return user


@pytest.fixture
def fake_admin_user() -> User:
    user = User(
        id=99,
        username="admin",
        email="admin@example.com",
        hashed_password="$2b$12$hashed_admin_password",
        is_active=True,
        is_admin=True,
        created_at=datetime(2026, 1, 1, 10, 0, 0),
    )
    return user


@pytest.fixture
def fake_category() -> Category:
    cat = Category(
        id=1,
        name="Продукты",
        description="Еда и напитки",
        category_type=CategoryType.NEEDS,
        color="#4CAF50",
        icon="🍎",
        is_default=True,
        created_at=datetime(2026, 1, 1),
    )
    return cat


@pytest.fixture
def fake_savings_category() -> Category:
    cat = Category(
        id=10,
        name="Сбережения / Цели",
        description="Взносы на финансовые цели",
        category_type=CategoryType.NEEDS,
        color="#00897B",
        icon="🎯",
        is_default=True,
        created_at=datetime(2026, 1, 1),
    )
    return cat


@pytest.fixture
def fake_income_category() -> Category:
    cat = Category(
        id=2,
        name="Зарплата",
        description="Основной доход от работы",
        category_type=CategoryType.INCOME,
        color="#4CAF50",
        icon="💰",
        is_default=True,
        created_at=datetime(2026, 1, 1),
    )
    return cat


@pytest.fixture
def fake_expense_transaction(fake_category) -> Transaction:
    tx = Transaction(
        id=1,
        user_id=1,
        category_id=fake_category.id,
        amount=Decimal("3000.00"),
        transaction_type=TransactionType.EXPENSE,
        notebook_type=NotebookType.SMALL,
        description="Продукты на неделю",
        notes=None,
        transaction_date=datetime(2026, 3, 11, 10, 0, 0),
        is_planned=False,
        is_recurring=False,
        created_at=datetime(2026, 3, 11, 10, 0, 0),
        updated_at=datetime(2026, 3, 11, 10, 0, 0),
    )
    tx.category = fake_category
    return tx


@pytest.fixture
def fake_income_transaction(fake_income_category) -> Transaction:
    tx = Transaction(
        id=2,
        user_id=1,
        category_id=fake_income_category.id,
        amount=Decimal("140000.00"),
        transaction_type=TransactionType.INCOME,
        notebook_type=NotebookType.BIG,
        description="Зарплата за март",
        notes=None,
        transaction_date=datetime(2026, 3, 11, 9, 0, 0),
        is_planned=False,
        is_recurring=True,
        created_at=datetime(2026, 3, 11, 9, 0, 0),
        updated_at=datetime(2026, 3, 11, 9, 0, 0),
    )
    tx.category = fake_income_category
    return tx


@pytest.fixture
def fake_goal_transaction(fake_savings_category) -> Transaction:
    """Transaction auto-created when goal progress is added."""
    tx = Transaction(
        id=3,
        user_id=1,
        category_id=fake_savings_category.id,
        amount=Decimal("14000.00"),
        transaction_type=TransactionType.EXPENSE,
        notebook_type=NotebookType.BIG,
        description="Взнос на цель: отпуск в израиле",
        notes="Автоматически создано при пополнении цели #1",
        transaction_date=datetime(2026, 3, 12, 15, 0, 0),
        is_planned=True,
        is_recurring=False,
        created_at=datetime(2026, 3, 12, 15, 0, 0),
        updated_at=datetime(2026, 3, 12, 15, 0, 0),
    )
    tx.category = fake_savings_category
    return tx


@pytest.fixture
def fake_goal() -> FinancialGoal:
    goal = FinancialGoal(
        id=1,
        user_id=1,
        title="отпуск в израиле",
        description="Накопить на отпуск",
        target_amount=Decimal("520000.00"),
        current_amount=Decimal("14000.00"),
        target_date=datetime(2026, 10, 1),
        is_achieved=False,
        priority=3,
        created_at=datetime(2026, 3, 1),
        updated_at=datetime(2026, 3, 12),
    )
    return goal


@pytest.fixture
def fake_stats():
    return {
        "total_income": Decimal("140000.00"),
        "total_expenses": Decimal("84000.00"),
        "savings": Decimal("56000.00"),
        "savings_rate": 40.0,
        "total_transactions": 3,
        "avg_expense": Decimal("28000.00"),
        "max_expense": Decimal("67000.00"),
        "planned_expenses": Decimal("14000.00"),
        "actual_expenses": Decimal("70000.00"),
        "category_breakdown": [
            {
                "category_id": 3,
                "total": Decimal("67000.00"),
                "count": 1,
                "category_name": "Электроника",
            },
            {
                "category_id": 10,
                "total": Decimal("14000.00"),
                "count": 1,
                "category_name": "Сбережения / Цели",
            },
            {
                "category_id": 1,
                "total": Decimal("3000.00"),
                "count": 1,
                "category_name": "Продукты",
            },
        ],
        "notebook_breakdown": [
            {"type": NotebookType.BIG, "total": Decimal("81000.00"), "count": 2},
            {"type": NotebookType.SMALL, "total": Decimal("3000.00"), "count": 1},
        ],
    }
