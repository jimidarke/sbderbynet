"""
Database configuration and session management with async SQLAlchemy.
Implements Row-Level Security (RLS) for multi-tenant isolation.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import text

# Import Base from models to ensure a single Base class
from models.base import Base


# Lazy-initialized engine and session factory (for testability)
_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Get or create the database engine (lazy initialization)."""
    global _engine
    if _engine is None:
        from app.config import get_settings
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_timeout=settings.database_pool_timeout,
            echo=settings.debug,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get or create the session factory (lazy initialization)."""
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides a database session.
    Use this for routes that don't require tenant context.
    """
    async with get_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_tenant_db(org_id: str) -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager that provides a database session with tenant context.
    Sets the RLS session variable for tenant isolation.

    Usage:
        async with get_tenant_db(org_id) as session:
            # All queries are now scoped to this org
            results = await session.execute(select(Event))
    """
    async with get_session_factory()() as session:
        try:
            # Set the tenant context for RLS
            await session.execute(
                text("SET app.current_org_id = :org_id"),
                {"org_id": org_id}
            )
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            # Clear tenant context
            await session.execute(text("RESET app.current_org_id"))
            await session.close()


async def init_db() -> None:
    """Initialize database tables. Run during startup."""
    async with get_engine().begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections. Run during shutdown."""
    await get_engine().dispose()
