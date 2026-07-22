"""Async SQLAlchemy database setup."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

# Normalize URL for asyncpg:
# 1. Convert postgresql:// to postgresql+asyncpg://
# 2. Convert sslmode=require to ssl=require (asyncpg uses different param name)
db_url = settings.database_url
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
if "sslmode=require" in db_url:
    db_url = db_url.replace("sslmode=require", "ssl=require")
# Also handle sslmode=verify-full etc
db_url = db_url.replace("sslmode=verify-full", "ssl=verify-full")
db_url = db_url.replace("sslmode=verify-ca", "ssl=verify-ca")
db_url = db_url.replace("sslmode=disable", "ssl=disable")
db_url = db_url.replace("sslmode=prefer", "ssl=prefer")
db_url = db_url.replace("sslmode=allow", "ssl=allow")

# Create engine lazily - don't fail at import time if DB is unavailable
engine = None
async_session = None

def get_engine():
    global engine
    if engine is None:
        engine = create_async_engine(db_url, echo=settings.app_env == "development")
    return engine

def get_session_maker():
    global async_session
    if async_session is None:
        async_session = async_sessionmaker(get_engine(), class_=AsyncSession, expire_on_commit=False)
    return async_session


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    maker = get_session_maker()
    async with maker() as session:
        yield session
