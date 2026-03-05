import asyncio
from app.database import AsyncSessionLocal
from app.models import BrokerAccount
from app.main import get_account_and_credentials
from app.adapters.factory import BrokerFactory
import logging
from sqlalchemy import select

logging.basicConfig(level=logging.ERROR)

async def test():
    db = AsyncSessionLocal()
    try:
        # Get all cTrader accounts
        result = await db.execute(select(BrokerAccount).where(BrokerAccount.broker_name == 'CTRADER'))
        accounts = result.scalars().all()
        
        for acc in accounts:
            try:
                acc_obj, cred = await get_account_and_credentials(str(acc.id), db)
                adapter = BrokerFactory.get_adapter(acc_obj.broker_name, cred)
                await adapter.client.connect()
                await adapter.client.authorize_app(adapter.client_id, adapter.client_secret)
                await adapter.client.authorize_account(adapter.account_id, adapter.token)
                reconcile = await adapter.client.get_reconcile(adapter.account_id)
                
                print(f"Account: {acc.id} - Positions: {len(reconcile.position) if hasattr(reconcile, 'position') else 0}")
                if hasattr(reconcile, 'position') and len(reconcile.position) > 0:
                    print("Adapter trades:", await adapter.get_open_trades())
            except Exception as e:
                print(f"Error on account {acc.id}: {str(e)}")
    finally:
        await db.close()

if __name__ == '__main__':
    asyncio.run(test())
