"""Logging configuration using loguru."""

import sys
from loguru import logger

from app.core.config import get_settings

settings = get_settings()

logger.remove()
logger.add(
    sys.stderr,
    level="DEBUG" if settings.app_env == "development" else "INFO",
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    ),
    serialize=settings.app_env == "production",
)


def get_logger():
    return logger
