import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routers.auth import get_current_user
from app.api.schemas.finance import (
    FinancialAnalysisCreate,
    FinancialAnalysisResponse,
    FinancialGoalCreate,
    FinancialGoalResponse,
    FinancialGoalUpdate,
    TransactionCreate,
)
from app.core.database import get_async_session
from app.core.db.crud.finance.analysis import (
    FinancialAnalysisCRUD,
    FinancialGoalCRUD,
)
from app.core.db.crud.finance.budget import CategoryCRUD
from app.core.db.crud.finance.transaction import TransactionCRUD
from app.core.db.models.finance import TransactionType
from app.core.db.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/finance/analysis", tags=["Financial Analysis & Goals"])


@router.get("/goals", response_model=List[FinancialGoalResponse])
async def get_financial_goals(
    active_only: bool = Query(True, description="Показать только активные цели"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    return await FinancialGoalCRUD.get_user_goals(
        db=db, user_id=current_user.id, active_only=active_only, skip=skip, limit=limit
    )


@router.post(
    "/goals", response_model=FinancialGoalResponse, status_code=status.HTTP_201_CREATED
)
async def create_financial_goal(
    goal_data: FinancialGoalCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    goal = await FinancialGoalCRUD.create(db, current_user.id, goal_data)

    return goal


@router.get("/goals/{goal_id}", response_model=FinancialGoalResponse)
async def get_financial_goal(
    goal_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    goal = await FinancialGoalCRUD.get(db, goal_id, current_user.id)
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Финансовая цель не найдена"
        )

    return goal


@router.put("/goals/{goal_id}", response_model=FinancialGoalResponse)
async def update_financial_goal(
    goal_id: int,
    goal_data: FinancialGoalUpdate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    goal = await FinancialGoalCRUD.update(db, goal_id, current_user.id, goal_data)
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Финансовая цель не найдена"
        )

    return goal


class GoalProgressBody(BaseModel):
    """request body for goal progress update."""

    amount: float = Field(..., gt=0, description="Сумма для добавления к прогрессу")


@router.post("/goals/{goal_id}/progress")
async def update_goal_progress(
    goal_id: int,
    body: GoalProgressBody,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    amount = Decimal(str(body.amount))

    goal = await FinancialGoalCRUD.update_progress(db, goal_id, current_user.id, amount)
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Финансовая цель не найдена"
        )

    savings_category = await CategoryCRUD.get_or_create_savings_category(db)
    transaction_data = TransactionCreate(
        category_id=savings_category.id,
        amount=amount,
        transaction_type=TransactionType.EXPENSE,
        description=f"Взнос на цель: {goal.title}",
        notes=f"Автоматически создано при пополнении цели #{goal.id}",
        transaction_date=datetime.utcnow(),
        is_planned=True,
        is_recurring=False,
    )
    await TransactionCRUD.create(db, current_user.id, transaction_data)

    return {"message": "Прогресс обновлен", "is_achieved": goal.is_achieved}


@router.delete("/goals/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_financial_goal(
    goal_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Удалить финансовую цель"""

    success = await FinancialGoalCRUD.delete(db, goal_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Финансовая цель не найдена"
        )


@router.get("/goals/summary", response_model=dict)
async def get_goals_summary(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Получить сводку по финансовым целям"""

    return await FinancialGoalCRUD.get_goals_summary(db, current_user.id)


# === ФИНАНСОВЫЙ АНАЛИЗ ===


@router.get("/analyses", response_model=List[FinancialAnalysisResponse])
async def get_financial_analyses(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    return await FinancialAnalysisCRUD.get_user_analyses(
        db=db, user_id=current_user.id, skip=skip, limit=limit
    )


@router.get("/analyses/latest", response_model=Optional[FinancialAnalysisResponse])
async def get_latest_analysis(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    return await FinancialAnalysisCRUD.get_latest_analysis(db, current_user.id)


async def perform_financial_analysis(
    user_id: int,
    analysis_id: int,
    start_date: datetime,
    end_date: datetime,
    db: AsyncSession,
):
    try:
        from app.core.db.models.finance import AnalysisStatus

        await FinancialAnalysisCRUD.update_status(
            db, analysis_id, user_id, AnalysisStatus.PROCESSING
        )

        stats = await TransactionCRUD.get_transaction_stats(
            db=db, user_id=user_id, start_date=start_date, end_date=end_date
        )

        await FinancialAnalysisCRUD.update_analysis_results(
            db=db,
            analysis_id=analysis_id,
            user_id=user_id,
            total_income=stats["total_income"],
            total_expenses=stats["total_expenses"],
            savings_rate=stats["savings_rate"],
        )

    except Exception as e:
        from app.core.db.models.finance import AnalysisStatus

        await FinancialAnalysisCRUD.update_status(
            db, analysis_id, user_id, AnalysisStatus.FAILED
        )
        raise e


@router.post(
    "/analyses",
    response_model=FinancialAnalysisResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_financial_analysis(
    analysis_data: FinancialAnalysisCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    analysis = await FinancialAnalysisCRUD.create(db, current_user.id, analysis_data)

    background_tasks.add_task(
        perform_financial_analysis,
        current_user.id,
        analysis.id,
        analysis_data.period_start,
        analysis_data.period_end,
        db,
    )

    return analysis


async def _resolve_category_names(
    db: AsyncSession, stats: Dict[str, Any]
) -> Dict[str, Any]:
    enriched = dict(stats)
    enriched_cats = []
    for cat in stats.get("category_breakdown", []):
        cat_id = cat["category_id"]
        category = await CategoryCRUD.get(db, cat_id)
        cat_name = category.name if category else f"Категория {cat_id}"
        enriched_cats.append({**cat, "category_name": cat_name})
    enriched["category_breakdown"] = enriched_cats
    return enriched
