
import logging
import json
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime
from redis.asyncio import Redis
import aiohttp
from scipy import stats
from app.core.config import settings

logger = logging.getLogger(__name__)

class EquityCurveProjections:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.curve_key_prefix = "equity_guardian:curve:"
        self.metrics_key_prefix = "equity_guardian:metrics:"

    async def get_curve(self, account_id: str) -> pd.DataFrame:
        """Fetch equity curve from Redis."""
        key = f"{self.curve_key_prefix}{account_id}"
        # LRANGE 0 -1 to get all
        raw_data = await self.redis.lrange(key, 0, -1)
        if not raw_data:
            return pd.DataFrame()
        
        # Parse JSON
        records = [json.loads(d) for d in raw_data]
        df = pd.DataFrame(records)
        if not df.empty:
             df['timestamp'] = pd.to_datetime(df['timestamp'])
             df.sort_values('timestamp', inplace=True)
        return df

    async def update_curve(self, trade: dict):
        """Append a new trade to the equity curve."""
        account_id = trade.get("account_id") or trade.get("broker_account_id")
        if not account_id:
            # logger.error(f"Cannot update curve: trade missing account_id: {trade}")
            # Silently ignore if not relevant context
            return
            
        key = f"{self.curve_key_prefix}{account_id}"
        
        entry = {
            "timestamp": trade.get("close_time", datetime.utcnow().isoformat()),
            "pnl": float(trade.get("pnl") or trade.get("pnl_usd", 0.0)),
            "id": trade.get("id") or trade.get("trade_id")
        }
        
        await self.redis.rpush(key, json.dumps(entry))
        # Trim to keep last 5000 trades
        await self.redis.ltrim(key, -5000, -1)

    async def hydrate(self, account_id: str):
        """Fetch full history from API Gateway."""
        logger.info(f"Hydrating Equity Curve for {account_id}...")
        url = f"{settings.API_GATEWAY_URL}/trades"
        params = {
            "broker_account_id": account_id,
            "per_page": 5000,
            "status": "CLOSED" 
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                 async with session.get(url, params=params) as resp:
                     if resp.status == 200:
                         data = await resp.json()
                         trades = data.get("data", [])
                         
                         # Clear existing
                         key = f"{self.curve_key_prefix}{account_id}"
                         await self.redis.delete(key)
                         
                         # Sort by time asc
                         trades.sort(key=lambda x: x['exit_timestamp'] or x['signal_timestamp'])
                         
                         pipeline = self.redis.pipeline()
                         for t in trades:
                             entry = {
                                 "timestamp": t['exit_timestamp'] or t['signal_timestamp'],
                                 "pnl": float(t.get('pnl_usd') or 0.0),
                                 "id": str(t['trade_id'])
                             }
                             pipeline.rpush(key, json.dumps(entry))
                         
                         await pipeline.execute()
                         logger.info(f"Hydration complete. Loaded {len(trades)} trades.")
                     else:
                         logger.error(f"Failed to hydrate: {await resp.text()}")
        except Exception as e:
            logger.error(f"Hydration error: {e}")

class EquityGuardian:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.projections = EquityCurveProjections(redis_client)

    async def check_health(self):
        """Standard entry point for Scheduler."""
        logger.info("Equity Guardian: Health Check Started...")
        
        # Fetch active accounts
        try:
            async with aiohttp.ClientSession() as session:
                 url = f"{settings.API_GATEWAY_URL}/accounts"
                 async with session.get(url) as resp:
                     if resp.status == 200:
                         res = await resp.json()
                         accounts = res.get("data", [])
                         
                         for acc in accounts:
                             await self.analyze(acc['id'])
        except Exception as e:
            logger.error(f"Health check failed: {e}")

    def _calculate_metrics(self, df: pd.DataFrame) -> dict:
        """
        Synchronous, CPU-bound calculation of equity metrics.
        Executed in a thread pool to avoid blocking the event loop.
        """
        if df.empty or len(df) < 5:
            return None

        # Equity Curve
        df['equity'] = df['pnl'].cumsum()
        
        # K-Ratio
        y = df['equity'].values
        x = np.arange(len(y))
        
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        r_squared = r_value ** 2
        
        if std_err == 0:
            k_ratio = 0
        else:
            k_ratio = slope / std_err
            
        # Drawdown
        rolling_max = df['equity'].cummax()
        drawdown = df['equity'] - rolling_max
        max_drawdown = drawdown.min()
        
        return {
            "updated_at": datetime.utcnow().isoformat(),
            "k_ratio": k_ratio,
            "r_squared": r_squared,
            "max_drawdown": max_drawdown,
            "total_pnl": float(df['equity'].iloc[-1]),
            "trade_count": len(df)
        }

    async def analyze(self, account_id: str):
        """Analyze equity curve stability and store metrics."""
        
        # 1. Hydrate if empty
        df = await self.projections.get_curve(account_id)
        if df.empty:
            await self.projections.hydrate(account_id)
            df = await self.projections.get_curve(account_id)
            
        if df.empty or len(df) < 5:
            return

        # 2. Offload heavy calculations to thread pool
        metrics = await asyncio.to_thread(self._calculate_metrics, df)
        
        if metrics:
            key = f"{self.projections.metrics_key_prefix}{account_id}"
            await self.redis.set(key, json.dumps(metrics))
            logger.info(f"Analyzed {account_id}: K-Ratio={metrics['k_ratio']:.2f}, R2={metrics['r_squared']:.2f}, DD={metrics['max_drawdown']:.2f}")
