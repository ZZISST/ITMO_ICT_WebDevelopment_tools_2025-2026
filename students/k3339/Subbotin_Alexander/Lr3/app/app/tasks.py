import logging

import httpx

from app.celery_app import celery
from app.core.settings.config import settings

logger = logging.getLogger(__name__)

FINANCE_URLS = [
    "https://en.wikipedia.org/wiki/Expense",
    "https://en.wikipedia.org/wiki/Income",
    "https://en.wikipedia.org/wiki/Budget",
    "https://en.wikipedia.org/wiki/Saving",
    "https://en.wikipedia.org/wiki/Investment",
    "https://en.wikipedia.org/wiki/Tax",
]


@celery.task(bind=True, name="app.tasks.parse_url")
def parse_url(self, url: str):
    with httpx.Client(timeout=30) as client:
        response = client.post(
            f"{settings.PARSER_SERVICE_URL}/parse",
            params={"url": url},
        )
        response.raise_for_status()
        return response.json()


@celery.task(name="app.tasks.periodic_parse")
def periodic_parse():
    results = []
    for url in FINANCE_URLS:
        result = parse_url.delay(url)
        results.append(result.id)
    return {"queued_tasks": results}
