import asyncio
import os
import sys
import logging
from app.adapters.factory import BrokerFactory
from app.utils.crypto import decrypt_data
from app.database import AsyncSessionLocal
from app.models import BrokerAccount
from sqlalchemy import select

# Add the project root to sys.path
sys.path.append(os.path.join(os.getcwd(), ".."))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("oanda-check")

async def check():
    async with AsyncSessionLocal() as db:
        stmt = select(BrokerAccount).where(BrokerAccount.id == "58840dc3-d1f1-4a9a-b1e0-fa04e1035e78")
        result = await db.execute(stmt)
        acc = result.scalar_one_or_none()
        
        if not acc:
            print("FAILED: Account not found")
            return
            
        creds = decrypt_data(acc.credentials_encrypted)
        creds["environment"] = acc.environment
        
        print(f"DEBUG: Using environment: {creds['environment']}")
        adapter = BrokerFactory.get_adapter("OANDA", creds)
        
        try:
            summary = await adapter.get_account_summary()
            print(f"SUCCESS: {summary}")
        except Exception as e:
            print(f"FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(check())
