#!/usr/bin/env bash
set -e

# Ждём, пока Postgres не станет доступен
until pg_isready --host="$DB_SERVER" --port="$POSTGRES_PORT" --username="$POSTGRES_USER" --dbname="$POSTGRES_DB"; do
  echo "Waiting for Postgres..."
  sleep 2
done

echo "Postgres is ready!"

# Применяем все миграции Alembic
echo "Running Alembic migrations..."
uv run alembic upgrade head

echo "Starting FastAPI server..."
# Запускаем FastAPI
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --reload-exclude '.venv'
