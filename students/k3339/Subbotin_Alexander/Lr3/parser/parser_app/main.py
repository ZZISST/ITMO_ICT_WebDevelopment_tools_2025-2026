import os

import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, Query
from sqlalchemy import create_engine, text

app = FastAPI(title="Mavrodi Wall Parser Service")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) MavrodiWall/3.0",
}

CATEGORY_TYPE_MAP: dict[str, str] = {
    "Expense": "NEEDS",
    "Income": "INCOME",
    "Budget": "NEEDS",
    "Saving": "WANTS",
    "Investment": "WANTS",
    "Tax": "NEEDS",
    "Insurance": "NEEDS",
    "Mortgage": "NEEDS",
    "Credit card": "NEEDS",
    "Salary": "INCOME",
    "Dividend": "INCOME",
    "Rent": "NEEDS",
}

INSERT_SQL = text("""
    INSERT INTO categories (name, description, category_type, is_default, created_at)
    VALUES (:name, :description, :category_type, false, NOW())
    RETURNING id, name, category_type
""")


def get_db_url() -> str:
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "mavrodi_pass")
    host = os.getenv("DB_SERVER", "db")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "mavrodi_db")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"


@app.post("/parse")
def parse(url: str = Query(..., description="URL to parse")):
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch URL: {e}")

    soup = BeautifulSoup(response.text, "html.parser")

    h1_span = soup.select_one("h1 .mw-page-title-main") or soup.find("h1")
    title = h1_span.get_text(strip=True) if h1_span else "Unknown"

    first_p = soup.select_one(
        "#mw-content-text .mw-parser-output > p:not(.mw-empty-elt)"
    )
    description = first_p.get_text(strip=True)[:500] if first_p else ""

    category_type = CATEGORY_TYPE_MAP.get(title, "NEEDS")

    engine = create_engine(get_db_url())
    try:
        with engine.connect() as conn:
            row = conn.execute(
                INSERT_SQL,
                {
                    "name": title,
                    "description": description,
                    "category_type": category_type,
                },
            ).fetchone()
            conn.commit()
    finally:
        engine.dispose()

    return {
        "message": "Parsing completed",
        "url": url,
        "category": {
            "id": row[0],
            "name": row[1],
            "category_type": row[2],
        },
    }


@app.get("/health")
def health():
    return {"status": "healthy"}
