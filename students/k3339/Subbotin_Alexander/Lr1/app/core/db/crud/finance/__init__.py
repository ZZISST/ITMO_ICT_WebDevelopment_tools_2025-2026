"""
CRUD операции для финансовых данных
"""

from .budget import CategoryCRUD, BudgetCRUD
from .transaction import TransactionCRUD
from .analysis import (
    FinancialGoalCRUD, 
    FinancialAnalysisCRUD,
)

__all__ = [
    "CategoryCRUD",
    "BudgetCRUD", 
    "TransactionCRUD",
    "FinancialGoalCRUD",
    "FinancialAnalysisCRUD",
]