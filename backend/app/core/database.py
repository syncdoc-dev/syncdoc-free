"""Database initialization and session management"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from app.core.config import settings

# Base class for models
Base = declarative_base()

# Lazy-initialized engine and session factory
_engine = None
_async_session_local = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.environment == "development",
            future=True,
        )
    return _engine


def _get_session_factory():
    global _async_session_local
    if _async_session_local is None:
        _async_session_local = async_sessionmaker(
            _get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_local


def get_session_factory():
    """Return the shared async session factory."""
    return _get_session_factory()


async def get_db():
    """Get database session"""
    async with _get_session_factory()() as session:
        yield session


async def init_db():
    """Initialize database (runs migrations)"""
    # Migrations are handled by Alembic on container startup
    pass
