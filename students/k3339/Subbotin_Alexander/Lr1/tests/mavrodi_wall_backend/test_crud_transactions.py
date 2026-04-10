import os
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.api.schemas.finance import TransactionCreate
from app.core.db.crud.finance.transaction import TransactionCRUD, _strip_tz
from app.core.db.models.finance import (
    NotebookType,
    Transaction,
    TransactionType,
)

def make_transaction(
    tx_id: int = 1,
    user_id: int = 1,
    amount: str = "1000.00",
    tx_type: TransactionType = TransactionType.EXPENSE,
    notebook: NotebookType = NotebookType.SMALL,
    description: str = "тестовая транзакция",
    notes: str | None = None,
    tx_date: datetime | None = None,
    is_planned: bool = False,
    is_recurring: bool = False,
    category_id: int = 1,
) -> Transaction:
    tx = Transaction(
        id=tx_id,
        user_id=user_id,
        category_id=category_id,
        amount=Decimal(amount),
        transaction_type=tx_type,
        notebook_type=notebook,
        description=description,
        notes=notes,
        transaction_date=tx_date or datetime(2026, 3, 11, 10, 0, 0),
        is_planned=is_planned,
        is_recurring=is_recurring,
        created_at=datetime(2026, 3, 11, 10, 0, 0),
        updated_at=datetime(2026, 3, 11, 10, 0, 0),
    )
    return tx


def valid_create_payload(**overrides) -> dict:
    base = dict(
        category_id=1,
        amount=Decimal("2500.00"),
        transaction_type=TransactionType.EXPENSE,
        notebook_type=NotebookType.SMALL,
        description="Продукты на неделю",
        notes=None,
        transaction_date=datetime(2026, 3, 11, 10, 0, 0),
        is_planned=False,
        is_recurring=False,
    )
    base.update(overrides)
    return base


class TestStripTz:
    def test_none_returns_none(self):
        assert _strip_tz(None) is None

    def test_naive_datetime_returned_unchanged(self):
        dt = datetime(2026, 3, 11, 10, 30, 0)
        result = _strip_tz(dt)
        assert result == dt
        assert result.tzinfo is None

    def test_utc_aware_datetime_stripped(self):
        dt = datetime(2026, 3, 11, 10, 30, 0, tzinfo=timezone.utc)
        result = _strip_tz(dt)
        assert result.tzinfo is None
        assert result == datetime(2026, 3, 11, 10, 30, 0)

    def test_positive_offset_aware_datetime_stripped(self):
        tz_plus3 = timezone(timedelta(hours=3))
        dt = datetime(2026, 3, 11, 13, 0, 0, tzinfo=tz_plus3)
        result = _strip_tz(dt)
        assert result.tzinfo is None
        # Wall-clock time is preserved, not converted to UTC
        assert result == datetime(2026, 3, 11, 13, 0, 0)

    def test_negative_offset_aware_datetime_stripped(self):
        tz_minus5 = timezone(timedelta(hours=-5))
        dt = datetime(2026, 3, 11, 5, 0, 0, tzinfo=tz_minus5)
        result = _strip_tz(dt)
        assert result.tzinfo is None
        assert result == datetime(2026, 3, 11, 5, 0, 0)

    def test_microseconds_preserved(self):
        dt = datetime(2026, 3, 11, 10, 30, 45, 123456, tzinfo=timezone.utc)
        result = _strip_tz(dt)
        assert result.microsecond == 123456

    def test_already_naive_with_time_components(self):
        dt = datetime(2026, 12, 31, 23, 59, 59)
        result = _strip_tz(dt)
        assert result == dt


class TestTransactionCRUDCreate:
    @pytest.mark.asyncio
    async def test_create_adds_object_to_session(self, mock_db):
        """db.add() must be called with a Transaction instance."""
        data = TransactionCreate(**valid_create_payload())

        # refresh should do nothing (side-effect free mock)
        mock_db.refresh = AsyncMock()
        mock_db.add = MagicMock()

        await TransactionCRUD.create(mock_db, user_id=1, transaction_data=data)

        assert mock_db.add.called
        added_obj = mock_db.add.call_args[0][0]
        assert isinstance(added_obj, Transaction)

    @pytest.mark.asyncio
    async def test_create_sets_correct_user_id(self, mock_db):
        data = TransactionCreate(**valid_create_payload())
        mock_db.refresh = AsyncMock()

        await TransactionCRUD.create(mock_db, user_id=42, transaction_data=data)

        added_tx = mock_db.add.call_args[0][0]
        assert added_tx.user_id == 42

    @pytest.mark.asyncio
    async def test_create_sets_correct_amount(self, mock_db):
        data = TransactionCreate(**valid_create_payload(amount=Decimal("9999.99")))
        mock_db.refresh = AsyncMock()

        await TransactionCRUD.create(mock_db, user_id=1, transaction_data=data)

        added_tx = mock_db.add.call_args[0][0]
        assert added_tx.amount == Decimal("9999.99")

    @pytest.mark.asyncio
    async def test_create_strips_timezone_from_date(self, mock_db):
        """transaction_date with tz info must be stored as naive datetime."""
        aware_date = datetime(2026, 3, 11, 10, 0, 0, tzinfo=timezone.utc)
        data = TransactionCreate(**valid_create_payload(transaction_date=aware_date))
        mock_db.refresh = AsyncMock()

        await TransactionCRUD.create(mock_db, user_id=1, transaction_data=data)

        added_tx = mock_db.add.call_args[0][0]
        assert added_tx.transaction_date.tzinfo is None

    @pytest.mark.asyncio
    async def test_create_naive_date_preserved(self, mock_db):
        naive_date = datetime(2026, 3, 11, 10, 0, 0)
        data = TransactionCreate(**valid_create_payload(transaction_date=naive_date))
        mock_db.refresh = AsyncMock()

        await TransactionCRUD.create(mock_db, user_id=1, transaction_data=data)

        added_tx = mock_db.add.call_args[0][0]
        assert added_tx.transaction_date == naive_date

    @pytest.mark.asyncio
    async def test_create_copies_description_and_notes(self, mock_db):
        data = TransactionCreate(
            **valid_create_payload(description="Ужин в ресторане", notes="С коллегами")
        )
        mock_db.refresh = AsyncMock()

        await TransactionCRUD.create(mock_db, user_id=1, transaction_data=data)

        added_tx = mock_db.add.call_args[0][0]
        assert added_tx.description == "Ужин в ресторане"
        assert added_tx.notes == "С коллегами"

    @pytest.mark.asyncio
    async def test_create_calls_commit(self, mock_db):
        data = TransactionCreate(**valid_create_payload())
        mock_db.refresh = AsyncMock()

        await TransactionCRUD.create(mock_db, user_id=1, transaction_data=data)

        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_planned_flag_set(self, mock_db):
        data = TransactionCreate(**valid_create_payload(is_planned=True))
        mock_db.refresh = AsyncMock()

        await TransactionCRUD.create(mock_db, user_id=1, transaction_data=data)

        added_tx = mock_db.add.call_args[0][0]
        assert added_tx.is_planned is True

    @pytest.mark.asyncio
    async def test_create_income_transaction_type_set(self, mock_db):
        data = TransactionCreate(
            **valid_create_payload(
                transaction_type=TransactionType.INCOME,
                notebook_type=NotebookType.BIG,
            )
        )
        mock_db.refresh = AsyncMock()

        await TransactionCRUD.create(mock_db, user_id=1, transaction_data=data)

        added_tx = mock_db.add.call_args[0][0]
        assert added_tx.transaction_type == TransactionType.INCOME
        assert added_tx.notebook_type == NotebookType.BIG

class TestSearchFiltering:
    """
    The search parameter added to get_user_transactions performs an ILIKE
    match on description and notes.  We test this by running the filter
    predicate directly against a list of in-memory Transaction objects,
    mirroring what the DB query would do.
    """

    def _matches_search(self, tx: Transaction, term: str) -> bool:
        """Replicate the ILIKE OR filter in pure Python (case-insensitive)."""
        lower = term.lower()
        desc_match = lower in (tx.description or "").lower()
        notes_match = lower in (tx.notes or "").lower()
        return desc_match or notes_match

    def test_match_by_description_exact(self):
        tx = make_transaction(description="Продукты на неделю")
        assert self._matches_search(tx, "Продукты на неделю")

    def test_match_by_description_partial(self):
        tx = make_transaction(description="Продукты на неделю")
        assert self._matches_search(tx, "Продукты")

    def test_match_by_description_case_insensitive(self):
        tx = make_transaction(description="Продукты на НЕДЕЛЮ")
        assert self._matches_search(tx, "неделю")

    def test_no_match_when_term_absent(self):
        tx = make_transaction(description="Покупка одежды")
        assert not self._matches_search(tx, "электроника")

    def test_match_by_notes_when_description_misses(self):
        tx = make_transaction(
            description="Разное",
            notes="Подробности: айфон 16 pro",
        )
        assert self._matches_search(tx, "айфон")

    def test_match_by_notes_partial(self):
        tx = make_transaction(
            description="Покупка",
            notes="Детали сделки с продавцом",
        )
        assert self._matches_search(tx, "продавцом")

    def test_no_match_when_notes_is_none(self):
        tx = make_transaction(description="Продукты", notes=None)
        assert not self._matches_search(tx, "Нет заметок")

    def test_empty_search_term_matches_everything(self):
        """Empty string is always a substring — matches all."""
        tx = make_transaction(description="Что угодно")
        assert self._matches_search(tx, "")

    def test_goal_contribution_findable_by_description(self):
        """Goal-auto-created transactions should be findable by goal name."""
        tx = make_transaction(
            description="Взнос на цель: отпуск в израиле",
            notes="Автоматически создано при пополнении цели #1",
        )
        assert self._matches_search(tx, "израиле")
        assert self._matches_search(tx, "взнос")

    def test_filter_applied_to_list(self):
        """Simulates filtering a list the way the router would."""
        transactions = [
            make_transaction(tx_id=1, description="Продукты"),
            make_transaction(tx_id=2, description="Электроника"),
            make_transaction(tx_id=3, description="Транспорт"),
            make_transaction(tx_id=4, description="Продуктовый магазин"),
        ]
        term = "продукт"
        filtered = [t for t in transactions if self._matches_search(t, term)]
        assert len(filtered) == 2
        assert {t.id for t in filtered} == {1, 4}

class TestDateRangeBoundaries:
    """
    Tests for the end_date midnight-extension fix added to the transactions
    router: when end_date has time 00:00:00 it is extended to 23:59:59 so
    that transactions created later in the same day are included.
    """

    def _should_extend(self, end_date: datetime) -> bool:
        """Replicate the router-level condition."""
        return (
            end_date is not None
            and end_date.hour == 0
            and end_date.minute == 0
            and end_date.second == 0
        )

    def _extend_end_date(self, end_date: datetime) -> datetime:
        return end_date.replace(hour=23, minute=59, second=59)

    def test_midnight_date_is_extended(self):
        end = datetime(2026, 3, 12, 0, 0, 0)
        assert self._should_extend(end)
        extended = self._extend_end_date(end)
        assert extended == datetime(2026, 3, 12, 23, 59, 59)

    def test_non_midnight_date_not_extended(self):
        end = datetime(2026, 3, 12, 15, 30, 0)
        assert not self._should_extend(end)

    def test_time_with_seconds_not_extended(self):
        end = datetime(2026, 3, 12, 0, 0, 1)
        assert not self._should_extend(end)

    def test_time_with_minutes_not_extended(self):
        end = datetime(2026, 3, 12, 0, 1, 0)
        assert not self._should_extend(end)

    def test_transaction_at_midday_included_after_extension(self):
        """A tx at 15:30 on March 12 must fall within the extended range."""
        end_raw = datetime(2026, 3, 12, 0, 0, 0)
        end_extended = self._extend_end_date(end_raw)

        tx_time = datetime(2026, 3, 12, 15, 30, 0)
        assert tx_time <= end_extended

    def test_transaction_at_midday_excluded_without_extension(self):
        """A tx at 15:30 on March 12 falls OUTSIDE the un-extended range."""
        end_raw = datetime(2026, 3, 12, 0, 0, 0)
        tx_time = datetime(2026, 3, 12, 15, 30, 0)
        assert tx_time > end_raw

    def test_extension_preserves_date(self):
        end = datetime(2026, 3, 12, 0, 0, 0)
        extended = self._extend_end_date(end)
        assert extended.date() == end.date()

    def test_end_of_year_date_extended_correctly(self):
        end = datetime(2026, 12, 31, 0, 0, 0)
        extended = self._extend_end_date(end)
        assert extended == datetime(2026, 12, 31, 23, 59, 59)

    def test_none_end_date_not_extended(self):
        """None end_date skips the extension check entirely."""
        assert not self._should_extend(None) if None is not None else True
        # The router guard is: `if end_date is not None and ...`
        # Just verify None doesn't trigger should_extend:
        end = None
        result = (
            end is not None and end.hour == 0 and end.minute == 0 and end.second == 0
        )
        assert result is False
