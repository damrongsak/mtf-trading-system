import asyncio
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.future import select
from app.database import AsyncSessionLocal
from app.models import Trade, BrokerAccount, TradeStatus, TradeDirection

async def seed_test_trade():
    async with AsyncSessionLocal() as db:
        # 1. Get existing demo account
        stmt = select(BrokerAccount).where(BrokerAccount.account_name == "ICMarkets Demo 9919680").limit(1)
        res = await db.execute(stmt)
        account = res.scalar_one_or_none()
        
        if not account:
            print("❌ demo account not found.")
            return

        # Explicitly build the Trade object with all known columns to avoid positional mismatch
        test_trade = Trade()
        test_trade.trade_id = uuid.uuid4()
        test_trade.strategy_run_id = None
        test_trade.broker_account_id = account.id
        test_trade.symbol = "XAUUSD"
        test_trade.strategy_name = "Institutional_SMC"
        test_trade.signal_timestamp = datetime.utcnow() - timedelta(hours=2)
        test_trade.signal_id = None
        test_trade.signal_timestamp_ns = None
        test_trade.execution_latency_ms = Decimal("120.50")
        test_trade.slippage_pips = Decimal("0.5")
        test_trade.slippage_ms = Decimal("45.20")
        test_trade.is_live = False
        test_trade.is_shadow = False
        test_trade.parent_trade_id = None
        test_trade.execution_algo = None
        test_trade.algo_params = None
        test_trade.algo_status = "NONE"
        test_trade.status = TradeStatus.CLOSED
        test_trade.rejection_reason = None
        test_trade.direction = TradeDirection.LONG
        test_trade.entry_price = Decimal("2150.50")
        test_trade.sl_price = Decimal("2145.00")
        test_trade.tp_price = Decimal("2165.00")
        test_trade.trailing_stop = False
        test_trade.lot_size = Decimal("0.10")
        test_trade.risk_usd = Decimal("25.00")
        test_trade.atr_pips = Decimal("15.0")
        test_trade.rr_ratio = Decimal("2.5")
        test_trade.pnl_usd = Decimal("52.50")
        test_trade.mae_usd = Decimal("-5.00")
        test_trade.mfe_usd = Decimal("60.00")
        test_trade.exit_price = Decimal("2155.75")
        test_trade.exit_timestamp = datetime.utcnow() - timedelta(hours=1)
        test_trade.broker_trade_id = "BRK_12345"
        test_trade.broker_deal_id = f"DEAL_{uuid.uuid4().hex[:8]}"
        test_trade.commission = Decimal("0.70")
        test_trade.swap = Decimal("0.00")
        test_trade.gross_pnl = Decimal("53.20")
        test_trade.broker_raw_pnl = Decimal("53.20")
        test_trade.broker_commission = Decimal("0.70")
        test_trade.broker_swap = Decimal("0.00")
        test_trade.reconciled_at = datetime.utcnow()
        test_trade.reconciliation_status = "PENDING"
        test_trade.metadata_json = {"test": True}

        try:
            db.add(test_trade)
            await db.commit()
            print(f"✅ Seeded test trade {test_trade.trade_id} with DEAL ID {test_trade.broker_deal_id}")
        except Exception as e:
            print(f"❌ Failed to seed: {e}")
            await db.rollback()

if __name__ == "__main__":
    asyncio.run(seed_test_trade())
