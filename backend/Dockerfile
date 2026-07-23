# Cache bust: 2026-07-23-v2
FROM python:3.13-slim

WORKDIR /app

RUN pip install --no-cache-dir fastapi uvicorn[standard] httpx beautifulsoup4 lxml pydantic pydantic-settings sqlalchemy asyncpg alembic arq redis openai psycopg2-binary resend python-multipart email-validator loguru tenacity

COPY . .

EXPOSE 8000

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
