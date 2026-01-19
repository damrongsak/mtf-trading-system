import asyncio
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database URL (force asyncpg for async engine)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://trader:trader@mtf-postgres:5432/mtf_db")
if "asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Sync Engine for quick check script (using psycopg2 driver usually, but let's stick to async or just standard psycopg)
# Alternatively, I'll use async since the service uses it.
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

async def main():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with async_session() as session:
        # Check Total Accounts
        result = await session.execute(text("SELECT count(*) FROM broker_accounts"))
        total = result.scalar()
        print(f"Total Broker Accounts: {total}")

        # Check Active Accounts
        result = await session.execute(text("SELECT count(*) FROM broker_accounts WHERE is_active = true"))
        active = result.scalar()
        print(f"Active Broker Accounts: {active}")

        if total > 0 and active == 0:
            print("Found accounts but none are active. Attempting to activate them...")
            await session.execute(text("UPDATE broker_accounts SET is_active = true WHERE is_active IS NOT true"))
            await session.commit()
            print("Activated all accounts.")
            
        # Verify content
        result = await session.execute(text("SELECT id, broker_name, is_active FROM broker_accounts"))
        rows = result.fetchall()
        for row in rows:
            print(f"Account: {row}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
