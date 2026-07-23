"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.database import Base, get_engine
# Import all models so they register with Base
from app.models.orm import Assessment, SiteSignal, Report, Lead, EmailLog, ScheduledCall

settings = get_settings()
logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting WebPulse Assessment API ({settings.app_env})")
    # Auto-create tables and add missing columns on startup
    try:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            # Add missing columns to existing tables (create_all won't do this)
            from sqlalchemy import text, inspect
            def add_missing_columns(sync_conn):
                inspector = inspect(sync_conn)
                # Check reports table for new columns
                if 'reports' in inspector.get_table_names():
                    existing_cols = [c['name'] for c in inspector.get_columns('reports')]
                    missing = []
                    if 'big_opportunity' not in existing_cols:
                        missing.append("ALTER TABLE reports ADD COLUMN big_opportunity TEXT")
                    if 'current_state' not in existing_cols:
                        missing.append("ALTER TABLE reports ADD COLUMN current_state TEXT")
                    for sql in missing:
                        sync_conn.execute(text(sql))
                        logger.info(f"Added column: {sql}")
            await conn.run_sync(add_missing_columns)
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.warning(f"Could not create/migrate tables on startup: {e}")
    yield
    logger.info("Shutting down WebPulse Assessment API")


app = FastAPI(
    title="WebPulse AI Visibility Assessment API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Root routes for health checks
@app.get("/")
async def root():
    return {"status": "healthy", "service": "webpulse-assessment-api"}

@app.get("/health")
async def health_root():
    return {"status": "healthy", "service": "webpulse-assessment-api"}

# API routes
app.include_router(router)

logger.info(f"CORS origins: {settings.cors_origin_list}")
