import logging
import asyncio
import json
from datetime import datetime, timezone
from typing import List, Dict, Any
from app.adapters.oanda import OandaClient
from app.adapters.ctrader import CTraderClient
from app.streaming.publisher import RedisPublisher
import redis.asyncio as redis
from app.core.config import settings

logger = logging.getLogger(__name__)

class SyncService:
    @classmethod
    async def run_broker_sync(cls):
        """
        Job to synchronize and detect drifts between OANDA and cTrader.
        """
        logger.info("📡 [SyncService] Starting Broker State Synchronization...")
        
        try:
            # 1. Fetch OANDA state
            oanda = OandaClient()
            # In data-pipeline, oanda.get_open_positions() is sync
            oanda_trades = await asyncio.to_thread(oanda.get_open_positions)
            
            # 2. Fetch cTrader state
            ctrader = CTraderClient()
            ctrader_trades = await ctrader.get_open_positions()
            
            # 3. Detect Cross-Broker Drift
            await cls._check_cross_broker_drift(oanda_trades, ctrader_trades)
            
        except Exception as e:
            logger.error(f"📡 [SyncService] Sync job failed: {e}")

    @classmethod
    async def _check_cross_broker_drift(cls, oanda_trades: List[dict], ctrader_trades: List[dict]):
        redis_url = getattr(settings, "REDIS_URL", "redis://redis:6379/0")
        redis_client = redis.from_url(redis_url, decode_responses=True)
        
        try:
            # Calculate net exposure per symbol
            exposure: Dict[str, Dict[str, float]] = {} # symbol -> {broker -> units}
            
            for t in oanda_trades:
                # OANDA symbol is XAU_USD or instrument
                symbol = t.get("instrument", "").replace("_", "")
                units = float(t.get("currentUnits", 0))
                if symbol not in exposure: exposure[symbol] = {}
                exposure[symbol]["OANDA"] = exposure[symbol].get("OANDA", 0) + units
                
            for t in ctrader_trades:
                symbol = t.get("symbol", "").replace("_", "").replace("/", "")
                units = float(t.get("units", 0))
                if symbol not in exposure: exposure[symbol] = {}
                exposure[symbol]["CTRADER"] = exposure[symbol].get("CTRADER", 0) + units
                
            # Detect drifts
            for symbol, brokers in exposure.items():
                oanda_exp = brokers.get("OANDA", 0.0)
                ct_exp = brokers.get("CTRADER", 0.0)
                
                drift = abs(oanda_exp - ct_exp)
                if drift > 0.0001: # Threshold
                    msg = f"⚖️ [DRIFT] {symbol}: OANDA={oanda_exp}, cTrader={ct_exp} | Drift={drift}"
                    logger.warning(msg)
                    
                    alert = {
                        "type": "BROKER_DRIFT",
                        "symbol": symbol,
                        "oanda_units": oanda_exp,
                        "ctrader_units": ct_exp,
                        "drift": drift,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    await redis_client.xadd("system.alerts.drift", {"payload": json.dumps(alert)})
        finally:
            await redis_client.close()

sync_service = SyncService()
