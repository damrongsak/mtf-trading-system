import asyncio
import uuid
import sys

# Ensure app is in path
sys.path.append('/app')

from app.database import AsyncSessionLocal
from app.models import BrokerAccount
from app.adapters.factory import BrokerFactory
from app.utils.crypto import decrypt_data
from sqlalchemy import select

async def emergency_close(account_id_str):
    async with AsyncSessionLocal() as db:
        try:
            account_uuid = uuid.UUID(account_id_str)
        except ValueError:
            print(f"Invalid UUID: {account_id_str}")
            return

        result = await db.execute(select(BrokerAccount).where(BrokerAccount.id == account_uuid))
        account = result.scalars().first()
        
        if not account:
            print("Account not found")
            return

        print(f"Connecting to {account.account_name} ({account.broker_name})...")
        credentials = decrypt_data(account.credentials_encrypted)
        credentials["environment"] = account.environment
        adapter = BrokerFactory.get_adapter(account.broker_name, credentials)
        
        # Get all positions
        try:
            trades = await adapter.get_open_trades()
            print(f"Found {len(trades)} open positions.")
            
            for t in trades:
                print(f"Position: {t['id']} | Symbol: {t['symbol']} | Units: {t['units']} | Side: {t['side']}")
                # Close ANY position > 5 units of Gold (which would be 0.05 lot, safe threshold for "too big")
                # Or just close ALL if this is an emergency script for this account
                if t['units'] >= 5.0 or "XAU" in t['symbol']:
                    print(f"EMERGENCY: Closing {t['id']} ({t['units']} units)...")
                    await adapter.close_trade(t['id'])
                    print("Closed.")
        except Exception as e:
            print(f"Error during closure: {e}")

if __name__ == "__main__":
    # cTrader Account ID
    acc_id = "4438a19e-5d19-48c9-89d6-5134ee996591"
    asyncio.run(emergency_close(acc_id))
