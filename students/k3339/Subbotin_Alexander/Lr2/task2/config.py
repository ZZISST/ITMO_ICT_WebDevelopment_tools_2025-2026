import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "mavrodi_pass")
DB_SERVER = os.getenv("DB_SERVER", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5433")
POSTGRES_DB = os.getenv("POSTGRES_DB", "mavrodi_db")

SYNC_DATABASE_URL = (
    f"postgresql+psycopg://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{DB_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}"
)
ASYNC_DATABASE_URL = (
    f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{DB_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

URLS = [
    "https://en.wikipedia.org/wiki/Expense",
    "https://en.wikipedia.org/wiki/Income",
    "https://en.wikipedia.org/wiki/Budget",
    "https://en.wikipedia.org/wiki/Saving",
    "https://en.wikipedia.org/wiki/Investment",
    "https://en.wikipedia.org/wiki/Tax",
    "https://en.wikipedia.org/wiki/Insurance",
    "https://en.wikipedia.org/wiki/Mortgage_loan",
    "https://en.wikipedia.org/wiki/Credit_card",
    "https://en.wikipedia.org/wiki/Salary",
    "https://en.wikipedia.org/wiki/Dividend",
    "https://en.wikipedia.org/wiki/Rent",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) LabWork/2.0",
}

CATEGORY_TYPE_MAP: dict[str, str] = {
    "Expense": "needs",
    "Income": "income",
    "Budget": "needs",
    "Saving": "wants",
    "Investment": "wants",
    "Tax": "needs",
    "Insurance": "needs",
    "Mortgage": "needs",
    "Credit card": "needs",
    "Salary": "income",
    "Dividend": "income",
    "Rent": "needs",
}
