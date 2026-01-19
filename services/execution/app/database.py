from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
import os

# Ensure DATABASE_URL starts with postgresql+asyncpg
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://trader:trader@localhost:5432/mtf_db"
)
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Use NullPool for compatibility with async frameworks if needed, or QueuePool for production
engine = create_async_engine(
    DATABASE_URL,
    poolclass=NullPool,
    echo=False
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()
