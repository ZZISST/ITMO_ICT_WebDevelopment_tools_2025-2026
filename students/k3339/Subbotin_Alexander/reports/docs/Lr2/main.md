# Лабораторная работа 2. Потоки. Процессы. Асинхронность.

## Цель

Понять отличия между потоками и процессами, изучить асинхронность в Python. Сравнить подходы `threading`, `multiprocessing` и `asyncio` на CPU-bound и I/O-bound задачах с замером времени выполнения.

---

## Стек технологий

| Компонент | Технология |
|---|---|
| Язык | Python 3.14 |
| Пакетный менеджер | uv |
| Потоки | `threading` |
| Процессы | `multiprocessing` |
| Асинхронность | `asyncio`, `aiohttp` |
| HTTP-клиент (sync) | `requests` |
| Парсинг HTML | `BeautifulSoup4` |
| ORM | SQLAlchemy 2.0 (sync + async) |
| БД-драйверы | `psycopg` (sync), `asyncpg` (async) |
| База данных | PostgreSQL 17 (из Лабораторной работы 1) |

---

## Структура проекта

```
Lr2/
├── pyproject.toml
├── .python-version
├── .env
├── task1/
│   ├── threading_sum.py
│   ├── multiprocessing_sum.py
│   └── async_sum.py
└── task2/
    ├── __init__.py
    ├── config.py
    ├── threading_parse.py
    ├── multiprocessing_parse.py
    └── async_parse.py
```

---

## Теоретическая справка

### GIL (Global Interpreter Lock)

GIL — глобальная блокировка интерпретатора CPython, которая позволяет только одному потоку исполнять байт-код Python в каждый момент времени. Это означает:

- **CPU-bound задачи**: потоки (`threading`) не дают реального параллелизма — они исполняются поочерёдно.
- **I/O-bound задачи**: GIL **отпускается** на время ожидания I/O (сетевые запросы, чтение файлов), поэтому потоки эффективны.

### Сравнение подходов

| Характеристика | `threading` | `multiprocessing` | `asyncio` |
|---|---|---|---|
| Параллелизм | Конкурентность (не параллельность) | Истинный параллелизм | Кооперативная многозадачность |
| GIL | Ограничивает CPU-bound | Обходит (свой GIL в каждом процессе) | Не влияет (один поток) |
| Память | Общая | Изолированная (копирование) | Общая |
| Оверхед создания | Низкий | Высокий (fork/spawn) | Минимальный (корутины) |
| Лучше для | I/O-bound | CPU-bound | I/O-bound (высокая конкурентность) |

---

## Задача 1. Вычисление суммы чисел

### Описание

Вычисление суммы всех чисел от 1 до 1 000 000 000. Диапазон разбивается на `cpu_count()` равных частей, каждая часть обрабатывается параллельно.

### Реализация: Threading

Создаётся по одному потоку на каждый чанк. Результаты записываются в общий список по индексу (потокобезопасно, т.к. каждый поток пишет в свою ячейку):

```python
def calculate_sum(start: int, end: int, results: list[int], index: int) -> None:
    total = 0
    for i in range(start, end + 1):
        total += i
    results[index] = total

def main() -> None:
    chunk_size = TOTAL_NUMBER // NUM_THREADS
    threads: list[threading.Thread] = []
    results = [0] * NUM_THREADS

    for i in range(NUM_THREADS):
        start = i * chunk_size + 1
        end = (i + 1) * chunk_size if i < NUM_THREADS - 1 else TOTAL_NUMBER
        t = threading.Thread(target=calculate_sum, args=(start, end, results, i))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    total = sum(results)
```

!!! warning "Влияние GIL"
    Несмотря на запуск нескольких потоков, GIL не даёт им выполняться одновременно на разных ядрах. Фактическое время выполнения сопоставимо с последовательным.

### Реализация: Multiprocessing

Каждый чанк обрабатывается отдельным процессом через `Pool.starmap`:

```python
def calculate_sum(start: int, end: int) -> int:
    total = 0
    for i in range(start, end + 1):
        total += i
    return total

def main() -> None:
    chunk_size = TOTAL_NUMBER // NUM_PROCESSES
    ranges = [(i * chunk_size + 1,
               (i + 1) * chunk_size if i < NUM_PROCESSES - 1 else TOTAL_NUMBER)
              for i in range(NUM_PROCESSES)]

    with multiprocessing.Pool(NUM_PROCESSES) as pool:
        results = pool.starmap(calculate_sum, ranges)

    total = sum(results)
```

!!! success "Истинный параллелизм"
    Каждый процесс имеет собственный GIL и адресное пространство. Вычисления реально распределяются по ядрам процессора.

### Реализация: Async

Корутины запускаются через `asyncio.gather`:

```python
async def calculate_sum(start: int, end: int) -> int:
    total = 0
    for i in range(start, end + 1):
        total += i
    return total

async def main() -> None:
    tasks = [asyncio.create_task(calculate_sum(start, end))
             for start, end in chunks]
    results = await asyncio.gather(*tasks)
    total = sum(results)
```

!!! warning "Последовательное выполнение"
    В `calculate_sum` нет точек переключения (`await`). Корутины выполняются последовательно, как обычные функции. `asyncio` не предназначен для CPU-bound задач.

### Результаты замеров

Тестовая платформа: Apple M3 Pro (10 ядер), Python 3.14, N = 1 000 000 000.

| Подход | Количество workers | Время (сек) | Ускорение |
|---|---|---|---|
| Threading | 10 | ~37 | 1.0× (базовое) |
| Multiprocessing | 10 | ~6 | ~6× |
| Async | 10 | ~33 | ~1.1× |

### Выводы по задаче 1

1. **Multiprocessing** — единственный подход, обеспечивающий реальное ускорение для CPU-bound задач. Ускорение ≈ количеству физических ядер.
2. **Threading** работает медленнее из-за оверхеда переключения между потоками при удержании GIL.
3. **Async** выполняет корутины последовательно, т.к. без `await`-точек event loop не переключает задачи.

---

## Задача 2. Параллельный парсинг веб-страниц

### Описание

Парсинг 12 статей Wikipedia о финансовых категориях с сохранением заголовка и описания в таблицу `categories` базы данных из Лабораторной работы 1.

Список URL:

| URL | Категория |
|---|---|
| `/wiki/Expense` | needs |
| `/wiki/Income` | income |
| `/wiki/Budget` | needs |
| `/wiki/Saving` | wants |
| `/wiki/Investment` | wants |
| `/wiki/Tax` | needs |
| `/wiki/Insurance` | needs |
| `/wiki/Mortgage_loan` | needs |
| `/wiki/Credit_card` | needs |
| `/wiki/Salary` | income |
| `/wiki/Dividend` | income |
| `/wiki/Rent` | needs |

### Общая логика `parse_and_save`

Для каждого URL:

1. Загрузить HTML-страницу
2. Извлечь заголовок из `<h1>` и первый параграф из контента
3. Определить `category_type` по маппингу заголовок → тип
4. Сохранить запись в таблицу `categories`

### Реализация: Threading

Используется синхронный HTTP-клиент `requests` и синхронный движок SQLAlchemy (`postgresql+psycopg`). Все потоки разделяют один `Engine` (SQLAlchemy Engine потокобезопасен):

```python
engine = create_engine(SYNC_DATABASE_URL)

def parse_and_save(url: str) -> None:
    response = requests.get(url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(response.text, "html.parser")

    h1_span = soup.select_one("h1 .mw-page-title-main") or soup.find("h1")
    title = h1_span.get_text(strip=True) if h1_span else "Unknown"

    first_p = soup.select_one(
        "#mw-content-text .mw-parser-output > p:not(.mw-empty-elt)"
    )
    description = first_p.get_text(strip=True)[:500] if first_p else ""

    with engine.connect() as conn:
        conn.execute(INSERT_SQL, {"name": title, ...})
        conn.commit()
```

!!! note "Эффективность"
    Threading эффективен для I/O-bound задач: GIL отпускается на время `requests.get()`, позволяя другим потокам выполняться.

### Реализация: Multiprocessing

Каждый процесс создаёт **собственный** `Engine` и соединение с БД (нельзя передавать Engine между процессами):

```python
def parse_and_save(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=15)
    # ... парсинг ...

    engine = create_engine(SYNC_DATABASE_URL)
    with engine.connect() as conn:
        conn.execute(INSERT_SQL, {"name": title, ...})
        conn.commit()
    engine.dispose()
    return title
```

!!! warning "Оверхед процессов"
    Создание процессов и отдельных DB-соединений в каждом — избыточно для лёгких I/O задач. Multiprocessing оправдан, когда парсинг включает тяжёлые вычисления.

### Реализация: Async

Асинхронный HTTP-клиент `aiohttp` и async-движок SQLAlchemy (`postgresql+asyncpg`). Все запросы запускаются одновременно через `asyncio.gather`:

```python
engine = create_async_engine(ASYNC_DATABASE_URL)
async_session = async_sessionmaker(engine, class_=AsyncSession)

async def parse_and_save(session: aiohttp.ClientSession, url: str) -> None:
    async with session.get(url, headers=HEADERS) as response:
        html = await response.text()

    soup = BeautifulSoup(html, "html.parser")
    # ... парсинг ...

    async with async_session() as db:
        await db.execute(INSERT_SQL, {"name": title, ...})
        await db.commit()

async def main() -> None:
    async with aiohttp.ClientSession() as session:
        tasks = [parse_and_save(session, url) for url in URLS]
        await asyncio.gather(*tasks)
```

!!! success "Масштабируемость"
    Async подход использует один поток и одно соединение aiohttp, но обрабатывает все URL конкурентно. Масштабируется на тысячи URL без роста потребления памяти.

### Результаты замеров

Тестовая платформа: Apple M3 Pro, 12 URL, PostgreSQL 17.

| Подход | HTTP-клиент | БД-драйвер | Время (сек) |
|---|---|---|---|
| Threading | `requests` | `psycopg` | ~0.65 |
| Multiprocessing | `requests` | `psycopg` | ~1.70 |
| Async | `aiohttp` | `asyncpg` | ~0.77 |

### Выводы по задаче 2

1. **Threading** и **Async** показывают сравнимую производительность: оба подхода обеспечивают конкурентность при ожидании сетевых ответов.
2. **Multiprocessing** значительно медленнее из-за накладных расходов на fork/spawn процессов и создание отдельных DB-соединений.
3. **Async** предпочтительнее threading при большом числе URL: нет оверхеда на создание потоков ОС, нет конкуренции за GIL.

---

## Данные в БД

После запуска всех трёх парсеров в таблице `categories` появляются записи с заголовками и описаниями финансовых статей:

```
    name     | category_type |              description
-------------+---------------+----------------------------------------
 Budget      | needs         | ...
 Salary      | income        | A salary is a form of periodic payment
 Mortgage    | needs         | A mortgage loan or simply mortgage ...
 Expense     | needs         | An expense is an item requiring ...
 Saving      | wants         | Saving is income not spent ...
 Income      | income        | Income is the consumption and ...
 ...
```

---

## Общие выводы

| Тип задачи | Лучший подход | Обоснование |
|---|---|---|
| **CPU-bound** (вычисления) | `multiprocessing` | Обходит GIL, использует все ядра CPU |
| **I/O-bound** (сеть, БД) | `asyncio` / `threading` | GIL отпускается при I/O; async эффективнее по памяти и масштабируется лучше |
| **Смешанный** | `multiprocessing` + `asyncio` | Процессы для CPU-нагрузки, async для I/O внутри каждого процесса |

### Ключевые наблюдения

- **GIL** — главный фактор при выборе между `threading` и `multiprocessing` для CPU-bound задач.
- **Async** не подходит для CPU-bound задач без `await`-точек — корутины выполняются последовательно.
- **Multiprocessing** имеет высокий оверхед (создание процессов, IPC, копирование памяти) — не оправдан для лёгких I/O-задач.
- Для I/O-bound задач `async` + `aiohttp` — наиболее эффективный подход при высокой конкурентности (сотни/тысячи одновременных соединений).
