"""Async SQLAlchemy engine and session factory."""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)

AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a scoped async DB session."""
    async with AsyncSessionLocal() as session:
        yield session


def make_session_factory() -> tuple["async_sessionmaker[AsyncSession]", "create_async_engine"]:
    """Create a **fresh** async engine + session factory that is safe to use
    inside a new event loop (e.g. a Celery task running asyncio.run()).

    Uses NullPool so that asyncpg never caches connections across loop
    boundaries - the root cause of the
    "Future attached to a different loop" RuntimeError that occurs when
    the module-level engine's pooled connections (bound to FastAPI's loop)
    are reused inside a worker thread's separate asyncio.run() loop.

    Callers are responsible for calling engine.dispose() when finished.
    """
    task_engine = create_async_engine(
        settings.database_url,
        echo=False,
        poolclass=NullPool,  # never pool connections - each acquire is a fresh connect
    )
    factory = async_sessionmaker(bind=task_engine, expire_on_commit=False, class_=AsyncSession)
    return factory, task_engine
