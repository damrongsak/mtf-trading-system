import logging
import os
import json
from datetime import datetime
from sqlalchemy.future import select
from app.models import BrokerAccount, AccountHistory
from app.adapters.factory import BrokerFactory
from app.utils.crypto import decrypt_data
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

class AnalyticsService:
    @classmethod
    async def capture_all_account_snapshots(cls):
        """
        [INSTITUTIONAL] Periodic job to capture fiscal snapshots for all active accounts.
        Tracks: balance, equity, used_margin, free_margin, margin_level, unrealized_gross, unrealized_net.
        """
        logger.info("📊 [Analytics] Starting account metric snapshot cycle...")
        
        async with AsyncSessionLocal() as db:
            # 1. Fetch active accounts
            stmt = select(BrokerAccount).where(BrokerAccount.is_active)
            result = await db.execute(stmt)
            accounts = result.scalars().all()
            
            captured_count = 0
            for account in accounts:
                try:
                    # 2. Initialize Adapter
                    credentials = decrypt_data(account.credentials_encrypted)
                    credentials["environment"] = account.environment
                    # Force numeric ID for cTrader/OANDA if needed by adapter
                    adapter = BrokerFactory.get_adapter(account.broker_name, credentials)
                    
                    # 3. Fetch fiscal summary from broker
                    # Standard interface: get_account_summary()
                    summary = await adapter.get_account_summary()
                    
                    # 4. Save to AccountHistory
                    snapshot = AccountHistory(
                        broker_account_id=account.id,
                        balance=float(summary.get("balance", 0)),
                        equity=float(summary.get("equity") or summary.get("NAV", 0)),
                        used_margin=float(summary.get("used_margin") or summary.get("marginUsed", 0)),
                        free_margin=float(summary.get("free_margin") or summary.get("marginAvailable", 0)),
                        margin_level=float(summary.get("margin_level") or summary.get("marginCallPercent", 0)),
                        unrealized_gross=float(summary.get("unrealized_gross", 0)),
                        unrealized_net=float(summary.get("unrealized_net") or summary.get("unrealizedPL", 0)),
                        timestamp=datetime.utcnow()
                    )
                    db.add(snapshot)
                    
                    # 5. Update last known balance in BrokerAccount table (Phase 28 legacy alignment)
                    account.balance_snapshot = snapshot.balance
                    
                    captured_count += 1
                    logger.debug(f"📊 [Analytics] Snapshot captured for {account.broker_name}:{account.account_name}")
                    
                except Exception as e:
                    logger.error(f"📊 [Analytics] Failed to capture snapshot for {account.id} ({account.broker_name}): {e}")
            
            # 6. Trigger Risk Parity Weight Recalculation (for all active funds)
            await cls.recalculate_all_fund_risk_parity_weights(db)

            if captured_count > 0:
                await db.commit()
                logger.info(f"📊 [Analytics] Snapshot cycle complete. Captured {captured_count} accounts.")
            else:
                logger.info("📊 [Analytics] No active accounts found for snapshots.")

    @classmethod
    async def recalculate_all_fund_risk_parity_weights(cls, db: AsyncSessionLocal):
        """
        [INSTITUTIONAL] Recalculate HRP/Risk Parity weights for all funds with RP enabled.
        Stores results in Redis for O(1) access by OrderService.
        """
        from app.models import Fund
        stmt = select(Fund).where(Fund.risk_parity_enabled)
        result = await db.execute(stmt)
        funds = result.scalars().all()
        
        for fund in funds:
            try:
                await cls.update_fund_risk_parity_weights(fund)
            except Exception as e:
                logger.error(f"📊 [Analytics] Failed to update RP weights for Fund {fund.id}: {e}")

    @classmethod
    async def update_fund_risk_parity_weights(cls, fund):
        """
        Fetch historical bars, calculate HRP, and cache in Redis.
        """
        import pandas as pd
        import httpx
        from app.services.cache_service import execution_cache
        from app.services.allocation_service import AllocationService
        
        # 1. Identify symbols in portfolio
        symbols = fund.asset_classes if isinstance(fund.asset_classes, list) else ["XAU_USD"]
        if not symbols:
            return
            
        # 2. Fetch last 250 bars for each symbol from Data Pipeline
        # Note: In production, use internal k8s/docker DNS (http://data-pipeline:8001)
        data_pipeline_url = os.getenv("DATA_PIPELINE_URL", "http://data-pipeline:8001")
        
        prices_data = {}
        async with httpx.AsyncClient() as client:
            for symbol in symbols:
                try:
                    # Fetch H1 bars (more stable for HRP)
                    resp = await client.get(
                        f"{data_pipeline_url}/api/v1/candles/{symbol}",
                        params={"timeframe": "H1", "limit": 250},
                        timeout=5.0
                    )
                    if resp.status_code == 200:
                        candles = resp.json()
                        # Assuming response is list of candles with 'close' and 'timestamp'
                        df = pd.DataFrame(candles)
                        if not df.empty and 'close' in df:
                            prices_data[symbol] = df.set_index('timestamp')['close']
                except Exception as ex:
                    logger.warning(f"📊 [Analytics] Could not fetch data for {symbol}: {ex}")

        if not prices_data:
            logger.warning(f"📊 [Analytics] No price data found for Fund {fund.id} symbols.")
            return

        # 3. Build prices DataFrame
        prices_df = pd.DataFrame(prices_data).ffill().dropna()
        if len(prices_df) < 20: # Minimum bars for covariance
            logger.warning(f"📊 [Analytics] Insufficient data for HRP: {len(prices_df)} bars.")
            return

        # 4. Calculate Weights
        # Total equity is helpful for units, but we only need weights for caching
        all_service = AllocationService(prices_df, total_equity=100000.0)
        weights = all_service.get_risk_parity_weights(model=fund.risk_parity_model or "HRP")
        
        # 5. Cache in Redis
        cache_key = f"fund:{fund.id}:risk_parity_weights"
        await execution_cache.redis.set(cache_key, json.dumps(weights), ex=7200) # 2h TTL
        logger.info(f"📊 [Analytics] Cached RP weights for Fund {fund.name}: {weights}")
