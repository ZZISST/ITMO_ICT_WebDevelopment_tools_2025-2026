import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.core.db.crud.finance.analysis import FinancialGoalCRUD
from app.core.db.models.finance import FinancialGoal

def make_goal(
    goal_id: int = 1,
    user_id: int = 1,
    target: str = "100000.00",
    current: str = "0.00",
    is_achieved: bool = False,
) -> FinancialGoal:
    goal = FinancialGoal(
        id=goal_id,
        user_id=user_id,
        title="Test Goal",
        description="Unit test goal",
        target_amount=Decimal(target),
        current_amount=Decimal(current),
        target_date=datetime.utcnow() + timedelta(days=180),
        is_achieved=is_achieved,
        priority=2,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    return goal

class TestUpdateProgress:
    @pytest.mark.asyncio
    async def test_partial_contribution_increases_current_amount(self, mock_db):
        goal = make_goal(current="10000.00", target="100000.00")

        with patch.object(FinancialGoalCRUD, "get", new=AsyncMock(return_value=goal)):
            result = await FinancialGoalCRUD.update_progress(
                mock_db, goal_id=1, user_id=1, amount_to_add=Decimal("5000.00")
            )

        assert result is not None
        assert result.current_amount == Decimal("15000.00")

    @pytest.mark.asyncio
    async def test_partial_contribution_does_not_mark_achieved(self, mock_db):
        goal = make_goal(current="50000.00", target="100000.00")

        with patch.object(FinancialGoalCRUD, "get", new=AsyncMock(return_value=goal)):
            result = await FinancialGoalCRUD.update_progress(
                mock_db, goal_id=1, user_id=1, amount_to_add=Decimal("10000.00")
            )

        assert result.is_achieved is False

    @pytest.mark.asyncio
    async def test_exact_full_contribution_marks_achieved(self, mock_db):
        goal = make_goal(current="90000.00", target="100000.00")

        with patch.object(FinancialGoalCRUD, "get", new=AsyncMock(return_value=goal)):
            result = await FinancialGoalCRUD.update_progress(
                mock_db, goal_id=1, user_id=1, amount_to_add=Decimal("10000.00")
            )

        assert result.current_amount == Decimal("100000.00")
        assert result.is_achieved is True

    @pytest.mark.asyncio
    async def test_overpayment_marks_achieved(self, mock_db):
        """Contributing more than remaining should still mark goal as achieved."""
        goal = make_goal(current="95000.00", target="100000.00")

        with patch.object(FinancialGoalCRUD, "get", new=AsyncMock(return_value=goal)):
            result = await FinancialGoalCRUD.update_progress(
                mock_db, goal_id=1, user_id=1, amount_to_add=Decimal("20000.00")
            )

        assert result.current_amount == Decimal("115000.00")
        assert result.is_achieved is True

    @pytest.mark.asyncio
    async def test_already_achieved_goal_does_not_flip_back(self, mock_db):
        """A goal already marked achieved should stay achieved after another contribution."""
        goal = make_goal(current="100000.00", target="100000.00", is_achieved=True)

        with patch.object(FinancialGoalCRUD, "get", new=AsyncMock(return_value=goal)):
            result = await FinancialGoalCRUD.update_progress(
                mock_db, goal_id=1, user_id=1, amount_to_add=Decimal("5000.00")
            )

        assert result.is_achieved is True

    @pytest.mark.asyncio
    async def test_nonexistent_goal_returns_none(self, mock_db):
        with patch.object(FinancialGoalCRUD, "get", new=AsyncMock(return_value=None)):
            result = await FinancialGoalCRUD.update_progress(
                mock_db, goal_id=999, user_id=1, amount_to_add=Decimal("1000.00")
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_commit_called_on_success(self, mock_db):
        goal = make_goal(current="0.00", target="50000.00")

        with patch.object(FinancialGoalCRUD, "get", new=AsyncMock(return_value=goal)):
            await FinancialGoalCRUD.update_progress(
                mock_db, goal_id=1, user_id=1, amount_to_add=Decimal("1000.00")
            )

        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_refresh_called_on_success(self, mock_db):
        goal = make_goal(current="0.00", target="50000.00")

        with patch.object(FinancialGoalCRUD, "get", new=AsyncMock(return_value=goal)):
            await FinancialGoalCRUD.update_progress(
                mock_db, goal_id=1, user_id=1, amount_to_add=Decimal("1000.00")
            )

        mock_db.refresh.assert_awaited_once_with(goal)

    @pytest.mark.asyncio
    async def test_commit_not_called_when_goal_missing(self, mock_db):
        with patch.object(FinancialGoalCRUD, "get", new=AsyncMock(return_value=None)):
            await FinancialGoalCRUD.update_progress(
                mock_db, goal_id=404, user_id=1, amount_to_add=Decimal("500.00")
            )

        mock_db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_small_decimal_contribution_precision(self, mock_db):
        """Decimal arithmetic must be precise — no float rounding errors."""
        goal = make_goal(current="0.10", target="1000.00")

        with patch.object(FinancialGoalCRUD, "get", new=AsyncMock(return_value=goal)):
            result = await FinancialGoalCRUD.update_progress(
                mock_db, goal_id=1, user_id=1, amount_to_add=Decimal("0.20")
            )

        # Exact decimal arithmetic: 0.10 + 0.20 = 0.30 (not 0.30000000000000004)
        assert result.current_amount == Decimal("0.30")

    @pytest.mark.asyncio
    async def test_wrong_user_id_returns_none(self, mock_db):
        """A goal that belongs to user 1 must not be accessible by user 2."""
        with patch.object(FinancialGoalCRUD, "get", new=AsyncMock(return_value=None)):
            result = await FinancialGoalCRUD.update_progress(
                mock_db, goal_id=1, user_id=2, amount_to_add=Decimal("1000.00")
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_contribution_added_to_existing_nonzero_amount(self, mock_db):
        goal = make_goal(current="14000.00", target="520000.00")

        with patch.object(FinancialGoalCRUD, "get", new=AsyncMock(return_value=goal)):
            result = await FinancialGoalCRUD.update_progress(
                mock_db, goal_id=1, user_id=1, amount_to_add=Decimal("14000.00")
            )

        assert result.current_amount == Decimal("28000.00")
        assert result.is_achieved is False
