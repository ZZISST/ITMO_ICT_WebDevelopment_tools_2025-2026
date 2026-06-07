from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routers.auth import get_current_user
from app.api.schemas.finance import (
    PlannedVsActualSummary,
    TransactionCreate,
    TransactionResponse,
    TransactionType,
    TransactionUpdate,
)
from app.core.database import get_async_session
from app.core.db.crud.finance.budget import CategoryCRUD
from app.core.db.crud.finance.transaction import TransactionCRUD
from app.core.db.models.finance import TransactionType as ModelTransactionType
from app.core.db.models.user import User

router = APIRouter(prefix="/finance/transactions", tags=["Transactions"])


@router.get("/", response_model=List[TransactionResponse])
async def get_user_transactions(
    skip: int = Query(0, ge=0, description="Количество пропускаемых записей"),
    limit: int = Query(50, ge=1, le=1000, description="Количество записей на странице"),
    transaction_type: Optional[TransactionType] = Query(
        None, description="Тип транзакции"
    ),
    category_id: Optional[int] = Query(None, description="ID категории"),
    start_date: Optional[datetime] = Query(None, description="Начальная дата"),
    end_date: Optional[datetime] = Query(None, description="Конечная дата"),
    is_planned: Optional[bool] = Query(None, description="Планируемая или фактическая"),
    search: Optional[str] = Query(None, description="Поиск по описанию и заметкам"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    if (
        end_date is not None
        and end_date.hour == 0
        and end_date.minute == 0
        and end_date.second == 0
    ):
        end_date = end_date.replace(hour=23, minute=59, second=59)

    return await TransactionCRUD.get_user_transactions(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        transaction_type=ModelTransactionType(transaction_type.value)
        if transaction_type
        else None,
        category_id=category_id,
        start_date=start_date,
        end_date=end_date,
        is_planned=is_planned,
        search=search,
    )


@router.post(
    "/", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED
)
async def create_transaction(
    transaction_data: TransactionCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    # Проверяем существование категории
    category = await CategoryCRUD.get(db, transaction_data.category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Категория не найдена"
        )

    transaction = await TransactionCRUD.create(db, current_user.id, transaction_data)

    return transaction


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Получить транзакцию по ID"""

    transaction = await TransactionCRUD.get(db, transaction_id, current_user.id)
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Транзакция не найдена"
        )

    return transaction


@router.put("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: int,
    transaction_data: TransactionUpdate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Обновить транзакцию"""

    transaction = await TransactionCRUD.update(
        db, transaction_id, current_user.id, transaction_data
    )
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Транзакция не найдена"
        )

    return transaction


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Удалить транзакцию"""

    success = await TransactionCRUD.delete(db, transaction_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Транзакция не найдена"
        )


@router.get("/stats/summary", response_model=dict)
async def get_transaction_stats(
    start_date: Optional[datetime] = Query(None, description="Начальная дата"),
    end_date: Optional[datetime] = Query(None, description="Конечная дата"),
    category_id: Optional[int] = Query(None, description="ID категории"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Получить статистику транзакций"""

    # По умолчанию берем текущий месяц
    if not start_date:
        start_date = datetime.utcnow().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
    if not end_date:
        end_date = datetime.utcnow()

    period_str = f"{start_date.strftime('%Y-%m')}_to_{end_date.strftime('%Y-%m')}"

    stats = await TransactionCRUD.get_transaction_stats(
        db=db,
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        category_id=category_id,
    )

    return stats


@router.get("/stats/planned-vs-actual", response_model=PlannedVsActualSummary)
async def get_planned_vs_actual(
    start_date: Optional[datetime] = Query(None, description="Начальная дата"),
    end_date: Optional[datetime] = Query(None, description="Конечная дата"),
    category_id: Optional[int] = Query(None, description="ID категории"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    period_start = start_date or datetime.utcnow().replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    period_end = end_date or datetime.utcnow()

    if (
        period_end is not None
        and period_end.hour == 0
        and period_end.minute == 0
        and period_end.second == 0
    ):
        period_end = period_end.replace(hour=23, minute=59, second=59)

    totals = await TransactionCRUD.get_planned_vs_actual_totals(
        db=db,
        user_id=current_user.id,
        start_date=period_start,
        end_date=period_end,
        category_id=category_id,
        transaction_type=ModelTransactionType.EXPENSE,
    )

    total_planned = totals["total_planned"]
    total_actual = totals["total_actual"]

    period_str = (
        f"{period_start.strftime('%Y-%m-%d')}_{period_end.strftime('%Y-%m-%d')}"
    )

    return PlannedVsActualSummary(
        period=period_str,
        total_planned=total_planned,
        total_actual=total_actual,
        variance=total_planned - total_actual,
        transactions=[],
    )


@router.get("/stats/top-expenses", response_model=List[TransactionResponse])
async def get_top_expenses(
    limit: int = Query(10, ge=1, le=100, description="Количество топ трат"),
    start_date: Optional[datetime] = Query(None, description="Начальная дата"),
    end_date: Optional[datetime] = Query(None, description="Конечная дата"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Получить топ расходов"""

    return await TransactionCRUD.get_top_expenses(
        db=db,
        user_id=current_user.id,
        limit=limit,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/recurring", response_model=List[TransactionResponse])
async def get_recurring_transactions(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Получить регулярные транзакции"""

    return await TransactionCRUD.get_recurring_transactions(db, current_user.id)


@router.post("/quick/expense", response_model=TransactionResponse)
async def create_quick_expense(
    category_id: int,
    amount: float,
    description: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Быстро создать расход"""

    transaction_data = TransactionCreate(
        category_id=category_id,
        amount=Decimal(str(amount)),
        transaction_type=TransactionType.EXPENSE,
        description=description,
        notes=None,
        transaction_date=datetime.utcnow(),
        is_planned=False,
    )

    return await create_transaction(transaction_data, db, current_user)


@router.post("/quick/income", response_model=TransactionResponse)
async def create_quick_income(
    category_id: int,
    amount: float,
    description: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Быстро создать доход"""

    transaction_data = TransactionCreate(
        category_id=category_id,
        amount=Decimal(str(amount)),
        transaction_type=TransactionType.INCOME,
        description=description,
        notes=None,
        transaction_date=datetime.utcnow(),
        is_planned=False,
    )

    return await create_transaction(transaction_data, db, current_user)
