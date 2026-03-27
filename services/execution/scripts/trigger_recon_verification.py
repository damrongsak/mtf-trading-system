import asyncio
import uuid
from sqlalchemy.future import select
from app.database import AsyncSessionLocal
from app.models import Trade, BrokerAccount, UserFund
from app.services.history_reconciliation import HistoryReconciliationService

async def trigger_reconciliation():
    async with AsyncSessionLocal() as db:
        # 1. Get existing demo account
        stmt = select(BrokerAccount).where(BrokerAccount.account_name == "ICMarkets Demo 9919680").limit(1)
        res = await db.execute(stmt)
        account = res.scalar_one_or_none()
        
        if not account:
            print("❌ demo1 account not found.")
            return

        print(f"🔄 Manual Trigger for {account.account_name} ({account.id})")
        
        # 2. Get the seeded trade
        stmt_trade = select(Trade).where(Trade.broker_account_id == account.id).order_by(Trade.signal_timestamp.desc()).limit(1)
        res_trade = await db.execute(stmt_trade)
        trade = res_trade.scalar_one_or_none()
        
        if not trade:
            print("❌ No seeded trade found.")
            return
            
        # 3. Mark as success and get user_id
        trade.reconciliation_status = "SUCCESS"
        
        stmt_user = select(UserFund.user_id).where(UserFund.fund_id == account.fund_id).limit(1)
        user_res = await db.execute(stmt_user)
        user_id = user_res.scalar_one_or_none()
        
        await db.commit()
        
        # 4. Publish Command
        print(f"🚀 Publishing Post-Mortem Command for Trade {trade.trade_id}")
        await HistoryReconciliationService._publish_post_mortem_cmd(trade, user_id)
        
        print("✅ Command published. Wait ~10s and check post_mortems table.")

if __name__ == "__main__":
    asyncio.run(trigger_reconciliation())
