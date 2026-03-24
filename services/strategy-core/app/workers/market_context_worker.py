import asyncio
import logging
import json
import os
from typing import Dict, Any, Optional
import pandas as pd
from sqlalchemy import text
import redis.asyncio as redis
from datetime import datetime, timezone

from app.database import SessionLocal
from app.models.market import MarketSymbol
from app.indicators.garch_engine import garch_engine
from app.quant.engine import quant_engine
from app.utils.scheduler_utils import tracing_context
from app.utils.redis_client import get_redis_client

logger = logging.getLogger(__name__)

class MarketContextWorker:
    """
    Background worker that periodically computes advanced market context (PIV, Quant, Liquidity)
    and broadcasts it to Redis for the Execution service to consume at HFT speeds (Phase 2).
    """
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        self.redis = None
        self.running = False
        self.interval_seconds = 300  # Update context every 5 minutes (aligned with ingestion)
        self.symbol_cache: Dict[str, Any] = {}
        
    async def start(self):
        self.running = True
        self.redis = get_redis_client()
        logger.info(f"MarketContextWorker connected to Global Redis Pool")
        
        asyncio.create_task(self._loop())

    async def stop(self):
        self.running = False
        # Managed by global pool
        pass

    async def _refresh_cache(self):
        try:
            db = SessionLocal()
            try:
                symbols = db.query(MarketSymbol).filter(MarketSymbol.is_active == True).all()
                self.symbol_cache = {s.symbol: s.id for s in symbols}
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to refresh symbol cache in MarketContextWorker: {e}")

    async def _loop(self):
        logger.info("MarketContextWorker loop started.")
        while self.running:
            try:
                await asyncio.to_thread(self._refresh_cache)
                for symbol, market_symbol_id in self.symbol_cache.items():
                    async with tracing_context(f"worker-context-{symbol}"):
                        # Process each symbol concurrently or simply sequentially
                        await self._process_symbol(symbol, market_symbol_id)
            except Exception as e:
                logger.error(f"MarketContextWorker loop error: {e}")
            
            await asyncio.sleep(self.interval_seconds)

    async def _process_symbol(self, symbol: str, market_symbol_id: Any):
        context = await asyncio.to_thread(self._compute_context_sync, symbol, market_symbol_id)
        if context:
            # Broadcast to Redis
            key = f"mtf:market_context:{symbol}"
            # Cache for slightly longer than interval to allow brief overlaps
            await self.redis.setex(key, self.interval_seconds * 2, json.dumps(context))
            logger.debug(f"Pushed Market Context to {key}")

    def _compute_context_sync(self, symbol: str, market_symbol_id: Any) -> Optional[Dict[str, Any]]:
        db = SessionLocal()
        try:
            # Fetch last 300 H1 candles for GARCH & Quant engine
            query = text("""
                SELECT timestamp, close, open, high, low, volume 
                FROM candles 
                WHERE market_symbol_id = :market_symbol_id
                AND timeframe = 'H1'
                ORDER BY timestamp DESC
                LIMIT 300
            """)
            
            df = pd.read_sql(query, db.bind, params={
                "market_symbol_id": market_symbol_id
            })
            
            if len(df) < 50:
                logger.warning(f"Not enough H1 data for {symbol} Context (<50 candles)")
                return None
                
            df = df.sort_values("timestamp").reset_index(drop=True)
            
            # --- 1. Compute PIV (Projected Implied Volatility via GARCH) ---
            returns = df['close'].pct_change().dropna()
            try:
                piv_volatility = garch_engine.get_projected_volatility(returns)
            except Exception as e:
                logger.warning(f"GARCH calculation failed for {symbol}: {e}")
                piv_volatility = 0.0
                
            # --- 2. Compute Quant Risk Map ---
            try:
                quant_risk = quant_engine.analyze(symbol, df, "H1")
            except Exception as e:
                logger.warning(f"Quant calculation failed for {symbol}: {e}")
                quant_risk = {"error": str(e), "risk_score": 50, "regime": "UNKNOWN"}

            # --- 3. Compile Context ---
            return {
                "symbol": symbol,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "piv": {
                    "volatility": float(piv_volatility),
                    "model": "GJR-GARCH"
                },
                "quant": quant_risk,
                "liquidity": {
                    "regime": "UNKNOWN", # Placeholder for actual OI LiquidityProfileAnalyzer 
                    "gamma_flip": None
                }
            }
            
        except Exception as e:
            logger.error(f"Context compute error for {symbol}: {e}")
            return None
        finally:
            db.close()

context_worker = MarketContextWorker()
