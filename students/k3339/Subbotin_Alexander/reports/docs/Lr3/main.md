# Лабораторная работа 3. Docker, источники данных и очереди

## Цель

Научиться упаковывать FastAPI приложение в Docker, интегрировать парсер данных с базой данных и вызывать парсер через API и очередь задач (Celery + Redis).

---

## Стек технологий

| Компонент | Технология |
|---|---|
| Основное приложение | FastAPI (из Лабораторной работы 1) |
| Парсер-сервис | FastAPI + `requests` + `BeautifulSoup4` |
| Очередь задач | Celery 5 |
| Брокер / Backend | Redis 7 |
| ORM | SQLAlchemy 2.0 (async + sync) |
| База данных | PostgreSQL 17 |
| Контейнеризация | Docker + Docker Compose |
| Пакетный менеджер | uv |

---

## Архитектура

```
┌──────────────┐     HTTP      ┌──────────────┐
│   Client     │────────────►  │   FastAPI     │
│              │◄────────────  │   (app)       │
└──────────────┘               │   :8000       │
                               └──────┬───────┘
                          ┌───────────┼───────────┐
                    sync  │     async │           │
                    HTTP  │    Celery │           │
                          ▼           ▼           │
                   ┌────────────┐ ┌────────┐     │
                   │  Parser    │ │ Redis  │     │
                   │  Service   │ │ :6379  │     │
                   │  :8001     │ └───┬────┘     │
                   └─────┬──────┘     │          │
                         │      ┌─────▼──────┐   │
                         │      │  Celery    │   │
                         │      │  Worker    │───┘
                         │      └─────┬──────┘
                         │            │ HTTP
                         │            ▼
                         │      ┌────────────┐
                         └─────►│ PostgreSQL │
                                │ :5432      │
                                └────────────┘
```

**Потоки данных:**

- **Синхронный**: Client → FastAPI → Parser Service → PostgreSQL → Client
- **Асинхронный**: Client → FastAPI → Redis (задача) → Celery Worker → Parser Service → PostgreSQL. Клиент получает `task_id` и опрашивает результат.
- **Периодический**: Celery Beat → Redis → Celery Worker → Parser Service → PostgreSQL (по расписанию каждые 6 часов)

---

## Структура проекта

```
Lr3/
├── docker-compose.yml          # Оркестрация всех сервисов
├── .env                        # Переменные окружения
├── app/                        # Основное FastAPI приложение
│   ├── dockerfile
│   ├── docker-entrypoint.sh
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/                # Миграции БД
│   └── app/
│       ├── main.py             # Точка входа FastAPI
│       ├── celery_app.py       # Конфигурация Celery
│       ├── tasks.py            # Celery-задачи
│       └── api/routers/
│           ├── auth.py
│           ├── budget.py
│           ├── transactions.py
│           ├── analysis.py
│           └── parsing.py      # Эндпоинты парсинга
└── parser/                     # Сервис парсера
    ├── dockerfile
    ├── pyproject.toml
    └── parser_app/
        └── main.py             # FastAPI с /parse эндпоинтом
```

---

## Подзадача 1. Docker-упаковка

### Dockerfile основного приложения

```dockerfile
FROM python:3.14-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    postgresql-client gcc g++ python3-dev curl \
 && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
WORKDIR /app

ENV UV_LINK_MODE=copy
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml .
RUN uv sync --no-dev
COPY . .

RUN chmod +x /app/docker-entrypoint.sh
ENTRYPOINT ["/app/docker-entrypoint.sh"]
```

!!! info "uv вместо pip"
    Используется `uv` для установки зависимостей — значительно быстрее pip. Multi-stage подход: сначала копируем `pyproject.toml` и устанавливаем зависимости (кэшируются Docker), затем копируем исходный код.

### Dockerfile парсер-сервиса

```dockerfile
FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /parser
COPY pyproject.toml .
RUN uv sync --no-dev
COPY . .

CMD ["uvicorn", "parser_app.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

### Docker Compose

6 сервисов в единой сети:

| Сервис | Образ / Билд | Порт | Назначение |
|---|---|---|---|
| `db` | `postgres:17` | 5433:5432 | База данных |
| `redis` | `redis:7-alpine` | 6379 | Брокер Celery |
| `app` | `./app` | 8000 | Основное API |
| `parser` | `./parser` | 8001 | Сервис парсинга |
| `celery_worker` | `./app` | — | Обработчик задач |
| `celery_beat` | `./app` | — | Планировщик задач |

```yaml
services:
  db:
    image: postgres:17
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]

  app:
    build: ./app
    depends_on:
      db: { condition: service_healthy }
      redis: { condition: service_healthy }

  parser:
    build: ./parser
    depends_on:
      db: { condition: service_healthy }

  celery_worker:
    build: ./app
    entrypoint: []
    command: celery -A app.celery_app.celery worker --loglevel=info
    depends_on:
      db: { condition: service_healthy }
      redis: { condition: service_healthy }
      parser: { condition: service_started }

  celery_beat:
    build: ./app
    entrypoint: []
    command: celery -A app.celery_app.celery beat --loglevel=info
    depends_on:
      redis: { condition: service_healthy }
```

!!! note "Healthcheck-зависимости"
    `app` и `celery_worker` запускаются только после того, как `db` и `redis` пройдут healthcheck. Это гарантирует готовность инфраструктуры.

---

## Подзадача 2. Вызов парсера из FastAPI

### Парсер-сервис (`parser/parser_app/main.py`)

Отдельное FastAPI приложение с эндпоинтом `/parse`:

```python
@app.post("/parse")
def parse(url: str = Query(...)):
    response = requests.get(url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(response.text, "html.parser")

    h1_span = soup.select_one("h1 .mw-page-title-main") or soup.find("h1")
    title = h1_span.get_text(strip=True) if h1_span else "Unknown"

    first_p = soup.select_one(
        "#mw-content-text .mw-parser-output > p:not(.mw-empty-elt)"
    )
    description = first_p.get_text(strip=True)[:500] if first_p else ""

    category_type = CATEGORY_TYPE_MAP.get(title, "NEEDS")

    engine = create_engine(get_db_url())
    with engine.connect() as conn:
        row = conn.execute(INSERT_SQL, {...}).fetchone()
        conn.commit()

    return {"message": "Parsing completed", "category": {...}}
```

### Эндпоинт синхронного вызова (`app/api/routers/parsing.py`)

Основное приложение вызывает парсер-сервис по HTTP через `httpx`:

```python
@router.post("/parsing/sync")
async def parse_sync(url: str = Query(...)):
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{settings.PARSER_SERVICE_URL}/parse",
            params={"url": url},
        )
        response.raise_for_status()
        return response.json()
```

### Пример запроса и ответа

**Запрос:**
```
POST /parsing/sync?url=https://en.wikipedia.org/wiki/Expense
```

**Ответ:**
```json
{
    "message": "Parsing completed",
    "url": "https://en.wikipedia.org/wiki/Expense",
    "category": {
        "id": 18,
        "name": "Expense",
        "category_type": "NEEDS"
    }
}
```

---

## Подзадача 3. Celery + Redis

### Конфигурация Celery (`app/celery_app.py`)

```python
from celery import Celery
from celery.schedules import crontab

celery = Celery(
    "mavrodi_wall",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks"],
)

celery.conf.beat_schedule = {
    "periodic-parse-finance-articles": {
        "task": "app.tasks.periodic_parse",
        "schedule": crontab(hour="*/6"),
    },
}
```

### Celery-задачи (`app/tasks.py`)

```python
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
```

### Эндпоинты асинхронного вызова

```python
@router.post("/parsing/async")
async def parse_async(url: str = Query(...)):
    task = parse_url.delay(url)
    return {"task_id": task.id, "status": "queued"}

@router.get("/parsing/result/{task_id}")
async def get_parse_result(task_id: str):
    result = parse_url.AsyncResult(task_id)
    response = {"task_id": task_id, "status": result.status}
    if result.ready():
        response["result"] = result.get()
    return response
```

### Пример работы

**1. Постановка задачи в очередь:**
```
POST /parsing/async?url=https://en.wikipedia.org/wiki/Income
```
```json
{
    "task_id": "08ca9484-ee5c-48e6-b2ad-8d1c52db9b81",
    "status": "queued"
}
```

**2. Получение результата:**
```
GET /parsing/result/08ca9484-ee5c-48e6-b2ad-8d1c52db9b81
```
```json
{
    "task_id": "08ca9484-ee5c-48e6-b2ad-8d1c52db9b81",
    "status": "SUCCESS",
    "result": {
        "message": "Parsing completed",
        "url": "https://en.wikipedia.org/wiki/Income",
        "category": {
            "id": 19,
            "name": "Income",
            "category_type": "INCOME"
        }
    }
}
```

### Периодические задачи (Celery Beat)

Celery Beat запускает `periodic_parse` каждые 6 часов. Задача ставит в очередь парсинг 6 финансовых статей Wikipedia (Expense, Income, Budget, Saving, Investment, Tax), пополняя таблицу `categories` актуальными данными.

---

## Запуск

```bash
cd Lr3

# Запуск всех сервисов
docker compose up -d --build

# Проверка статуса
docker compose ps

# Просмотр логов
docker compose logs -f celery_worker

# Остановка
docker compose down
```

---

## Вывод

В ходе лабораторной работы реализована микросервисная архитектура из 6 контейнеров:

- **FastAPI приложение** (из ЛР1) расширено эндпоинтами для синхронного и асинхронного парсинга
- **Парсер-сервис** — отдельное FastAPI приложение для парсинга веб-страниц с сохранением в БД
- **Celery Worker** обрабатывает задачи парсинга в фоне, не блокируя основной API
- **Celery Beat** запускает периодический парсинг по расписанию
- **Redis** выступает брокером и хранилищем результатов задач
- **PostgreSQL** хранит все данные приложения

Docker Compose обеспечивает оркестрацию с healthcheck-зависимостями, гарантируя корректный порядок запуска сервисов.
