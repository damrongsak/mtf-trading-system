import asyncio
import logging
import pandas as pd
from datetime import datetime
from typing import List, Optional
from app.models.data_source import DataSource
from app.database import SessionLocal
from app.adapters.ctrader_client import AsyncCTraderClient
from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import ProtoOATrendbarPeriod
from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOAGetTrendbarsReq, ProtoOAGetTrendbarsRes

logger = logging.getLogger(__name__)

class CTraderAdapter:
    def __init__(self, data_source_id: str):
        self.db = SessionLocal()
        self.data_source = self.db.query(DataSource).filter(DataSource.id == data_source_id).first()
        if not self.data_source:
            raise ValueError(f"DataSource {data_source_id} not found")
        
        self.config = self.data_source.config_json
        self.host = self.config.get("host", "demo.ctraderapi.com")
        self.port = int(self.config.get("port", 5035))
        self.client_id = self.config.get("client_id")
        self.client_secret = self.config.get("client_secret")
        self.account_id = int(self.config.get("account_id"))
        self.token = self.config.get("token")
        
        if not all([self.client_id, self.client_secret, self.account_id, self.token]):
            raise ValueError("Incomplete cTrader configuration (client_id, client_secret, account_id, token required)")

    async def _fetch_candles_async(self, symbol_id: int, timeframe: str, count: int) -> List[dict]:
        client = AsyncCTraderClient(self.host, self.port)
        try:
            await client.connect()
            await client.authorize_app(self.client_id, self.client_secret)
            await client.authorize_account(self.account_id, self.token)
            
            # Map Timeframe
            period = self._map_timeframe(timeframe)
            
            # Send Request
            req = ProtoOAGetTrendbarsReq()
            req.ctidTraderAccountId = self.account_id
            req.period = period
            req.symbolId = symbol_id # Need numeric Symbol ID!
            req.count = count
            # req.fromTimestamp = ... # Optional, defaults to latest if count used? 
            # Actually cTrader usually takes 'from' and 'to'. If count is used it might imply range from now?
            # Looking at protobuf: optional fromTimestamp, optional toTimestamp, optional count.
            # Usually we provide 'from' or 'to'.
            
            # For "latest N candles", we might not easily support 'count' without knowing current server time or using from=0 to=now?
            # Let's set toTimestamp = now
            # req.toTimestamp = int(datetime.utcnow().timestamp() * 1000)
            
            resp = await client.send(req)
            
            if resp.payloadType == ProtoOAGetTrendbarsRes().payloadType:
                res_payload = ProtoOAGetTrendbarsRes()
                res_payload.ParseFromString(resp.payload)
                
                candles = []
                # cTrader uses delta encoded prices for OHLC relative to previous? 
                # Check Protobuf definition:
                # int64 deltaOpen = 3; uint64 deltaHigh = 4; uint64 deltaLow = 5; int64 deltaClose = 6;
                # We need to decode them. The first candle is absolute (or relative to what?)
                # Wait, ProtoOATrendbar has:
                # low = (low(i-1) + deltaLow) ? No.
                # Usually: Open is absolute for first?
                # Actually, documentation says internal representation is compact.
                # We might need a utility to decode.
                
                # For MVP, assume unscaled long values and we need to convert to float (price = value / 100000 or digits).
                # We need 'digits' or 'pipPosition' from symbol entity to normalize.
                # This complexity suggests we really need the Symbol Entity metadata first (ProtoOASymbol).
                
                # MVP Shortcut: Just return raw/partial for now or check if we can get symbol details first.
                return [] 
                
            else:
                logger.error(f"Unexpected response for trendbars: {resp.payloadType}")
                return []
                
        finally:
            await client.disconnect()

    def fetch_candles(self, symbol: str, timeframe: str, count: int = 500) -> List[dict]:
        """
        Synchronous wrapper for fetching candles.
        Note: 'symbol' here is the string name (e.g. 'EURUSD'). cTrader needs numeric ID.
        We need to lookup numeric ID from our DB (if we stored it) or fetch it from cTrader (GetSymbols).
        This implies a mapping step is missing.
        """
        # TODO: Implement Symbol Name -> ID Lookup
        # For now, this is a placeholder stub as we need the Symbol Map.
        logger.warning("fetch_candles not fully implemented without Symbol ID map")
        return []

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
