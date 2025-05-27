"""SQLAlchemy session management"""

from sqlalchemy import create_engine, text, event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateSchema

from config import settings

# Create async engine for PostgreSQL
async_engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.DEBUG,
    future=True,
)

# Create sync engine for migrations and utilities
sync_engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    echo=settings.DEBUG,
    future=True,
)

# Create session factories
AsyncSessionLocal = sessionmaker(
    async_engine, 
    class_=AsyncSession, 
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Utility function to get a database session
async def get_db():
    """
    Dependency for FastAPI to get a DB session
    """
    db = AsyncSessionLocal()
    try:
        yield db
    finally:
        await db.close() 