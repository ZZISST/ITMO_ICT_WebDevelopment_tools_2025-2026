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
alembic upgrade head

# Ждём, пока Ollama не станет доступен, и скачиваем модель
OLLAMA_HOST="${OLLAMA_HOST:-http://ollama:11434}"
OLLAMA_MODEL="${OLLAMA_MODEL:-llama3.2}"
MAX_OLLAMA_WAIT=60
WAITED=0

echo "Waiting for Ollama at ${OLLAMA_HOST} ..."
while [ "$WAITED" -lt "$MAX_OLLAMA_WAIT" ]; do
  if curl -sf "${OLLAMA_HOST}/api/version" > /dev/null 2>&1; then
    echo "Ollama is reachable."
    break
  fi
  sleep 3
  WAITED=$((WAITED + 3))
  echo "  ...still waiting for Ollama (${WAITED}s / ${MAX_OLLAMA_WAIT}s)"
done

if [ "$WAITED" -ge "$MAX_OLLAMA_WAIT" ]; then
  echo "WARNING: Ollama did not become ready within ${MAX_OLLAMA_WAIT}s. Skipping model pull."
else
  # Check whether the model is already pulled
  MODEL_EXISTS=$(curl -sf "${OLLAMA_HOST}/api/tags" 2>/dev/null \
    | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    models = data.get('models', [])
    names = [m.get('name','').split(':')[0] for m in models]
    print('yes' if '${OLLAMA_MODEL}'.split(':')[0] in names else 'no')
except:
    print('no')
" 2>/dev/null || echo "no")

  if [ "$MODEL_EXISTS" = "yes" ]; then
    echo "Ollama model '${OLLAMA_MODEL}' is already available."
  else
    echo "Pulling Ollama model '${OLLAMA_MODEL}'... This may take several minutes on first run."
    # Use curl to trigger a pull via the Ollama API (streams progress as JSON)
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
      --max-time 600 \
      -X POST "${OLLAMA_HOST}/api/pull" \
      -H "Content-Type: application/json" \
      -d "{\"name\": \"${OLLAMA_MODEL}\", \"stream\": false}" 2>/dev/null || echo "000")

    if [ "$HTTP_CODE" = "200" ]; then
      echo "Ollama model '${OLLAMA_MODEL}' pulled successfully."
    else
      echo "WARNING: Failed to pull Ollama model '${OLLAMA_MODEL}' (HTTP ${HTTP_CODE}). AI features will use rule-based fallback."
    fi
  fi
fi

echo "Starting FastAPI server..."
# Запускаем FastAPI
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload
