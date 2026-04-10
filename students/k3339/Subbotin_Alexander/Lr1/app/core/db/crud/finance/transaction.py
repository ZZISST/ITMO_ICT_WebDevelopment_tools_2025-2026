from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, case, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas.finance import TransactionCreate, TransactionUpdate
from app.core.db.models.finance import Transaction, TransactionType


def _strip_tz(dt: Optional[datetime]) -> Optional[datetime]:
    """strip tzinfo to match timestamp without time zone."""
    if dt is not None and dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


class TransactionCRUD:
    """CRUD операции для транзакций"""

    @staticmethod
    async def create(
        db: AsyncSession, user_id: int, transaction_data: TransactionCreate
    ) -> Transaction:
        """Создать новую транзакцию"""
        tx_date = transaction_data.transaction_date
        if tx_date is not None and tx_date.tzinfo is not None:
            tx_date = tx_date.replace(tzinfo=None)

        transaction = Transaction(
            user_id=user_id,
            category_id=transaction_data.category_id,
            amount=transaction_data.amount,
            transaction_type=transaction_data.transaction_type,
            description=transaction_data.description,
            notes=transaction_data.notes,
            transaction_date=tx_date,
            is_planned=transaction_data.is_planned,
            is_recurring=transaction_data.is_recurring,
        )
        db.add(transaction)
        await db.commit()
        await db.refresh(transaction, ["category"])
        return transaction

    @staticmethod
    async def get(
        db: AsyncSession, transaction_id: int, user_id: int
    ) -> Optional[Transaction]:
        """Получить транзакцию по ID"""
        result = await db.execute(
            select(Transaction)
            .options(selectinload(Transaction.category))
            .where(
                and_(Transaction.id == transaction_id, Transaction.user_id == user_id)
            )
        )
        return result.scalars().first()

    @staticmethod
    async def get_user_transactions(
        db: AsyncSession,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        transaction_type: Optional[TransactionType] = None,
        category_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        is_planned: Optional[bool] = None,
        search: Optional[str] = None,
        order_by_date: bool = True,
    ) -> List[Transaction]:
        """Получить транзакции пользователя с фильтрацией"""
        start_date = _strip_tz(start_date)
        end_date = _strip_tz(end_date)

        query = (
            select(Transaction)
            .options(selectinload(Transaction.category))
            .where(Transaction.user_id == user_id)
        )

        if transaction_type:
            query = query.where(Transaction.transaction_type == transaction_type)

        if category_id:
            query = query.where(Transaction.category_id == category_id)

        if start_date:
            query = query.where(Transaction.transaction_date >= start_date)

        if end_date:
            query = query.where(Transaction.transaction_date <= end_date)

        if is_planned is not None:
            query = query.where(Transaction.is_planned == is_planned)

        if search:
            pattern = f"%{search}%"
            query = query.where(
                or_(
                    Transaction.description.ilike(pattern),
                    Transaction.notes.ilike(pattern),
                )
            )

        if order_by_date:
            query = query.order_by(desc(Transaction.transaction_date))
        else:
            query = query.order_by(desc(Transaction.created_at))

        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_daily_transactions(
        db: AsyncSession,
        user_id: int,
        date: datetime,
    ) -> List[Transaction]:
        """Получить транзакции за определенный день"""
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = date.replace(hour=23, minute=59, second=59)

        return await TransactionCRUD.get_user_transactions(
            db=db,
            user_id=user_id,
            start_date=start_of_day,
            end_date=end_of_day,
            limit=1000,
        )

    @staticmethod
    async def update(
        db: AsyncSession,
        transaction_id: int,
        user_id: int,
        transaction_data: TransactionUpdate,
    ) -> Optional[Transaction]:
        """Обновить транзакцию"""
        transaction = await TransactionCRUD.get(db, transaction_id, user_id)
        if not transaction:
            return None

        for field, value in transaction_data.dict(exclude_unset=True).items():
            setattr(transaction, field, value)

        await db.commit()
        await db.refresh(transaction, ["category"])
        return transaction

    @staticmethod
    async def delete(db: AsyncSession, transaction_id: int, user_id: int) -> bool:
        """Удалить транзакцию"""
        transaction = await TransactionCRUD.get(db, transaction_id, user_id)
        if not transaction:
            return False

        await db.delete(transaction)
        await db.commit()
        return True

    @staticmethod
    async def get_transaction_stats(
        db: AsyncSession,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        category_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Получить статистику транзакций"""
        start_date = _strip_tz(start_date)
        end_date = _strip_tz(end_date)

        # Базовый запрос
        base_query_conditions = [Transaction.user_id == user_id]

        if start_date:
            base_query_conditions.append(Transaction.transaction_date >= start_date)
        if end_date:
            base_query_conditions.append(Transaction.transaction_date <= end_date)
        if category_id:
            base_query_conditions.append(Transaction.category_id == category_id)

        # Общая статистика
        stats_query = select(
            func.sum(
                case(
                    (
                        Transaction.transaction_type == TransactionType.INCOME,
                        Transaction.amount,
                    ),
                    else_=0,
                )
            ).label("total_income"),
            func.sum(
                case(
                    (
                        Transaction.transaction_type == TransactionType.EXPENSE,
                        Transaction.amount,
                    ),
                    else_=0,
                )
            ).label("total_expenses"),
            func.count(Transaction.id).label("total_transactions"),
            func.avg(
                case(
                    (
                        Transaction.transaction_type == TransactionType.EXPENSE,
                        Transaction.amount,
                    ),
                    else_=None,
                )
            ).label("avg_expense"),
            func.max(
                case(
                    (
                        Transaction.transaction_type == TransactionType.EXPENSE,
                        Transaction.amount,
                    ),
                    else_=None,
                )
            ).label("max_expense"),
            func.sum(
                case(
                    (
                        and_(
                            Transaction.transaction_type == TransactionType.EXPENSE,
                            Transaction.is_planned == True,
                        ),
                        Transaction.amount,
                    ),
                    else_=0,
                )
            ).label("planned_expenses"),
            func.sum(
                case(
                    (
                        and_(
                            Transaction.transaction_type == TransactionType.EXPENSE,
                            Transaction.is_planned == False,
                        ),
                        Transaction.amount,
                    ),
                    else_=0,
                )
            ).label("actual_expenses"),
        ).where(and_(*base_query_conditions))

        result = await db.execute(stats_query)
        stats = result.first()

        # Статистика по категориям
        category_stats_query = (
            select(
                Transaction.category_id,
                func.sum(Transaction.amount).label("category_total"),
                func.count(Transaction.id).label("category_count"),
            )
            .where(
                and_(
                    *base_query_conditions,
                    Transaction.transaction_type == TransactionType.EXPENSE,
                )
            )
            .group_by(Transaction.category_id)
            .order_by(desc("category_total"))
        )

        category_result = await db.execute(category_stats_query)
        category_stats = category_result.all()

        total_income = stats.total_income or Decimal("0")
        total_expenses = stats.total_expenses or Decimal("0")
        savings = total_income - total_expenses
        savings_rate = float(savings / total_income * 100) if total_income > 0 else 0

        return {
            "total_income": total_income,
            "total_expenses": total_expenses,
            "savings": savings,
            "savings_rate": savings_rate,
            "total_transactions": stats.total_transactions or 0,
            "avg_expense": stats.avg_expense or Decimal("0"),
            "max_expense": stats.max_expense or Decimal("0"),
            "planned_expenses": stats.planned_expenses or Decimal("0"),
            "actual_expenses": stats.actual_expenses or Decimal("0"),
            "category_breakdown": [
                {
                    "category_id": row.category_id,
                    "total": row.category_total,
                    "count": row.category_count,
                }
                for row in category_stats
            ],
        }

    @staticmethod
    async def get_planned_vs_actual_totals(
        db: AsyncSession,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        category_id: Optional[int] = None,
        transaction_type: TransactionType = TransactionType.EXPENSE,
    ) -> Dict[str, Decimal]:
        """get plan/fact totals without loading rows."""
        start_date = _strip_tz(start_date)
        end_date = _strip_tz(end_date)

        conditions = [Transaction.user_id == user_id]
        if start_date:
            conditions.append(Transaction.transaction_date >= start_date)
        if end_date:
            conditions.append(Transaction.transaction_date <= end_date)
        if category_id:
            conditions.append(Transaction.category_id == category_id)

        conditions.append(Transaction.transaction_type == transaction_type)

        q = select(
            func.coalesce(
                func.sum(
                    case((Transaction.is_planned == True, Transaction.amount), else_=0)
                ),
                0,
            ).label("total_planned"),
            func.coalesce(
                func.sum(
                    case((Transaction.is_planned == False, Transaction.amount), else_=0)
                ),
                0,
            ).label("total_actual"),
        ).where(and_(*conditions))

        res = await db.execute(q)
        row = res.first()

        return {
            "total_planned": row.total_planned
            if row and row.total_planned is not None
            else Decimal("0"),
            "total_actual": row.total_actual
            if row and row.total_actual is not None
            else Decimal("0"),
        }

    @staticmethod
    async def get_top_expenses(
        db: AsyncSession,
        user_id: int,
        limit: int = 10,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Transaction]:
        """Получить топ расходов"""
        start_date = _strip_tz(start_date)
        end_date = _strip_tz(end_date)

        query = (
            select(Transaction)
            .options(selectinload(Transaction.category))
            .where(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.transaction_type == TransactionType.EXPENSE,
                )
            )
            .order_by(desc(Transaction.amount))
            .limit(limit)
        )

        if start_date:
            query = query.where(Transaction.transaction_date >= start_date)
        if end_date:
            query = query.where(Transaction.transaction_date <= end_date)

        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_recurring_transactions(
        db: AsyncSession, user_id: int
    ) -> List[Transaction]:
        """Получить регулярные транзакции"""
        result = await db.execute(
            select(Transaction)
            .options(selectinload(Transaction.category))
            .where(
                and_(Transaction.user_id == user_id, Transaction.is_recurring == True)
            )
            .order_by(Transaction.transaction_date)
        )
        return result.scalars().all()
