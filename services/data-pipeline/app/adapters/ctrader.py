import logging
import pandas as pd
from typing import List, Optional
from datetime import datetime
from app.core.config import settings
from app.adapters.ctrader_client import AsyncCTraderClient
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOATrendbarPeriod

from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOAGetTrendbarsReq, ProtoOAGetTrendbarsRes

logger = logging.getLogger(__name__)

class CTraderClient:
    def __init__(self, 
                 client_id: Optional[str] = None, 
                 client_secret: Optional[str] = None,
                 account_id: Optional[str] = None,
                 token: Optional[str] = None,
                 host: Optional[str] = None,
                 port: Optional[int] = None):
        
        # Priority: Arguments -> Settings -> Defaults
        self.host = host or getattr(settings, "CTRADER_HOST", "demo.ctraderapi.com")
        self.port = port or int(getattr(settings, "CTRADER_PORT", 5035))
        self.client_id = client_id or getattr(settings, "CTRADER_CLIENT_ID", "")
        self.client_secret = client_secret or getattr(settings, "CTRADER_CLIENT_SECRET", "")
        self.account_id = int(account_id) if account_id else int(getattr(settings, "CTRADER_ACCOUNT_ID", 0))
        self.token = token or getattr(settings, "CTRADER_TOKEN", "")
        
        if not self.client_id:
             logger.warning("CTRADER_CLIENT_ID not set in settings or arguments.")

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

    async def fetch_trade_history(self, start_date: datetime, end_date: datetime) -> List[dict]:
        """
        Fetch historical trades (Deals) from cTrader within the specified range.
        """
        if not self.client_id:
            raise ValueError("cTrader credentials not configured")
            
        client = AsyncCTraderClient(self.host, self.port)
        try:
            await client.connect()
            await client.authorize_app(self.client_id, self.client_secret)
            await client.authorize_account(self.account_id, self.token)
            
            # Convert dates to milliseconds
            from_ts = int(start_date.timestamp() * 1000)
            to_ts = int(end_date.timestamp() * 1000)
            
            # Fetch Deals
            deals = await client.get_deal_list(self.account_id, from_ts, to_ts)
            
            # Extract unique Symbol IDs from deals
            deal_symbol_ids = set([d.symbolId for d in deals])
            symbol_map = {}
            
            if deal_symbol_ids:
                # Resolve symbols from Database first (primary source for consistency)
                try:
                    import asyncio
                    from app.database import SessionLocal
                    from app.models.market import MarketSymbol
                    from sqlalchemy import select
                    
                    def fetch_symbols_sync(ids):
                        with SessionLocal() as db:
                            # Fetch all symbols or filter by IDs if possible
                            # Ideally we want to filter, but details is JSONB.
                            # Fetching all is safer for now given volume.
                            res = db.execute(select(MarketSymbol))
                            all_syms = res.scalars().all()
                            
                            mapped = {}
                            for s in all_syms:
                                if not s.details: continue
                                sid = s.details.get("symbolId")
                                if not sid and "raw" in s.details:
                                    sid = s.details["raw"].get("symbolId")
                                
                                if sid and int(sid) in ids:
                                    mapped[int(sid)] = s
                            return mapped

                    # Run sync DB query in thread
                    symbol_map = await asyncio.to_thread(fetch_symbols_sync, deal_symbol_ids)
                            
                except Exception as db_e:
                    logger.error(f"Failed to resolve symbols from DB: {db_e}")
                    pass

                # Fallback to API for missing symbols
                missing_ids = [sid for sid in deal_symbol_ids if sid not in symbol_map]
                if missing_ids:
                     try:
                         full_symbols = await client.get_symbols_full(self.account_id, missing_ids)
                         for fs in full_symbols:
                             symbol_map[fs.symbolId] = fs # These are ProtoOASymbols, not MarketSymbol models
                     except Exception as api_e:
                         logger.error(f"Failed to fetch symbols from API: {api_e}")

            results = []
            for d in deals:
                if d.closePositionDetail:
                    sym_entity = symbol_map.get(d.symbolId)
                    
                    s_name = f"Unknown_{d.symbolId}"
                    digits = 5
                    
                    if sym_entity:
                        # Check if it's a DB Model (MarketSymbol) or Proto Obj
                        if hasattr(sym_entity, "symbol"): # MarketSymbol
                            s_name = sym_entity.symbol
                        else: # ProtoOASymbol
                            s_name = getattr(sym_entity, "symbolName", getattr(sym_entity, "name", f"Unknown_{d.symbolId}"))
                    
                    money_divisor = 100.0 # Cents to Units
                    
                    # ProtoOADeal prices are usually already normalized doubles.
                    # We do NOT divide by digits.
                    entry_p = d.closePositionDetail.entryPrice if d.closePositionDetail.entryPrice else 0.0
                    exit_p = d.executionPrice if d.executionPrice else 0.0
                    
                    gross_profit = d.closePositionDetail.grossProfit / money_divisor
                    # Comm/Swap are usually negative in cents.
                    commission = d.commission / money_divisor if d.commission else 0
                    swap = d.closePositionDetail.swap / money_divisor if d.closePositionDetail.swap else 0
                    net_pnl = gross_profit + commission + swap
                    
                    # Direction: If we SOLD to close, we were LONG.
                    # TradeSide: BUY=1, SELL=2
                    from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOATradeSide
                    direction = "LONG" if d.tradeSide == ProtoOATradeSide.SELL else "SHORT"
                    
                    # Volume is in cents. Units = volume / 100.
                    units = d.volume / 100.0
                    
                    # We treat 'lot_size' as units because 'Standard Lot' depends on symbol
                    # If we want standard lots, we need lotSize from symbol entity.
                    # ProtoOASymbol has 'lotSize'? No. It has 'stepVolume'?
                    # Usually 1 Lot = 100,000 units for FX.
                    # We will store UNITS in lot_size for consistency with execution service logic or 
                    # we can try to normalize. 
                    # Let's check `execution` service implementation again? 
                    # It used `d.volume / 100.0`. So "units".
                    
                    results.append({
                        "trade_id": str(d.dealId), # Unique ID for this deal
                        "broker_trade_id": str(d.positionId), # Link to Position
                        "broker_deal_id": str(d.dealId),
                        "symbol": s_name,
                        "strategy_name": "Imported", # Default
                        "signal_timestamp": datetime.fromtimestamp(d.createTimestamp / 1000.0),
                        "status": "CLOSED",
                        "direction": direction,
                        "entry_price": entry_p,
                        "exit_price": exit_p,
                        "sl_price": 0.0, # Not easily available in Deal
                        "tp_price": 0.0,
                        "lot_size": units, 
                        "risk_usd": 0.0, # Unknown from history
                        "commission": commission,
                        "swap": swap,
                        "gross_pnl": gross_profit,
                        "pnl_usd": net_pnl,
                        "exit_timestamp": datetime.fromtimestamp(d.executionTimestamp / 1000.0),
                        "metadata_json": {
                            "deal_id": str(d.dealId), 
                            "position_id": str(d.positionId),
                            "commission": commission,
                            "swap": swap,
                            "gross_pnl": gross_profit,
                            "raw_symbol_id": d.symbolId
                        }
                    })
                    
            return results
            
        except Exception as e:
            logger.error(f"Fetch trade history error: {e}")
            # Don't raise, just return empty list to avoid crashing pipeline?
            # Or raise to retry?
            # Raise to retry in job.
            raise e
        finally:
            await client.disconnect()
