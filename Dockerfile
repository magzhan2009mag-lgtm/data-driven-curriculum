# Один контейнер для живой демо-ссылки: аналитика (FastAPI) и интерфейс (Next.js).
# Наружу открыт только порт интерфейса ($PORT, по умолчанию 10000); API и Swagger — по адресу /api/…
#   docker build -t ddc . && docker run -p 3000:10000 ddc   →   http://localhost:3000

# --- Интерфейс: сборка Next.js в standalone ---
FROM node:22-bookworm-slim AS web
WORKDIR /app/frontend
ENV NEXT_TELEMETRY_DISABLED=1 NEXT_OUTPUT=standalone API_URL=http://127.0.0.1:8000
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# --- Итоговый образ: Python для аналитики + node для интерфейса ---
FROM python:3.12-slim-bookworm
RUN apt-get update \
    && apt-get install -y --no-install-recommends libstdc++6 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=web /usr/local/bin/node /usr/local/bin/node

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
    NEXT_TELEMETRY_DISABLED=1 NODE_ENV=production API_URL=http://127.0.0.1:8000 PORT=10000

WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install -r backend/requirements.txt

COPY backend/ backend/
# Демо-данные (seed 42) создаются при сборке, поэтому контейнер стартует сразу.
RUN cd backend && python -m scripts.seed --reset

COPY --from=web /app/frontend/.next/standalone frontend/
COPY --from=web /app/frontend/.next/static frontend/.next/static
COPY --from=web /app/frontend/public frontend/public
COPY docker/start.sh /app/start.sh

RUN useradd --create-home app && chown -R app /app
USER app

EXPOSE 10000
CMD ["sh", "/app/start.sh"]
