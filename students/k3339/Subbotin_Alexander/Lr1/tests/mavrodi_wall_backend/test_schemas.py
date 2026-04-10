import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.api.schemas.finance import (
    BudgetCreate,
    CategoryBase,
    CategoryCreate,
    CategoryType,
    FinancialGoalCreate,
    FinancialGoalResponse,
    NotebookType,
    TransactionCreate,
    TransactionType,
)

FUTURE = datetime.now() + timedelta(days=30)
NOW = datetime.utcnow()


def valid_transaction_payload(**overrides) -> dict:
    base = dict(
        category_id=1,
        amount=Decimal("1500.00"),
        transaction_type=TransactionType.EXPENSE,
        notebook_type=NotebookType.SMALL,
        description="Кофе и булочка",
        transaction_date=NOW,
    )
    base.update(overrides)
    return base


def valid_budget_payload(**overrides) -> dict:
    base = dict(
        category_id=1,
        amount=Decimal("20000.00"),
        period_start=datetime(2026, 3, 1),
        period_end=datetime(2026, 3, 31),
    )
    base.update(overrides)
    return base


def valid_goal_payload(**overrides) -> dict:
    base = dict(
        title="Отпуск в Испании",
        target_amount=Decimal("300000.00"),
        target_date=FUTURE.strftime("%Y-%m-%dT%H:%M:%S"),
    )
    base.update(overrides)
    return base

class TestTransactionCreate:
    def test_valid_expense_passes(self):
        tx = TransactionCreate(**valid_transaction_payload())
        assert tx.amount == Decimal("1500.00")
        assert tx.transaction_type == TransactionType.EXPENSE

    def test_valid_income_passes(self):
        tx = TransactionCreate(
            **valid_transaction_payload(
                transaction_type=TransactionType.INCOME,
                notebook_type=NotebookType.BIG,
                amount=Decimal("80000.00"),
                description="Зарплата",
            )
        )
        assert tx.transaction_type == TransactionType.INCOME

    def test_zero_amount_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            TransactionCreate(**valid_transaction_payload(amount=Decimal("0")))
        errors = exc_info.value.errors()
        assert any("amount" in str(e["loc"]) for e in errors)

    def test_negative_amount_rejected(self):
        with pytest.raises(ValidationError):
            TransactionCreate(**valid_transaction_payload(amount=Decimal("-500.00")))

    def test_empty_description_rejected(self):
        with pytest.raises(ValidationError):
            TransactionCreate(**valid_transaction_payload(description=""))

    def test_description_too_long_rejected(self):
        with pytest.raises(ValidationError):
            TransactionCreate(**valid_transaction_payload(description="x" * 501))

    def test_description_exactly_at_max_passes(self):
        tx = TransactionCreate(**valid_transaction_payload(description="a" * 500))
        assert len(tx.description) == 500

    def test_notes_optional_defaults_to_none(self):
        tx = TransactionCreate(**valid_transaction_payload())
        assert tx.notes is None

    def test_notes_accepted_when_provided(self):
        tx = TransactionCreate(**valid_transaction_payload(notes="Детали покупки"))
        assert tx.notes == "Детали покупки"

    def test_notes_too_long_rejected(self):
        with pytest.raises(ValidationError):
            TransactionCreate(**valid_transaction_payload(notes="n" * 1001))

    def test_category_id_must_be_positive(self):
        with pytest.raises(ValidationError):
            TransactionCreate(**valid_transaction_payload(category_id=0))

    def test_category_id_negative_rejected(self):
        with pytest.raises(ValidationError):
            TransactionCreate(**valid_transaction_payload(category_id=-1))

    def test_is_planned_defaults_to_false(self):
        tx = TransactionCreate(**valid_transaction_payload())
        assert tx.is_planned is False

    def test_is_recurring_defaults_to_false(self):
        tx = TransactionCreate(**valid_transaction_payload())
        assert tx.is_recurring is False

    def test_planned_flag_can_be_set(self):
        tx = TransactionCreate(**valid_transaction_payload(is_planned=True))
        assert tx.is_planned is True

    def test_invalid_transaction_type_rejected(self):
        with pytest.raises(ValidationError):
            TransactionCreate(**valid_transaction_payload(transaction_type="transfer"))

    def test_invalid_notebook_type_rejected(self):
        with pytest.raises(ValidationError):
            TransactionCreate(**valid_transaction_payload(notebook_type="medium"))

    def test_big_notebook_accepted(self):
        tx = TransactionCreate(
            **valid_transaction_payload(notebook_type=NotebookType.BIG)
        )
        assert tx.notebook_type == NotebookType.BIG

    def test_large_valid_amount_passes(self):
        tx = TransactionCreate(
            **valid_transaction_payload(amount=Decimal("9999999.99"))
        )
        assert tx.amount == Decimal("9999999.99")


class TestBudgetCreate:
    def test_valid_budget_passes(self):
        budget = BudgetCreate(**valid_budget_payload())
        assert budget.amount == Decimal("20000.00")
        assert budget.category_id == 1

    def test_period_end_before_period_start_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            BudgetCreate(
                **valid_budget_payload(
                    period_start=datetime(2026, 3, 31),
                    period_end=datetime(2026, 3, 1),
                )
            )
        errors = exc_info.value.errors()
        assert any("period_end" in str(e["loc"]) for e in errors)

    def test_period_end_equal_to_period_start_rejected(self):
        same_date = datetime(2026, 3, 15)
        with pytest.raises(ValidationError):
            BudgetCreate(
                **valid_budget_payload(period_start=same_date, period_end=same_date)
            )

    def test_zero_amount_allowed(self):
        """Zero budget amount is allowed (budget not yet assigned)."""
        budget = BudgetCreate(**valid_budget_payload(amount=Decimal("0.00")))
        assert budget.amount == Decimal("0.00")

    def test_negative_amount_rejected(self):
        with pytest.raises(ValidationError):
            BudgetCreate(**valid_budget_payload(amount=Decimal("-100.00")))

    def test_category_id_zero_rejected(self):
        with pytest.raises(ValidationError):
            BudgetCreate(**valid_budget_payload(category_id=0))

    def test_one_day_period_passes(self):
        budget = BudgetCreate(
            **valid_budget_payload(
                period_start=datetime(2026, 4, 1, 0, 0, 0),
                period_end=datetime(2026, 4, 1, 23, 59, 59),
            )
        )
        assert budget.period_start < budget.period_end


class TestFinancialGoalCreate:
    def test_valid_goal_passes(self):
        goal = FinancialGoalCreate(**valid_goal_payload())
        assert goal.title == "Отпуск в Испании"
        assert goal.target_amount == Decimal("300000.00")

    def test_past_target_date_rejected(self):
        past = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
        with pytest.raises(ValidationError) as exc_info:
            FinancialGoalCreate(**valid_goal_payload(target_date=past))
        errors = exc_info.value.errors()
        assert any("target_date" in str(e["loc"]) for e in errors)

    def test_zero_target_amount_rejected(self):
        with pytest.raises(ValidationError):
            FinancialGoalCreate(**valid_goal_payload(target_amount=Decimal("0")))

    def test_negative_target_amount_rejected(self):
        with pytest.raises(ValidationError):
            FinancialGoalCreate(**valid_goal_payload(target_amount=Decimal("-1000")))

    def test_empty_title_rejected(self):
        with pytest.raises(ValidationError):
            FinancialGoalCreate(**valid_goal_payload(title=""))

    def test_title_too_long_rejected(self):
        with pytest.raises(ValidationError):
            FinancialGoalCreate(**valid_goal_payload(title="t" * 201))

    def test_title_exactly_at_max_passes(self):
        goal = FinancialGoalCreate(**valid_goal_payload(title="x" * 200))
        assert len(goal.title) == 200

    def test_description_optional(self):
        goal = FinancialGoalCreate(**valid_goal_payload())
        assert goal.description is None

    def test_description_too_long_rejected(self):
        with pytest.raises(ValidationError):
            FinancialGoalCreate(**valid_goal_payload(description="d" * 1001))

    def test_priority_defaults_to_one(self):
        goal = FinancialGoalCreate(**valid_goal_payload())
        assert goal.priority == 1

    def test_priority_min_boundary(self):
        goal = FinancialGoalCreate(**valid_goal_payload(priority=1))
        assert goal.priority == 1

    def test_priority_max_boundary(self):
        goal = FinancialGoalCreate(**valid_goal_payload(priority=5))
        assert goal.priority == 5

    def test_priority_above_max_rejected(self):
        with pytest.raises(ValidationError):
            FinancialGoalCreate(**valid_goal_payload(priority=6))

    def test_priority_below_min_rejected(self):
        with pytest.raises(ValidationError):
            FinancialGoalCreate(**valid_goal_payload(priority=0))

    def test_date_only_string_accepted(self):
        """'YYYY-MM-DD' format should be coerced to a datetime by the validator."""
        future_date = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
        goal = FinancialGoalCreate(**valid_goal_payload(target_date=future_date))
        assert isinstance(goal.target_date, datetime)

class TestCategoryBase:
    def test_valid_category_passes(self):
        cat = CategoryCreate(
            name="Развлечения",
            category_type=CategoryType.WANTS,
            color="#9C27B0",
            icon="🎉",
        )
        assert cat.name == "Развлечения"

    def test_invalid_hex_color_rejected(self):
        with pytest.raises(ValidationError):
            CategoryCreate(
                name="Test",
                category_type=CategoryType.NEEDS,
                color="red",  # not a hex color
            )

    def test_hex_color_without_hash_rejected(self):
        with pytest.raises(ValidationError):
            CategoryCreate(
                name="Test",
                category_type=CategoryType.NEEDS,
                color="4CAF50",
            )

    def test_valid_hex_color_accepted(self):
        cat = CategoryCreate(
            name="Test",
            category_type=CategoryType.NEEDS,
            color="#4CAF50",
        )
        assert cat.color == "#4CAF50"

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            CategoryCreate(name="", category_type=CategoryType.NEEDS)

    def test_name_too_long_rejected(self):
        with pytest.raises(ValidationError):
            CategoryCreate(name="x" * 101, category_type=CategoryType.NEEDS)

    def test_color_and_icon_optional(self):
        cat = CategoryCreate(name="Прочее", category_type=CategoryType.UNEXPECTED)
        assert cat.color is None
        assert cat.icon is None

    def test_all_category_types_accepted(self):
        for ct in CategoryType:
            cat = CategoryCreate(name="Тест", category_type=ct)
            assert cat.category_type == ct

class TestFinancialGoalResponse:
    def _make_response(self, current: str, target: str) -> FinancialGoalResponse:
        return FinancialGoalResponse(
            id=1,
            user_id=1,
            title="Цель",
            target_amount=Decimal(target),
            current_amount=Decimal(current),
            target_date=FUTURE,
            is_achieved=False,
            priority=1,
            created_at=NOW,
            updated_at=NOW,
        )

    def test_zero_progress(self):
        resp = self._make_response("0", "100000")
        assert resp.progress_percentage == 0.0

    def test_half_progress(self):
        resp = self._make_response("50000", "100000")
        assert abs(resp.progress_percentage - 50.0) < 0.01

    def test_full_progress_capped_at_100(self):
        resp = self._make_response("100000", "100000")
        assert resp.progress_percentage == 100.0

    def test_over_target_capped_at_100(self):
        """Even if current > target, percentage must not exceed 100."""
        resp = self._make_response("150000", "100000")
        assert resp.progress_percentage == 100.0

    def test_small_contribution_precision(self):
        resp = self._make_response("14000", "520000")
        expected = round(14000 / 520000 * 100, 2)
        assert abs(resp.progress_percentage - expected) < 0.01
