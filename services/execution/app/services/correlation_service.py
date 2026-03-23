import asyncio
import json
import logging
import pandas as pd
from datetime import datetime, timezone
from typing import List, Dict, Any

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import Fund, Strategy
from app.utils.data_pipeline_client import DataPipelineClient
from app.utils.ai_analyst_client import AIAnalystClient
from app.utils.redis_client import get_redis_client

logger = logging.getLogger(__name__)

class CorrelationService:
    """
    [PHASE 40] AI Sentiment Correlation Service.
    Calculates PCA-based asset correlation loadings using AI Analyst.
    """
    def __init__(self):
        self.pipeline_client = DataPipelineClient()
        self.ai_client = AIAnalystClient()

    async def update_all_correlations(self):
        """
        Main entry point to update correlation data for all active funds.
        """
        logger.info("📊 [CorrelationService] Starting global correlation update...")
        async with AsyncSessionLocal() as db:
            # 1. Fetch all active funds
            stmt = select(Fund).where(Fund.risk_parity_enabled == True)
            result = await db.execute(stmt)
            funds = result.scalars().all()
            
            if not funds:
                logger.info("📊 [CorrelationService] No funds with Risk Parity enabled found.")
                return

            for fund in funds:
                try:
                    await self.update_fund_correlation(db, fund)
                except Exception as e:
                    logger.error(f"📊 [CorrelationService] Failed to update correlation for Fund {fund.name} ({fund.id}): {e}", exc_info=True)

    async def update_fund_correlation(self, db, fund: Fund):
        """
        Update correlation data for a specific fund.
        """
        logger.info(f"📊 [CorrelationService] Updating correlation for Fund: {fund.name} ({fund.id})")
        
        # 1. Identify active strategies and their symbols
        stmt = select(Strategy).where(Strategy.fund_id == fund.id, Strategy.is_active == True)
        result = await db.execute(stmt)
        strategies = result.scalars().all()
        
        if not strategies:
            logger.warning(f"📊 [CorrelationService] No active strategies found for Fund {fund.name}.")
            return

        symbols = list(set([s.config_json.get("symbol") for s in strategies if s.config_json.get("symbol")]))
        if len(symbols) < 2:
             logger.info(f"📊 [CorrelationService] Insufficient symbols (< 2) for correlation in Fund {fund.name}.")
             return

        # 2. Fetch Historical Price Data (D1 for PCA)
        prices_payload = {}
        for sym in symbols:
            candles = await self.pipeline_client.get_candles(sym, "D1", limit=60) # 60 days
            if candles:
                prices_payload[sym] = [float(c['close']) for c in candles]
        
        if len(prices_payload) < 2:
            logger.error(f"📊 [CorrelationService] Could not fetch sufficient price history for {fund.name}.")
            return

        # 3. Call AI Analyst for PCA Correlation
        logger.info(f"📊 [CorrelationService] Requesting PCA analysis for {len(prices_payload)} symbols...")
        analysis = await self.ai_client.get_correlation_analysis(prices_payload)
        
        if analysis.get("status") == "error":
            logger.error(f"📊 [CorrelationService] AI Analyst error for {fund.name}: {analysis.get('reason')}")
            return

        # 4. Persistence (Redis)
        # Store the entire analysis result for the RiskParityEngine to consume
        rc = get_redis_client()
        redis_key = f"fund:{fund.id}:correlation_stats"
        await rc.set(redis_key, json.dumps(analysis), ex=86400 * 2) # 2 day TTL
        
        logger.info(f"✅ [CorrelationService] Fund {fund.name} correlation stats updated. Systemic Alert: {analysis.get('systemic_alert')}")
