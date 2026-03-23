import asyncio
import json
import logging
import pandas as pd
from datetime import datetime, timezone
from typing import List, Dict, Any

from sqlalchemy import select, update
from app.database import AsyncSessionLocal
from app.models import Fund, Strategy, PortfolioAllocation
from app.utils.data_pipeline_client import DataPipelineClient
from app.services.allocation_service import AllocationService
from app.utils.redis_client import get_redis_client

logger = logging.getLogger(__name__)

class PortfolioRebalancer:
    """
    [PHASE 30] Portfolio Rebalancer Service.
    Periodically recalculates Risk Parity weights for all active funds.
    """
    def __init__(self):
        self.pipeline_client = DataPipelineClient()

    async def rebalance_all_funds(self):
        """
        Main entry point to rebalance all eligible funds.
        """
        logger.info("⚖️ [Rebalancer] Starting global portfolio rebalancing...")
        async with AsyncSessionLocal() as db:
            # 1. Fetch all funds with risk parity enabled
            stmt = select(Fund).where(Fund.risk_parity_enabled == True)
            result = await db.execute(stmt)
            funds = result.scalars().all()
            
            if not funds:
                logger.info("⚖️ [Rebalancer] No funds with Risk Parity enabled found.")
                return

            for fund in funds:
                try:
                    await self.rebalance_fund(db, fund)
                except Exception as e:
                    logger.error(f"⚖️ [Rebalancer] Failed to rebalance Fund {fund.name} ({fund.id}): {e}", exc_info=True)

    async def rebalance_fund(self, db, fund: Fund):
        """
        Rebalance a specific fund.
        """
        logger.info(f"⚖️ [Rebalancer] Rebalancing Fund: {fund.name} ({fund.id})")
        
        # 1. Identify active strategies and their symbols
        stmt = select(Strategy).where(Strategy.fund_id == fund.id, Strategy.is_active == True)
        result = await db.execute(stmt)
        strategies = result.scalars().all()
        
        if not strategies:
            logger.warning(f"⚖️ [Rebalancer] No active strategies found for Fund {fund.name}.")
            return

        symbols = list(set([s.config_json.get("symbol") for s in strategies if s.config_json.get("symbol")]))
        if not symbols:
             logger.warning(f"⚖️ [Rebalancer] No symbols resolved for Fund {fund.name}.")
             return

        # 2. Fetch Historical Price Data (D1 for volatility calculation)
        prices_map = {}
        for sym in symbols:
            candles = await self.pipeline_client.get_candles(sym, "D1", limit=100)
            if candles:
                # Need sort ascending for pct_change
                df = pd.DataFrame(candles)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.sort_values('timestamp', inplace=True)
                prices_map[sym] = df.set_index('timestamp')['close'].astype(float)
        
        if not prices_map:
            logger.error(f"⚖️ [Rebalancer] Could not fetch price history for any symbols in {fund.name}.")
            return

        prices_df = pd.DataFrame(prices_map).fillna(method='ffill').dropna()
        
        if len(prices_df) < 20:
             logger.warning(f"⚖️ [Rebalancer] Insufficient history length ({len(prices_df)}) for {fund.name}.")
             return

        # 3. Optimize Weights
        # Note: AllocationService currently take equity but we just want weights
        # We can extract them directly or via AllocationService
        allocator = AllocationService(prices_df, total_equity=100.0) # Dummy equity for weight extraction
        weights = allocator.get_risk_parity_weights(model=fund.risk_parity_model or "HRP")
        
        logger.info(f"⚖️ [Rebalancer] {fund.name} New Weights: {weights}")

        # 4. Persistence (DB)
        for strategy in strategies:
            sym = strategy.config_json.get("symbol")
            weight = weights.get(sym, 0.0)
            
            # Check if allocation record exists
            stmt = select(PortfolioAllocation).where(
                PortfolioAllocation.fund_id == fund.id,
                PortfolioAllocation.strategy_id == strategy.id
            )
            res = await db.execute(stmt)
            existing = res.scalar_one_or_none()
            
            if existing:
                existing.weight = weight
                existing.last_rebalance = datetime.now(timezone.utc)
            else:
                new_alloc = PortfolioAllocation(
                    fund_id=fund.id,
                    strategy_id=strategy.id,
                    weight=weight,
                    last_rebalance=datetime.now(timezone.utc)
                )
                db.add(new_alloc)
        
        await db.commit()

        # 5. Persistence (Redis)
        # RiskParityEngine expects a map of symbol -> weight in Redis
        rc = get_redis_client()
        redis_key = f"fund:{fund.id}:risk_parity_weights"
        await rc.set(redis_key, json.dumps(weights), ex=86400 * 7) # 7 day TTL
        
        logger.info(f"✅ [Rebalancer] Fund {fund.name} rebalanced successfully.")
