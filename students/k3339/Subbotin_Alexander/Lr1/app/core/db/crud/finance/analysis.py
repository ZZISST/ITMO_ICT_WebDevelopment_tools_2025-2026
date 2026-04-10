from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.finance import (
    FinancialAnalysisCreate,
    FinancialGoalCreate,
    FinancialGoalUpdate,
)
from app.core.db.models.finance import AnalysisStatus, FinancialAnalysis, FinancialGoal


class FinancialGoalCRUD:
    """CRUD операции для финансовых целей"""

    @staticmethod
    async def create(
        db: AsyncSession, user_id: int, goal_data: FinancialGoalCreate
    ) -> FinancialGoal:
        """Создать новую финансовую цель"""
        goal = FinancialGoal(
            user_id=user_id,
            title=goal_data.title,
            description=goal_data.description,
            target_amount=goal_data.target_amount,
            target_date=goal_data.target_date,
            priority=goal_data.priority,
        )
        db.add(goal)
        await db.commit()
        await db.refresh(goal)
        return goal

    @staticmethod
    async def get(
        db: AsyncSession, goal_id: int, user_id: int
    ) -> Optional[FinancialGoal]:
        """Получить финансовую цель по ID"""
        result = await db.execute(
            select(FinancialGoal).where(
                and_(FinancialGoal.id == goal_id, FinancialGoal.user_id == user_id)
            )
        )
        return result.scalars().first()

    @staticmethod
    async def get_user_goals(
        db: AsyncSession,
        user_id: int,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> List[FinancialGoal]:
        """Получить финансовые цели пользователя"""
        query = (
            select(FinancialGoal)
            .where(FinancialGoal.user_id == user_id)
            .order_by(FinancialGoal.priority.desc(), FinancialGoal.target_date.asc())
            .offset(skip)
            .limit(limit)
        )

        if active_only:
            query = query.where(FinancialGoal.is_achieved == False)

        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def update(
        db: AsyncSession, goal_id: int, user_id: int, goal_data: FinancialGoalUpdate
    ) -> Optional[FinancialGoal]:
        """Обновить финансовую цель"""
        goal = await FinancialGoalCRUD.get(db, goal_id, user_id)
        if not goal:
            return None

        for field, value in goal_data.dict(exclude_unset=True).items():
            setattr(goal, field, value)

        # Проверяем достижение цели
        if goal.current_amount >= goal.target_amount and not goal.is_achieved:
            goal.is_achieved = True

        await db.commit()
        await db.refresh(goal)
        return goal

    @staticmethod
    async def update_progress(
        db: AsyncSession, goal_id: int, user_id: int, amount_to_add: Decimal
    ) -> Optional[FinancialGoal]:
        """Обновить прогресс по финансовой цели"""
        goal = await FinancialGoalCRUD.get(db, goal_id, user_id)
        if not goal:
            return None

        goal.current_amount += amount_to_add

        if goal.current_amount >= goal.target_amount and not goal.is_achieved:
            goal.is_achieved = True

        await db.commit()
        await db.refresh(goal)
        return goal

    @staticmethod
    async def delete(db: AsyncSession, goal_id: int, user_id: int) -> bool:
        """Удалить финансовую цель"""
        goal = await FinancialGoalCRUD.get(db, goal_id, user_id)
        if not goal:
            return False

        await db.delete(goal)
        await db.commit()
        return True

    @staticmethod
    async def get_goals_summary(db: AsyncSession, user_id: int) -> Dict[str, Any]:
        """Получить сводку по финансовым целям"""
        result = await db.execute(
            select(
                func.count(FinancialGoal.id).label("total_goals"),
                func.sum(case((FinancialGoal.is_achieved == True, 1), else_=0)).label(
                    "achieved_goals"
                ),
                func.sum(FinancialGoal.target_amount).label("total_target"),
                func.sum(FinancialGoal.current_amount).label("total_saved"),
                func.avg(
                    FinancialGoal.current_amount / FinancialGoal.target_amount * 100
                ).label("avg_progress"),
            ).where(FinancialGoal.user_id == user_id)
        )
        summary = result.first()

        return {
            "total_goals": summary.total_goals or 0,
            "achieved_goals": summary.achieved_goals or 0,
            "active_goals": (summary.total_goals or 0) - (summary.achieved_goals or 0),
            "total_target": summary.total_target or Decimal("0"),
            "total_saved": summary.total_saved or Decimal("0"),
            "average_progress": float(summary.avg_progress or 0),
        }


class FinancialAnalysisCRUD:
    """CRUD операции для финансового анализа"""

    @staticmethod
    async def create(
        db: AsyncSession, user_id: int, analysis_data: FinancialAnalysisCreate
    ) -> FinancialAnalysis:
        """Создать новый финансовый анализ"""
        analysis = FinancialAnalysis(
            user_id=user_id,
            period_start=analysis_data.period_start,
            period_end=analysis_data.period_end,
            status=AnalysisStatus.PENDING,
        )
        db.add(analysis)
        await db.commit()
        await db.refresh(analysis)
        return analysis

    @staticmethod
    async def get(
        db: AsyncSession, analysis_id: int, user_id: int
    ) -> Optional[FinancialAnalysis]:
        """Получить финансовый анализ по ID"""
        result = await db.execute(
            select(FinancialAnalysis).where(
                and_(
                    FinancialAnalysis.id == analysis_id,
                    FinancialAnalysis.user_id == user_id,
                )
            )
        )
        return result.scalars().first()

    @staticmethod
    async def get_user_analyses(
        db: AsyncSession, user_id: int, skip: int = 0, limit: int = 50
    ) -> List[FinancialAnalysis]:
        """Получить финансовые анализы пользователя"""
        result = await db.execute(
            select(FinancialAnalysis)
            .where(FinancialAnalysis.user_id == user_id)
            .order_by(desc(FinancialAnalysis.created_at))
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    @staticmethod
    async def get_latest_analysis(
        db: AsyncSession, user_id: int
    ) -> Optional[FinancialAnalysis]:
        """Получить последний анализ пользователя"""
        result = await db.execute(
            select(FinancialAnalysis)
            .where(
                and_(
                    FinancialAnalysis.user_id == user_id,
                    FinancialAnalysis.status == AnalysisStatus.COMPLETED,
                )
            )
            .order_by(desc(FinancialAnalysis.analysis_date))
            .limit(1)
        )
        return result.scalars().first()

    @staticmethod
    async def update_analysis_results(
        db: AsyncSession,
        analysis_id: int,
        user_id: int,
        total_income: Decimal,
        total_expenses: Decimal,
        savings_rate: Decimal,
    ) -> Optional[FinancialAnalysis]:
        """Обновить результаты анализа"""
        analysis = await FinancialAnalysisCRUD.get(db, analysis_id, user_id)
        if not analysis:
            return None

        analysis.total_income = total_income
        analysis.total_expenses = total_expenses
        analysis.savings_rate = savings_rate
        analysis.status = AnalysisStatus.COMPLETED

        await db.commit()
        await db.refresh(analysis)
        return analysis

    @staticmethod
    async def update_status(
        db: AsyncSession, analysis_id: int, user_id: int, status: AnalysisStatus
    ) -> Optional[FinancialAnalysis]:
        """Обновить статус анализа"""
        analysis = await FinancialAnalysisCRUD.get(db, analysis_id, user_id)
        if not analysis:
            return None

        analysis.status = status
        await db.commit()
        await db.refresh(analysis)
        return analysis
