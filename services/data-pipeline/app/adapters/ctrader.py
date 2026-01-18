import logging
import pandas as pd
from typing import List, Optional
from datetime import datetime
from app.core.config import settings
from app.adapters.ctrader_client import AsyncCTraderClient
from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import ProtoOATrendbarPeriod
from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOAGetTrendbarsReq, ProtoOAGetTrendbarsRes

logger = logging.getLogger(__name__)

class CTraderClient:
    def __init__(self):
        # In data-pipeline, we might use settings or a config dict from DataSource.
        # Assuming settings based on Oanda pattern, or we need to pass config.
        # OandaClient uses settings.OANDA_API_KEY.
        # We should probably add CTRADER settings to `app.core.config` or pass them.
        self.host = getattr(settings, "CTRADER_HOST", "demo.ctraderapi.com")
        self.port = int(getattr(settings, "CTRADER_PORT", 5035))
        self.client_id = getattr(settings, "CTRADER_CLIENT_ID", "")
        self.client_secret = getattr(settings, "CTRADER_CLIENT_SECRET", "")
        self.account_id = int(getattr(settings, "CTRADER_ACCOUNT_ID", 0))
        self.token = getattr(settings, "CTRADER_TOKEN", "")
        
        if not self.client_id:
             logger.warning("CTRADER_CLIENT_ID not set in settings.")

    async def fetch_candles(self, symbol: str, timeframe: str, count: int = 500) -> List[dict]:
        if not self.client_id:
            raise ValueError("cTrader credentials not configured")
            
        client = AsyncCTraderClient(self.host, self.port)
        try:
            await client.connect()
            await client.authorize_app(self.client_id, self.client_secret)
            await client.authorize_account(self.account_id, self.token)
            
            # Map Symbol -> ID
            # This is expensive to do every time. Better to cache.
            # For data pipeline ingestion (scheduled job), we can afford one call or modify this to be more stateful.
            symbols_list = await client.get_symbols_list(self.account_id)
            symbol_id = None
            clean_sym = symbol.replace("/", "").replace("_", "")
            for s in symbols_list:
                if s.symbolName == symbol or s.symbolName == clean_sym:
                    symbol_id = s.symbolId
                    break
            
            if not symbol_id:
                raise ValueError(f"Symbol {symbol} not found")

            # Map Timeframe
            period = self._map_timeframe(timeframe)
            
            req = ProtoOAGetTrendbarsReq()
            req.ctidTraderAccountId = self.account_id
            req.period = period
            req.symbolId = symbol_id
            req.count = count
            
            # Use current time as end?
            # req.toTimestamp = int(datetime.utcnow().timestamp() * 1000) 

            resp = await client.send(req)
            
            if resp.payloadType == ProtoOAGetTrendbarsRes().payloadType:
                res_payload = ProtoOAGetTrendbarsRes()
                res_payload.ParseFromString(resp.payload)
                
                # Decode Logic (Simplified)
                # Trendbar properties are delta encoded?
                # Actually, the Trendbar message itself has low, deltaHigh, deltaOpen, deltaClose.
                # All are relative to low? Or relative to previous bar?
                # Documentation:
                # low: int64 (absolute)
                # deltaOpen: int64 (relative to low) -> open = low + deltaOpen
                # deltaHigh: uint64 (relative to low) -> high = low + deltaHigh
                # deltaClose: int64 (relative to low) -> close = low + deltaClose
                # The values are in "points". Need to divide by 10^digits.
                # Without digits, we have raw points.
                
                # We need digits. Can get from symbol list entity (digits field).
                digits = 5 # Default assumption for Forex?
                # Find symbol entity again
                for s in symbols_list:
                     if s.symbolId == symbol_id:
                         digits = s.digits
                         break
                
                divisor = 10 ** digits
                
                candles = []
                for b in res_payload.trendbar:
                    low = b.low
                    open_p = low + b.deltaOpen
                    high_p = low + b.deltaHigh
                    close_p = low + b.deltaClose
                    
                    candles.append({
                        # timestamp in cTrader is minutes/timestamp?
                        # It has 'timestamp' field? No. it has 'utcTimestampInMinutes'?
                        # Actually ProtoOATrendbar has no timestamp field directly inside the repeated delta?
                        # Wait, cTrader Trendbars might be a list.
                        # ProtoOATrendbar:
                        # optional int64 volume = 1;
                        # optional int64 period = 2; ?
                        # optional int64 low = 3;
                        # optional uint64 deltaOpen = 4;
                        # ...
                        # optional uint64 utcTimestampInMinutes = 7;
                        
                        "timestamp": datetime.fromtimestamp(b.utcTimestampInMinutes * 60) if b.utcTimestampInMinutes else datetime.now(),
                        "open": open_p / divisor,
                        "high": high_p / divisor,
                        "low": low / divisor,
                        "close": close_p / divisor,
                        "volume": b.volume # Volume in cents/units?
                    })
                return candles
            else:
                logger.error(f"Unexpected response: {resp.payloadType}")
                return []
        
        except Exception as e:
            logger.error(f"Fetch candles error: {e}")
            raise
        finally:
            await client.disconnect()

    def _map_timeframe(self, tf: str):
        mapping = {
            "M1": ProtoOATrendbarPeriod.M1,
            "M5": ProtoOATrendbarPeriod.M5,
            "M15": ProtoOATrendbarPeriod.M15,
            "H1": ProtoOATrendbarPeriod.H1,
            "H4": ProtoOATrendbarPeriod.H4,
            "D1": ProtoOATrendbarPeriod.D1,
        }
        return mapping.get(tf, ProtoOATrendbarPeriod.H1)
