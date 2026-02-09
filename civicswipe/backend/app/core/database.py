"""
Database connection and session management
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator

from app.core.config import settings

# Only echo SQL in development — massive I/O overhead in production
_echo_sql = settings.ENVIRONMENT == "development"

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=_echo_sql,
    future=True,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=40,
)

# Create async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Base class for models
Base = declarative_base()


async def init_db():
    """Initialize database connection"""
    # Test connection
    async with engine.begin() as conn:
        # Could create tables here if needed
        # await conn.run_sync(Base.metadata.create_all)
        pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database session
    
    Usage in FastAPI:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
