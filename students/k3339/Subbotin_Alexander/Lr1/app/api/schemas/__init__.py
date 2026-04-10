"""
Схемы для API
"""

# Импорт пользовательских схем
from .user import (
    UserBase,
    UserCreate,
    UserLogin,
    UserResponse,
    Token,
    TokenData,
    UserUpdate,
    PasswordChange,
)
# flake8: noqa

from .finance import (
    AnalysisRequest,
    AnalysisResponse,
    AnalysisStatus,
    BudgetBase,
    BudgetCreate,
    BudgetResponse,
    BudgetUpdate,
    CategoryBase,
    CategoryCreate,
    CategoryResponse,
    CategoryType,
    CategoryUpdate,
    FinancialAnalysisBase,
    FinancialAnalysisCreate,
    FinancialAnalysisResponse,
    FinancialGoalBase,
    FinancialGoalCreate,
    FinancialGoalResponse,
    FinancialGoalUpdate,
    TransactionBase,
    TransactionCreate,
    TransactionResponse,
    TransactionType,
    TransactionUpdate,
)

from .user import (
    PasswordChange,
    Token,
    TokenData,
    UserBase,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)

__all__ = [
    "CategoryType",
    "TransactionType",
    "AnalysisStatus",
    "CategoryBase",
    "CategoryCreate",
    "CategoryUpdate",
    "CategoryResponse",
    "BudgetBase",
    "BudgetCreate",
    "BudgetUpdate",
    "BudgetResponse",
    "TransactionBase",
    "TransactionCreate",
    "TransactionUpdate",
    "TransactionResponse",
    "FinancialGoalBase",
    "FinancialGoalCreate",
    "FinancialGoalUpdate",
    "FinancialGoalResponse",
    "FinancialAnalysisBase",
    "FinancialAnalysisCreate",
    "FinancialAnalysisResponse",
    "AnalysisRequest",
    "AnalysisResponse",
    "Token",
    "TokenData",
    "UserBase",
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "UserUpdate",
    "PasswordChange",
]
