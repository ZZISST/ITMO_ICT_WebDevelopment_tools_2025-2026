from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routers.auth import get_current_user
from app.api.schemas.finance import (
    BudgetCreate,
    BudgetResponse,
    BudgetUpdate,
    CategoryCreate,
    CategoryResponse,
    CategoryType,
    CategoryUpdate,
)
from app.core.database import get_async_session
from app.core.db.crud.finance.budget import BudgetCRUD, CategoryCRUD
from app.core.db.models.finance import CategoryType as ModelCategoryType
from app.core.db.models.finance import Transaction
from app.core.db.models.finance import TransactionType as ModelTransactionType
from app.core.db.models.user import User

router = APIRouter(prefix="/finance/budget", tags=["Budget & Categories"])


async def _enrich_budgets_with_spending(db: AsyncSession, budgets: list) -> list:
    """Compute spent/remaining for each budget by summing actual expense transactions."""
    enriched = []
    for budget in budgets:
        # Query total actual expenses for this category in the budget period
        result = await db.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                and_(
                    Transaction.user_id == budget.user_id,
                    Transaction.category_id == budget.category_id,
                    Transaction.transaction_type == ModelTransactionType.EXPENSE,
                    ~Transaction.is_planned,
                    Transaction.transaction_date >= budget.period_start,
                    Transaction.transaction_date <= budget.period_end,
                )
            )
        )
        spent = result.scalar() or Decimal("0")

        # Set these as attributes so the Pydantic model can read them
        budget.spent = spent
        budget.remaining = budget.amount - spent
        enriched.append(budget)

    return enriched


@router.get("/categories", response_model=List[CategoryResponse])
async def get_categories(
    category_type: Optional[CategoryType] = Query(
        None, description="Фильтр по типу категории"
    ),
    skip: int = Query(0, ge=0, description="Количество пропускаемых записей"),
    limit: int = Query(
        100, ge=1, le=1000, description="Количество записей на странице"
    ),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Получить список категорий"""

    if category_type:
        categories = await CategoryCRUD.get_by_type(
            db, ModelCategoryType(category_type.value)
        )
    else:
        categories = await CategoryCRUD.get_all(db, skip, limit)

    return categories


@router.get("/categories/default", response_model=List[CategoryResponse])
async def get_default_categories(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Получить стандартные категории"""
    return await CategoryCRUD.get_default_categories(db)


@router.post(
    "/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED
)
async def create_category(
    category_data: CategoryCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Создать новую категорию"""

    # Только администраторы могут создавать категории
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только администраторы могут создавать категории",
        )

    return await CategoryCRUD.create(db, category_data)


@router.get("/categories/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Получить категорию по ID"""

    category = await CategoryCRUD.get(db, category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Категория не найдена"
        )

    return category


@router.put("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    category_data: CategoryUpdate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Обновить категорию"""

    # Только администраторы могут изменять категории
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только администраторы могут изменять категории",
        )

    category = await CategoryCRUD.update(db, category_id, category_data)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Категория не найдена"
        )

    return category


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Удалить категорию"""

    # Только администраторы могут удалять категории
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только администраторы могут удалять категории",
        )

    success = await CategoryCRUD.delete(db, category_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Категория не найдена или не может быть удалена",
        )


@router.post("/categories/init-defaults", response_model=List[CategoryResponse])
async def init_default_categories(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Создать стандартные категории"""

    # Только администраторы могут инициализировать категории
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только администраторы могут инициализировать категории",
        )

    return await CategoryCRUD.init_default_categories(db)


@router.get("/budgets", response_model=List[BudgetResponse])
async def get_user_budgets(
    active_only: bool = Query(True, description="Показать только активные бюджеты"),
    skip: int = Query(0, ge=0, description="Количество пропускаемых записей"),
    limit: int = Query(
        100, ge=1, le=1000, description="Количество записей на странице"
    ),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Получить бюджеты пользователя"""

    budgets = await BudgetCRUD.get_user_budgets(
        db=db, user_id=current_user.id, active_only=active_only, skip=skip, limit=limit
    )

    return await _enrich_budgets_with_spending(db, budgets)


@router.get("/budgets/current", response_model=List[BudgetResponse])
async def get_current_budgets(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Получить текущие активные бюджеты"""

    budgets = await BudgetCRUD.get_current_budgets(db, current_user.id)
    return await _enrich_budgets_with_spending(db, budgets)


@router.post(
    "/budgets", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED
)
async def create_budget(
    budget_data: BudgetCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Создать новый бюджет"""

    # Проверяем существование категории
    category = await CategoryCRUD.get(db, budget_data.category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Категория не найдена"
        )

    budget = await BudgetCRUD.create(db, current_user.id, budget_data)
    return budget


@router.get("/budgets/{budget_id}", response_model=BudgetResponse)
async def get_budget(
    budget_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Получить бюджет по ID"""

    budget = await BudgetCRUD.get(db, budget_id, current_user.id)
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Бюджет не найден"
        )

    return budget


@router.put("/budgets/{budget_id}", response_model=BudgetResponse)
async def update_budget(
    budget_id: int,
    budget_data: BudgetUpdate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Обновить бюджет"""

    budget = await BudgetCRUD.update(db, budget_id, current_user.id, budget_data)
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Бюджет не найден"
        )

    return budget


@router.delete("/budgets/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    budget_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Удалить бюджет"""

    success = await BudgetCRUD.delete(db, budget_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Бюджет не найден"
        )


@router.get("/budgets/summary", response_model=dict)
async def get_budget_summary(
    category_id: Optional[int] = Query(None, description="ID категории для фильтрации"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Получить сводку по бюджетам"""

    return await BudgetCRUD.get_budget_summary(db, current_user.id, category_id)
