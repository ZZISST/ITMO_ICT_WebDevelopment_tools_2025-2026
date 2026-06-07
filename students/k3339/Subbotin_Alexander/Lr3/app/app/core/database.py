import logging
from typing import Any, AsyncGenerator

import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.settings.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(settings.DATABASE_URL, echo=True, future=True)

async_session_local = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, Any]:
    """
    Dependency for getting async database session.

    Yields:
        AsyncSession: SQLAlchemy async session instance
    """
    async with async_session_local() as session:
        yield session


async def init_db():
    """
    Initialize database on application startup.

    Creates all tables based on SQLAlchemy models.
    This function is called during the lifespan startup event.
    """
    from app.core.db import Base
    from app.core.db.models.finance import (
        Budget,
        Category,
        FinancialAnalysis,
        FinancialGoal,
        Transaction,
    )

    # Import all models to register them in metadata
    from app.core.db.models.user import User, UserProfile

    logger.info("Creating database tables...")
    async with engine.begin() as conn:
        # Add 'income' to categorytype enum if it doesn't exist yet
        # (create_all won't alter existing enum types)
        await conn.execute(
            sqlalchemy.text(
                "DO $$ BEGIN "
                "  IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'categorytype') THEN "
                "    BEGIN "
                "      ALTER TYPE categorytype ADD VALUE IF NOT EXISTS 'INCOME'; "
                "    EXCEPTION WHEN duplicate_object THEN NULL; "
                "    END; "
                "  END IF; "
                "END $$;"
            )
        )
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created successfully")


async def close_db():
    """
    Close database connections on application shutdown.

    Disposes of the engine and closes all active connections.
    This function is called during the lifespan shutdown event.
    """
    logger.info("Disposing database engine...")
    await engine.dispose()
    logger.info("Database engine disposed successfully")
