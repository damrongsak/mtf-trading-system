import asyncio
from app.database import AsyncSessionLocal
from app.main import get_account_and_credentials
from app.adapters.factory import BrokerFactory
import logging

logging.basicConfig(level=logging.INFO)

async def test():
    db = AsyncSessionLocal()
    account_id = '4438a19e-5d19-48c9-89d6-5134ee996591'
    try:
        acc, cred = await get_account_and_credentials(account_id, db)
        adapter = BrokerFactory.get_adapter(acc.broker_name, cred)
        print("Summary:", await adapter.get_account_summary())
        print("Trades:", await adapter.get_open_trades())
    finally:
        await db.close()

if __name__ == '__main__':
    asyncio.run(test())
