# syntax=docker/dockerfile:1.7

# ── Stage 1: build LIFF frontend ─────────────────────────────────────────────
FROM node:20-slim AS node-builder
WORKDIR /app/frontend/liff
COPY frontend/liff/package*.json ./
RUN npm ci
COPY frontend/liff/ ./
ARG LIFF_ID
ENV VITE_LIFF_ID=$LIFF_ID
RUN npm run build

# ── Stage 2: Python runtime ───────────────────────────────────────────────────
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir -U pip
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY --from=node-builder /app/frontend/liff/dist ./frontend/liff/dist

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
