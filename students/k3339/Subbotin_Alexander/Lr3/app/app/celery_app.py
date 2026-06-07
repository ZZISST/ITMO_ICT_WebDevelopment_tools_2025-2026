from celery import Celery
from celery.schedules import crontab

from app.core.settings.config import settings

celery = Celery(
    "mavrodi_wall",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks"],
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Moscow",
    enable_utc=True,
    task_track_started=True,
    result_expires=3600,
)

celery.conf.beat_schedule = {
    "periodic-parse-finance-articles": {
        "task": "app.tasks.periodic_parse",
        "schedule": crontab(hour="*/6"),
    },
}
