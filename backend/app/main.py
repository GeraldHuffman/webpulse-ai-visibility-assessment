"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting WebPulse Assessment API ({settings.app_env})")
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

# Routes
# Root route for Railway health checks
@app.get("/")
async def root():
    return {"status": "healthy", "service": "webpulse-assessment-api"}

@app.get("/health")
async def health_root():
    return {"status": "healthy", "service": "webpulse-assessment-api"}

app.include_router(router)

logger.info(f"CORS origins: {settings.cors_origin_list}")
