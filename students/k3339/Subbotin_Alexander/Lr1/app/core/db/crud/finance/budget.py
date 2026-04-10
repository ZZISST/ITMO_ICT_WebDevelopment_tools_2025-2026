from decimal import Decimal
from typing import List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas.finance import (
    BudgetCreate,
    BudgetUpdate,
    CategoryCreate,
    CategoryUpdate,
)
from app.core.db.models.finance import Budget, Category, CategoryType, TransactionType


class CategoryCRUD:
    """CRUD операции для категорий"""

    @staticmethod
    async def create(
        db: AsyncSession, category_data: CategoryCreate, is_default: bool = False
    ) -> Category:
        """Создать новую категорию"""
        category = Category(
            name=category_data.name,
            description=category_data.description,
            category_type=category_data.category_type,
            color=category_data.color,
            icon=category_data.icon,
            is_default=is_default,
        )
        db.add(category)
        await db.commit()
        await db.refresh(category)
        return category

    @staticmethod
    async def get(db: AsyncSession, category_id: int) -> Optional[Category]:
        """Получить категорию по ID"""
        result = await db.execute(select(Category).where(Category.id == category_id))
        return result.scalars().first()

    @staticmethod
    async def get_by_name(db: AsyncSession, name: str) -> Optional[Category]:
        """Получить категорию по имени"""
        result = await db.execute(select(Category).where(Category.name == name))
        return result.scalars().first()

    @staticmethod
    async def get_or_create_savings_category(db: AsyncSession) -> Category:
        """Получить или создать категорию 'Сбережения / Цели'.

        This guarantees the category exists even if the default-category
        seed has not run yet (e.g. first deployment, or the seed ran
        before this category was added to the list).
        """
        name = "Сбережения / Цели"
        result = await db.execute(select(Category).where(Category.name == name))
        category = result.scalars().first()
        if category:
            return category

        category = Category(
            name=name,
            description="Взносы на финансовые цели и накопления",
            category_type=CategoryType.NEEDS,
            color="#00897B",
            icon="🎯",
            is_default=True,
        )
        db.add(category)
        await db.commit()
        await db.refresh(category)
        return category

    @staticmethod
    async def get_all(
        db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> List[Category]:
        """Получить все категории"""
        result = await db.execute(
            select(Category)
            .offset(skip)
            .limit(limit)
            .order_by(Category.category_type, Category.name)
        )
        return result.scalars().all()

    @staticmethod
    async def get_by_type(
        db: AsyncSession, category_type: CategoryType
    ) -> List[Category]:
        """Получить категории по типу"""
        result = await db.execute(
            select(Category)
            .where(Category.category_type == category_type)
            .order_by(Category.name)
        )
        return result.scalars().all()

    @staticmethod
    async def get_default_categories(db: AsyncSession) -> List[Category]:
        """Получить стандартные категории"""
        result = await db.execute(
            select(Category)
            .where(Category.is_default == True)
            .order_by(Category.category_type, Category.name)
        )
        return result.scalars().all()

    @staticmethod
    async def update(
        db: AsyncSession, category_id: int, category_data: CategoryUpdate
    ) -> Optional[Category]:
        """Обновить категорию"""
        category = await CategoryCRUD.get(db, category_id)
        if not category:
            return None

        for field, value in category_data.dict(exclude_unset=True).items():
            setattr(category, field, value)

        await db.commit()
        await db.refresh(category)
        return category

    @staticmethod
    async def delete(db: AsyncSession, category_id: int) -> bool:
        """Удалить категорию"""
        category = await CategoryCRUD.get(db, category_id)
        if not category or category.is_default:
            return False

        await db.delete(category)
        await db.commit()
        return True

    @staticmethod
    async def init_default_categories(db: AsyncSession) -> List[Category]:
        """Создать стандартные категории"""
        default_categories = [
            # Потребности
            {
                "name": "Продукты",
                "description": "Еда и напитки",
                "category_type": CategoryType.NEEDS,
                "color": "#4CAF50",
                "icon": "🍎",
            },
            {
                "name": "Жилье",
                "description": "Аренда, коммунальные услуги",
                "category_type": CategoryType.NEEDS,
                "color": "#2196F3",
                "icon": "🏠",
            },
            {
                "name": "Транспорт",
                "description": "Общественный транспорт, топливо",
                "category_type": CategoryType.NEEDS,
                "color": "#FF9800",
                "icon": "🚗",
            },
            {
                "name": "Здоровье",
                "description": "Медицина, лекарства",
                "category_type": CategoryType.NEEDS,
                "color": "#F44336",
                "icon": "💊",
            },
            # Желания
            {
                "name": "Развлечения",
                "description": "Кино, рестораны, хобби",
                "category_type": CategoryType.WANTS,
                "color": "#9C27B0",
                "icon": "🎉",
            },
            {
                "name": "Одежда",
                "description": "Одежда и аксессуары",
                "category_type": CategoryType.WANTS,
                "color": "#E91E63",
                "icon": "👕",
            },
            {
                "name": "Электроника",
                "description": "Гаджеты и техника",
                "category_type": CategoryType.WANTS,
                "color": "#607D8B",
                "icon": "📱",
            },
            # Культура
            {
                "name": "Образование",
                "description": "Курсы, книги, обучение",
                "category_type": CategoryType.CULTURE,
                "color": "#3F51B5",
                "icon": "📚",
            },
            {
                "name": "Культурные мероприятия",
                "description": "Театр, музеи, концерты",
                "category_type": CategoryType.CULTURE,
                "color": "#673AB7",
                "icon": "🎭",
            },
            # Неожиданные
            {
                "name": "Экстренные расходы",
                "description": "Непредвиденные траты",
                "category_type": CategoryType.UNEXPECTED,
                "color": "#795548",
                "icon": "⚡",
            },
            {
                "name": "Подарки",
                "description": "Подарки и сюрпризы",
                "category_type": CategoryType.UNEXPECTED,
                "color": "#FF5722",
                "icon": "🎁",
            },
            # Доходы
            {
                "name": "Зарплата",
                "description": "Основной доход от работы",
                "category_type": CategoryType.INCOME,
                "color": "#4CAF50",
                "icon": "💰",
            },
            {
                "name": "Подработка",
                "description": "Дополнительный заработок",
                "category_type": CategoryType.INCOME,
                "color": "#8BC34A",
                "icon": "💼",
            },
            {
                "name": "Подарок",
                "description": "Денежные подарки",
                "category_type": CategoryType.INCOME,
                "color": "#CDDC39",
                "icon": "🎁",
            },
            {
                "name": "Инвестиции",
                "description": "Доход от инвестиций и дивидендов",
                "category_type": CategoryType.INCOME,
                "color": "#009688",
                "icon": "📈",
            },
            {
                "name": "Прочие доходы",
                "description": "Другие источники дохода",
                "category_type": CategoryType.INCOME,
                "color": "#00BCD4",
                "icon": "💵",
            },
            # Сбережения / Цели — синхронизация с добавлением средств в сбережениях и целях
            {
                "name": "Сбережения / Цели",
                "description": "Взносы на финансовые цели и накопления",
                "category_type": CategoryType.NEEDS,
                "color": "#00897B",
                "icon": "🎯",
            },
        ]

        created_categories = []
        # Use no_autoflush to prevent premature flushes during the loop
        # (autoflush on SELECT would try to INSERT pending objects mid-loop)
        with db.no_autoflush:
            for cat_data in default_categories:
                # Проверяем, что категория еще не создана
                existing = await db.execute(
                    select(Category).where(
                        and_(
                            Category.name == cat_data["name"],
                            Category.is_default == True,
                        )
                    )
                )
                if not existing.scalars().first():
                    category = Category(**cat_data, is_default=True)
                    db.add(category)
                    created_categories.append(category)

        await db.commit()
        return created_categories


class BudgetCRUD:
    """CRUD операции для бюджетов"""

    @staticmethod
    async def create(
        db: AsyncSession, user_id: int, budget_data: BudgetCreate
    ) -> Budget:
        """Создать новый бюджет"""
        budget = Budget(
            user_id=user_id,
            category_id=budget_data.category_id,
            amount=budget_data.amount,
            period_start=budget_data.period_start,
            period_end=budget_data.period_end,
        )
        db.add(budget)
        await db.commit()
        await db.refresh(budget, ["category"])
        return budget

    @staticmethod
    async def get(db: AsyncSession, budget_id: int, user_id: int) -> Optional[Budget]:
        """Получить бюджет по ID"""
        result = await db.execute(
            select(Budget)
            .options(selectinload(Budget.category))
            .where(and_(Budget.id == budget_id, Budget.user_id == user_id))
        )
        return result.scalars().first()

    @staticmethod
    async def get_user_budgets(
        db: AsyncSession,
        user_id: int,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Budget]:
        """Получить бюджеты пользователя"""
        query = (
            select(Budget)
            .options(selectinload(Budget.category))
            .where(Budget.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .order_by(Budget.created_at.desc())
        )

        if active_only:
            query = query.where(Budget.is_active == True)

        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_current_budgets(db: AsyncSession, user_id: int) -> List[Budget]:
        """Получить текущие активные бюджеты пользователя"""
        from datetime import datetime

        now = datetime.utcnow()

        result = await db.execute(
            select(Budget)
            .options(selectinload(Budget.category))
            .where(
                and_(
                    Budget.user_id == user_id,
                    Budget.is_active == True,
                    Budget.period_start <= now,
                    Budget.period_end >= now,
                )
            )
            .order_by(Budget.category_id)
        )
        return result.scalars().all()

    @staticmethod
    async def update(
        db: AsyncSession, budget_id: int, user_id: int, budget_data: BudgetUpdate
    ) -> Optional[Budget]:
        """Обновить бюджет"""
        budget = await BudgetCRUD.get(db, budget_id, user_id)
        if not budget:
            return None

        for field, value in budget_data.dict(exclude_unset=True).items():
            setattr(budget, field, value)

        await db.commit()
        await db.refresh(budget, ["category"])
        return budget

    @staticmethod
    async def delete(db: AsyncSession, budget_id: int, user_id: int) -> bool:
        """Удалить бюджет"""
        budget = await BudgetCRUD.get(db, budget_id, user_id)
        if not budget:
            return False

        await db.delete(budget)
        await db.commit()
        return True

    @staticmethod
    async def get_budget_summary(
        db: AsyncSession, user_id: int, category_id: Optional[int] = None
    ) -> dict:
        """Получить сводку по бюджетам"""
        from datetime import datetime

        now = datetime.utcnow()

        query = select(
            func.sum(Budget.amount).label("total_budget"),
            func.count(Budget.id).label("budget_count"),
        ).where(
            and_(
                Budget.user_id == user_id,
                Budget.is_active == True,
                Budget.period_start <= now,
                Budget.period_end >= now,
            )
        )

        if category_id:
            query = query.where(Budget.category_id == category_id)

        result = await db.execute(query)
        summary = result.first()

        return {
            "total_budget": summary.total_budget or Decimal("0"),
            "budget_count": summary.budget_count or 0,
        }
