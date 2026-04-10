import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.finance import FinancialAnalysisCreate
from app.core.db.crud.finance import (
    BudgetCRUD,
    CategoryCRUD,
    FinancialAnalysisCRUD,
    FinancialGoalCRUD,
    TransactionCRUD,
)
from app.core.db.models.finance import CategoryType

logger = logging.getLogger(__name__)


class FinancialAnalysisService:
    """сервис финансового анализа."""

    @staticmethod
    async def perform_comprehensive_analysis(
        db: AsyncSession, user_id: int, period_days: int = 30
    ) -> Dict[str, Any]:
        """выполнить комплексный анализ."""

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=period_days)

        # Базовая статистика
        stats = await TransactionCRUD.get_transaction_stats(
            db, user_id, start_date, end_date
        )

        # Анализ целей
        goals = await FinancialGoalCRUD.get_user_goals(db, user_id, active_only=True)
        goals_data = [
            {
                "title": goal.title,
                "target_amount": goal.target_amount,
                "current_amount": goal.current_amount,
                "target_date": goal.target_date,
            }
            for goal in goals
        ]
        goals_summary = await FinancialGoalCRUD.get_goals_summary(db, user_id)

        category_type_totals: Dict[str, Decimal] = {
            ct.value: Decimal("0") for ct in CategoryType
        }
        total_expenses = stats.get("total_expenses", Decimal("0"))

        for cat_stat in stats.get("category_breakdown", []):
            category = await CategoryCRUD.get(db, cat_stat["category_id"])
            if category and category.category_type:
                ct_value = (
                    category.category_type.value
                    if hasattr(category.category_type, "value")
                    else str(category.category_type)
                )
                if ct_value in category_type_totals:
                    category_type_totals[ct_value] += cat_stat["total"]

        category_type_breakdown = {}
        for category_type in CategoryType:
            spent = category_type_totals[category_type.value]
            category_type_breakdown[category_type.value] = {
                "total_spent": spent,
                "percentage_of_total": float(spent / total_expenses * 100)
                if total_expenses > 0
                else 0.0,
            }

        try:
            analysis_create = FinancialAnalysisCreate(
                period_start=start_date,
                period_end=end_date,
            )
            analysis_record = await FinancialAnalysisCRUD.create(
                db, user_id, analysis_create
            )
            await FinancialAnalysisCRUD.update_analysis_results(
                db,
                analysis_id=analysis_record.id,
                user_id=user_id,
                total_income=stats.get("total_income", Decimal("0")),
                total_expenses=total_expenses,
                savings_rate=Decimal(str(stats.get("savings_rate", 0))),
            )
        except Exception as e:
            logger.warning(f"Не удалось сохранить результат анализа: {e}")

        result = {
            "period": {"start": start_date, "end": end_date, "days": period_days},
            "basic_metrics": stats,
            "goals_analysis": goals_summary,
            "goals_details": goals_data,
            "category_type_breakdown": category_type_breakdown,
            "recommendations": {
                "needs_attention": [],
                "positive_trends": [],
                "action_items": [],
            },
        }

        return result

    @staticmethod
    async def generate_monthly_report(db: AsyncSession, user_id: int) -> Dict[str, Any]:
        """сгенерировать месячный отчет"""

        now = datetime.utcnow()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Получаем данные за месяц
        analysis = await FinancialAnalysisService.perform_comprehensive_analysis(
            db, user_id, (now - start_of_month).days
        )

        # Прогресс по целям
        goals = await FinancialGoalCRUD.get_user_goals(db, user_id, active_only=True)

        return {
            "report_type": "monthly",
            "generated_at": now,
            "period": {"start": start_of_month, "end": now},
            "financial_analysis": analysis,
            "goals_progress": [
                {
                    "title": goal.title,
                    "progress_percentage": float(
                        goal.current_amount / goal.target_amount * 100
                    )
                    if goal.target_amount > 0
                    else 0,
                    "is_achieved": goal.is_achieved,
                }
                for goal in goals
            ],
        }


class BudgetOptimizationService:
    """сервис оптимизации бюджета"""

    @staticmethod
    async def suggest_budget_adjustments(
        db: AsyncSession, user_id: int
    ) -> Dict[str, Any]:
        """предложить корректировки бюджета"""

        # Получаем текущие бюджеты
        current_budgets = await BudgetCRUD.get_current_budgets(db, user_id)

        # Получаем статистику трат за последние 3 месяца
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=90)

        stats = await TransactionCRUD.get_transaction_stats(
            db, user_id, start_date, end_date
        )

        suggestions = []

        # Анализируем каждый бюджет
        for budget in current_budgets:
            # Находим фактические траты по этой категории
            category_spent = Decimal("0")
            for cat_stat in stats.get("category_breakdown", []):
                if cat_stat["category_id"] == budget.category_id:
                    category_spent = cat_stat["total"] / 3  # Среднемесячные траты
                    break

            utilization = (
                float(category_spent / budget.amount * 100) if budget.amount > 0 else 0
            )

            suggestion = {
                "category": budget.category.name,
                "current_budget": budget.amount,
                "avg_monthly_spending": category_spent,
                "utilization_percentage": utilization,
                "status": "optimal",
            }

            if utilization > 120:
                suggestion["status"] = "increase_needed"
                suggestion["suggested_amount"] = category_spent * Decimal(
                    "1.1"
                )  # +10% буфер
                suggestion["reason"] = "Регулярное превышение бюджета"
            elif utilization < 50:
                suggestion["status"] = "decrease_possible"
                suggestion["suggested_amount"] = category_spent * Decimal(
                    "1.2"
                )  # +20% буфер
                suggestion["reason"] = "Недоиспользование бюджета"

            suggestions.append(suggestion)

        return {
            "analysis_period": {"start": start_date, "end": end_date},
            "suggestions": suggestions,
            "summary": {
                "total_current_budget": sum(b.amount for b in current_budgets),
                "categories_analyzed": len(suggestions),
                "needs_increase": len(
                    [s for s in suggestions if s["status"] == "increase_needed"]
                ),
                "can_decrease": len(
                    [s for s in suggestions if s["status"] == "decrease_possible"]
                ),
            },
        }


class NotificationService:
    """сервис уведомлений"""

    @staticmethod
    async def check_budget_alerts(
        db: AsyncSession, user_id: int
    ) -> List[Dict[str, Any]]:
        """проверить превышения бюджета."""

        alerts = []
        current_budgets = await BudgetCRUD.get_current_budgets(db, user_id)

        # Получаем траты за текущий месяц
        now = datetime.utcnow()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        stats = await TransactionCRUD.get_transaction_stats(
            db, user_id, start_of_month, now
        )

        for budget in current_budgets:
            # Находим траты по этой категории
            category_spent = Decimal("0")
            for cat_stat in stats.get("category_breakdown", []):
                if cat_stat["category_id"] == budget.category_id:
                    category_spent = cat_stat["total"]
                    break

            utilization = (
                float(category_spent / budget.amount * 100) if budget.amount > 0 else 0
            )

            if utilization >= 90:
                alert_type = "critical" if utilization >= 100 else "warning"
                alerts.append(
                    {
                        "type": alert_type,
                        "category": budget.category.name,
                        "budget_amount": budget.amount,
                        "spent_amount": category_spent,
                        "utilization": utilization,
                        "message": f"Бюджет категории '{budget.category.name}' использован на {utilization:.1f}%",
                    }
                )

        return alerts

    @staticmethod
    async def check_goal_milestones(
        db: AsyncSession, user_id: int
    ) -> List[Dict[str, Any]]:
        """Проверить достижение промежуточных целей"""

        notifications = []
        goals = await FinancialGoalCRUD.get_user_goals(db, user_id, active_only=True)

        for goal in goals:
            progress = (
                float(goal.current_amount / goal.target_amount * 100)
                if goal.target_amount > 0
                else 0
            )

            # Уведомления о промежуточных достижениях
            milestones = [25, 50, 75, 90]
            for milestone in milestones:
                if progress >= milestone:
                    notifications.append(
                        {
                            "type": "milestone",
                            "goal_title": goal.title,
                            "milestone": milestone,
                            "current_progress": progress,
                            "message": f"Достигнуто {milestone}% от цели '{goal.title}'",
                        }
                    )

        return notifications
