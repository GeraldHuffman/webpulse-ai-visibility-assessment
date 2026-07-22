FROM python:3.13-slim

WORKDIR /app

# Install uv for fast dependency management
RUN pip install --no-cache-dir uv

# Copy only pyproject.toml first for layer caching
COPY pyproject.toml .

# Install dependencies
RUN uv pip install --system --no-cache-dir fastapi uvicorn[standard] httpx beautifulsoup4 lxml pydantic pydantic-settings sqlalchemy asyncpg alembic arq redis openai resend python-multipart email-validator loguru tenacity

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run the app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
