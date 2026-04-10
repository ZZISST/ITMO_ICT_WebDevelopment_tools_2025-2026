from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, computed_field, validator


class AnalysisStatus(str, Enum):
    """Статусы анализа"""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class CategoryType(str, Enum):
    """типы категорий"""

    NEEDS = "needs"
    WANTS = "wants"
    CULTURE = "culture"
    UNEXPECTED = "unexpected"
    INCOME = "income"


class TransactionType(str, Enum):
    """Типы транзакций"""

    EXPENSE = "expense"
    INCOME = "income"


# Category Schemas
class CategoryBase(BaseModel):
    """Базовая схема категории"""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    category_type: CategoryType
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = Field(None, max_length=50)


class CategoryCreate(CategoryBase):
    """Схема создания категории"""

    pass


class CategoryUpdate(BaseModel):
    """Схема обновления категории"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = Field(None, max_length=50)


class CategoryResponse(CategoryBase):
    """Схема ответа категории"""

    id: int
    is_default: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Budget Schemas
class BudgetBase(BaseModel):
    """Базовая схема бюджета"""

    category_id: int = Field(..., gt=0)
    amount: Decimal = Field(..., ge=0, decimal_places=2)
    period_start: datetime
    period_end: datetime

    @validator("period_end")
    def validate_period_end(cls, v, values):
        if "period_start" in values and v <= values["period_start"]:
            raise ValueError("Дата окончания должна быть позже даты начала")
        return v


class BudgetCreate(BudgetBase):
    """Схема создания бюджета"""

    pass


class BudgetUpdate(BaseModel):
    """Схема обновления бюджета"""

    amount: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    is_active: Optional[bool] = None


class BudgetResponse(BudgetBase):
    """Схема ответа бюджета"""

    id: int
    user_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    category: CategoryResponse
    spent: Decimal = Decimal("0")
    remaining: Decimal = Decimal("0")

    class Config:
        from_attributes = True


# Transaction Schemas
class TransactionBase(BaseModel):
    """Базовая схема транзакции"""

    category_id: int = Field(..., gt=0)
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    transaction_type: TransactionType
    description: str = Field(..., min_length=1, max_length=500)
    notes: Optional[str] = Field(None, max_length=1000)
    transaction_date: datetime
    is_planned: bool = False
    is_recurring: bool = False


class TransactionCreate(TransactionBase):
    """Схема создания транзакции"""

    pass


class TransactionUpdate(BaseModel):
    """Схема обновления транзакции"""

    category_id: Optional[int] = Field(None, gt=0)
    amount: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    transaction_type: Optional[TransactionType] = None
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    notes: Optional[str] = Field(None, max_length=1000)
    transaction_date: Optional[datetime] = None
    is_planned: Optional[bool] = None
    is_recurring: Optional[bool] = None


class TransactionResponse(TransactionBase):
    """Схема ответа транзакции"""

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    category: CategoryResponse

    class Config:
        from_attributes = True


# Financial Goal Schemas
class FinancialGoalBase(BaseModel):
    """Базовая схема финансовой цели"""

    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    target_amount: Decimal = Field(..., gt=0, decimal_places=2)
    target_date: datetime
    priority: int = Field(1, ge=1, le=5)

    @validator("target_date", pre=True)
    def validate_target_date(cls, v):
        if isinstance(v, str):
            # Handle date-only strings like "2026-12-31"
            if "T" not in v and len(v) == 10:
                v = datetime.strptime(v, "%Y-%m-%d").replace(
                    hour=23, minute=59, second=59
                )
            else:
                # Strip trailing Z and parse ISO format
                v = datetime.fromisoformat(v.replace("Z", "+00:00"))
        # Strip timezone info to avoid naive/aware comparison errors
        if hasattr(v, "tzinfo") and v.tzinfo is not None:
            v = v.replace(tzinfo=None)
        if v.date() < datetime.now().date():
            raise ValueError("Дата цели должна быть в будущем")
        return v

class FinancialGoalCreate(FinancialGoalBase):
    """Схема создания финансовой цели"""

    pass

class FinancialGoalUpdate(BaseModel):
    """Схема обновления финансовой цели"""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    target_amount: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    current_amount: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    target_date: Optional[datetime] = None
    is_achieved: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=1, le=5)


class FinancialGoalResponse(FinancialGoalBase):
    """Схема ответа финансовой цели"""

    id: int
    user_id: int
    current_amount: Decimal
    is_achieved: bool
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def progress_percentage(self) -> float:
        """Процент выполнения цели"""
        if self.target_amount <= 0:
            return 0.0
        return min(float(self.current_amount / self.target_amount * 100), 100.0)

    class Config:
        from_attributes = True

# Financial Analysis Schemas
class FinancialAnalysisBase(BaseModel):
    """Базовая схема финансового анализа"""

    period_start: datetime
    period_end: datetime

    @validator("period_end")
    def validate_period_end(cls, v, values):
        if "period_start" in values and v <= values["period_start"]:
            raise ValueError("Дата окончания должна быть позже даты начала")
        return v

class FinancialAnalysisCreate(FinancialAnalysisBase):
    """Схема создания финансового анализа"""

    pass

class FinancialAnalysisResponse(FinancialAnalysisBase):
    """Схема ответа финансового анализа"""

    id: int
    user_id: int
    analysis_date: datetime
    total_income: Decimal
    total_expenses: Decimal
    savings_rate: Decimal
    status: AnalysisStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PlannedVsActualSummary(BaseModel):
    """сводка план/факт по транзакциям"""

    period: str
    total_planned: Decimal
    total_actual: Decimal
    variance: Decimal
    transactions: List[TransactionResponse]


