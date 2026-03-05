import asyncio
from app.database import AsyncSessionLocal
from app.main import get_account_and_credentials
from app.adapters.factory import BrokerFactory
import logging

logging.basicConfig(level=logging.ERROR)

async def test():
    db = AsyncSessionLocal()
    account_id = "4438a19e-5d19-48c9-89d6-5134ee996591" # the E2E account ID
    try:
        acc, cred = await get_account_and_credentials(account_id, db)
        adapter = BrokerFactory.get_adapter(acc.broker_name, cred)
        await adapter.client.connect()
        await adapter.client.authorize_app(adapter.client_id, adapter.client_secret)
        await adapter.client.authorize_account(adapter.account_id, adapter.token)
        reconcile = await adapter.client.get_reconcile(adapter.account_id)
        
        print("\n=== RECONCILE DATA ===")
        print(f"openPositions: {len(reconcile.position)}")
        for p in reconcile.position:
            print(f"Position: ID={p.positionId}, Volume={p.tradeData.volume}, Side={p.tradeData.tradeSide}")
            
        print(f"pendingOrders: {len(reconcile.order)}")
        for o in reconcile.order:
            print(f"Order: ID={o.orderId}, Type={o.orderType}, Status={o.orderStatus}")
            
        print("\n=== ADAPTER OUTPUT ===")
        print("open_trades:", await adapter.get_open_trades())
        
    finally:
        await db.close()

if __name__ == '__main__':
    asyncio.run(test())
