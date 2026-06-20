# syntax=docker/dockerfile:1.7

# ── Stage 1: build frontends (skipped in Phase 1 — no frontend yet) ──────────
# Placeholder — frontend stages will be added in Phase 2/3

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

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
