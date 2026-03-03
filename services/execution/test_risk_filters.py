import asyncio
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.services.order_service import OrderService
from app.models import BrokerAccount, Fund
import os

# Database details for Docker
DATABASE_URL = "postgresql+asyncpg://trader:trader@mtf-postgres:5432/mtf_db"

async def test_risk_filters():
    engine = create_async_engine(DATABASE_URL)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as db:
        # Fetch a real account to test with
        from sqlalchemy import select
        result = await db.execute(select(BrokerAccount).where(BrokerAccount.is_active == True))
        account = result.scalars().first()
        
        if not account:
            print("No active BrokerAccount found in DB for testing.")
            return

        print(f"Testing with account: {account.id}")

        # 1. Test SL/TP Mandatory
        req_no_sl = {
            "broker_account_id": str(account.id),
            "symbol": "XAUUSD",
            "direction": "BULLISH",
            "stop_loss": 0,
            "take_profit": 2100,
            "generated_by": "TestStrategy",
            "signal_id": "test-1"
        }
        
        try:
            print("\n--- Testing SL Mandatory ---")
            await OrderService.execute_smart_order(req_no_sl, db)
        except Exception as e:
            print(f"Caught expected error: {e}")

        # 2. Test Session Filter (if during restricted time)
        # Note: This depends on the current time. 
        # London Open: 08:00 GMT, NY Open: 13:00 GMT. 
        # If running around those times, it should trigger.

        req_valid = {
            "broker_account_id": str(account.id),
            "symbol": "XAUUSD",
            "direction": "BULLISH",
            "stop_loss": 2000,
            "take_profit": 2100,
            "generated_by": "TestStrategy",
            "signal_id": "test-2",
            "risk_usd": 10.0
        }
        
        print("\n--- Testing Valid Request with Risk Filters ---")
        try:
             # This might fail on other filters (News, Spread, ATR) which is good proof they work
             await OrderService.execute_smart_order(req_valid, db)
        except Exception as e:
             print(f"Result (Filter Action): {e}")

if __name__ == "__main__":
    asyncio.run(test_risk_filters())
