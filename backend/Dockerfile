FROM python:3.13-slim

# Cache bust - forces fresh build
ARG CACHE_BUST=1

WORKDIR /app

# Install all dependencies explicitly
RUN pip install --no-cache-dir fastapi uvicorn[standard] httpx beautifulsoup4 lxml pydantic pydantic-settings sqlalchemy asyncpg alembic arq redis openai psycopg2-binary resend python-multipart email-validator loguru tenacity

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run the app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
