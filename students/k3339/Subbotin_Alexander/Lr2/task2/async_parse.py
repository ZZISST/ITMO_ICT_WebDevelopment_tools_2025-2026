import asyncio
import time

import aiohttp
from bs4 import BeautifulSoup
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from task2.config import ASYNC_DATABASE_URL, CATEGORY_TYPE_MAP, HEADERS, URLS

engine = create_async_engine(ASYNC_DATABASE_URL)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

INSERT_SQL = text("""
    INSERT INTO categories (name, description, category_type, is_default, created_at)
    VALUES (:name, :description, :category_type, false, NOW())
""")


async def parse_and_save(session: aiohttp.ClientSession, url: str) -> None:
    async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=15)) as response:
        html = await response.text()

    soup = BeautifulSoup(html, "html.parser")

    h1_span = soup.select_one("h1 .mw-page-title-main") or soup.find("h1")
    title = h1_span.get_text(strip=True) if h1_span else "Unknown"

    first_p = soup.select_one("#mw-content-text .mw-parser-output > p:not(.mw-empty-elt)")
    description = first_p.get_text(strip=True)[:500] if first_p else ""

    category_type = CATEGORY_TYPE_MAP.get(title, "needs")

    async with async_session() as db:
        await db.execute(INSERT_SQL, {
            "name": title,
            "description": description,
            "category_type": category_type,
        })
        await db.commit()

    print(f"  [async] Сохранено: {title}")


async def main() -> None:
    print(f"=== Async: парсинг {len(URLS)} страниц ===")

    start_time = time.time()

    async with aiohttp.ClientSession() as session:
        tasks = [parse_and_save(session, url) for url in URLS]
        await asyncio.gather(*tasks)

    await engine.dispose()

    elapsed = time.time() - start_time
    print(f"Время: {elapsed:.4f} сек")


if __name__ == "__main__":
    asyncio.run(main())
