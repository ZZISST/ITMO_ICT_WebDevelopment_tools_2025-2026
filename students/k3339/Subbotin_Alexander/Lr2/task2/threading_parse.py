import threading
import time

import requests
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text

from task2.config import CATEGORY_TYPE_MAP, HEADERS, SYNC_DATABASE_URL, URLS

engine = create_engine(SYNC_DATABASE_URL)

INSERT_SQL = text("""
    INSERT INTO categories (name, description, category_type, is_default, created_at)
    VALUES (:name, :description, :category_type, false, NOW())
""")


def parse_and_save(url: str) -> None:
    response = requests.get(url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(response.text, "html.parser")

    h1_span = soup.select_one("h1 .mw-page-title-main") or soup.find("h1")
    title = h1_span.get_text(strip=True) if h1_span else "Unknown"

    first_p = soup.select_one("#mw-content-text .mw-parser-output > p:not(.mw-empty-elt)")
    description = first_p.get_text(strip=True)[:500] if first_p else ""

    category_type = CATEGORY_TYPE_MAP.get(title, "needs")

    with engine.connect() as conn:
        conn.execute(INSERT_SQL, {
            "name": title,
            "description": description,
            "category_type": category_type,
        })
        conn.commit()

    print(f"  [threading] Сохранено: {title}")


def main() -> None:
    print(f"=== Threading: парсинг {len(URLS)} страниц ===")

    threads: list[threading.Thread] = []
    start_time = time.time()

    for url in URLS:
        t = threading.Thread(target=parse_and_save, args=(url,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    elapsed = time.time() - start_time
    print(f"Время: {elapsed:.4f} сек")


if __name__ == "__main__":
    main()
