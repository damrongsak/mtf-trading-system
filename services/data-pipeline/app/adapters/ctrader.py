import logging
import pandas as pd
from typing import List, Optional
from datetime import datetime
from app.core.config import settings
from app.utils.crypto import decrypt_data, encrypt_data
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
            try:
                await client.authorize_account(self.account_id, self.token)
            except Exception as e:
                if "CH_ACCESS_TOKEN_INVALID" in str(e):
                    logger.warning(f"cTrader token expired for account {self.account_id}. Attempting refresh...")
                    new_token = await self._refresh_token_and_update_db(client)
                    if new_token:
                        self.token = new_token
                        await client.authorize_account(self.account_id, self.token)
                    else:
                        raise e
                else:
                    raise e
            
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
            
            # Use current time as end
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            req.toTimestamp = now_ms

            # MUST provide fromTimestamp if required by the OpenAPI spec/broker
            if count:
                # Timeframe multiplication for count (in seconds)
                m_map = {
                    "M1": 60, "M5": 300, "M15": 900, "M30": 1800,
                    "H1": 3600, "H4": 14400, "D1": 86400, "W1": 604800, "MN1": 2592000
                }
                # Use timeframe string instead of period int
                offset_sec = count * m_map.get(timeframe, 60)
                # Ensure we look back far enough (add 20% buffer for missing candles/weekends)
                req.fromTimestamp = now_ms - (int(offset_sec * 1.2) * 1000)
            else:
                # Fallback to 1 week if no count
                req.fromTimestamp = now_ms - (7 * 86400 * 1000)

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
                    low_raw = b.low
                    
                    # Heuristic: If delta is suspicious (e.g. > 50% of low), treat as absolute.
                    # This happens on some cTrader broker feeds where deltaOpen is actually Open price.
                    if b.deltaOpen > (low_raw * 0.5):
                        open_p = b.deltaOpen
                        high_p = b.deltaHigh
                        close_p = b.deltaClose
                    else:
                        open_p = low_raw + b.deltaOpen
                        high_p = low_raw + b.deltaHigh
                        close_p = low_raw + b.deltaClose
                    
                    open_p_norm = open_p / divisor
                    high_p_norm = high_p / divisor
                    low_p_norm = low_raw / divisor
                    close_p_norm = close_p / divisor

                    # cTrader Gold Quirk: Some feeds send doubled price (likely Bid+Ask aggregate)
                    # If the price is > 3500 for Gold, it's likely doubled (market is ~2400-2600)
                    if close_p_norm > 3500:
                        open_p_norm /= 2.0
                        high_p_norm /= 2.0
                        low_p_norm /= 2.0
                        close_p_norm /= 2.0

                    candles.append({
                        "timestamp": datetime.fromtimestamp(b.utcTimestampInMinutes * 60) if b.utcTimestampInMinutes else datetime.now(),
                        "open": open_p_norm,
                        "high": high_p_norm,
                        "low": low_p_norm,
                        "close": close_p_norm,
                        "volume": b.volume
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
            "W1": ProtoOATrendbarPeriod.W1,
            "MN1": ProtoOATrendbarPeriod.MN1,
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
            try:
                await client.authorize_account(self.account_id, self.token)
            except Exception as e:
                if "CH_ACCESS_TOKEN_INVALID" in str(e):
                    logger.warning(f"cTrader token expired for account {self.account_id}. Attempting refresh...")
                    new_token = await self._refresh_token_and_update_db(client)
                    if new_token:
                        self.token = new_token
                        await client.authorize_account(self.account_id, self.token)
                    else:
                        raise e
                else:
                    raise e
            
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
                if d.HasField('closePositionDetail'):
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
                    
                    # Normalizing Lot Size
                    # cTrader volume is in "cents" (units * 100)
                    units = d.volume / 100.0
                    lot_size_divisor = 100000.0 # Default for FX
                    
                    if sym_entity:
                        # Check if it's a DB Model (MarketSymbol)
                        if hasattr(sym_entity, "details") and sym_entity.details:
                            lot_size_divisor = float(sym_entity.details.get("lotSize", 10000000.0)) / 100.0
                        # Check if it's a ProtoOASymbol
                        elif hasattr(sym_entity, "lotSize"):
                            lot_size_divisor = float(sym_entity.lotSize) / 100.0
                    
                    normalized_lots = units / lot_size_divisor if lot_size_divisor > 0 else units
                    
                    results.append({
                        "trade_id": str(d.dealId), # Unique ID for this deal
                        "broker_trade_id": str(d.positionId), # Link to Position
                        "broker_deal_id": str(d.dealId),
                        "symbol": s_name,
                        "strategy_name": "Imported", # Default
                        "signal_timestamp": datetime.fromtimestamp(d.createTimestamp / 1000.0),
                        "status": "CLOSED",
                        "direction": "LONG" if d.tradeSide == ProtoOATradeSide.SELL else "SHORT", # If we SELL to close, we were LONG
                        "entry_price": entry_p,
                        "exit_price": exit_p,
                        "sl_price": 0.0, # Not easily available in Deal
                        "tp_price": 0.0,
                        "lot_size": normalized_lots, 
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

    async def get_open_positions(self) -> List[dict]:
        """
        Fetch all open positions from cTrader.
        """
        if not self.client_id:
            raise ValueError("cTrader credentials not configured")
            
        client = AsyncCTraderClient(self.host, self.port)
        try:
            await client.connect()
            await client.authorize_app(self.client_id, self.client_secret)
            try:
                await client.authorize_account(self.account_id, self.token)
            except Exception as e:
                if "CH_ACCESS_TOKEN_INVALID" in str(e):
                    logger.warning(f"cTrader token expired for account {self.account_id}. Attempting refresh...")
                    new_token = await self._refresh_token_and_update_db(client)
                    if new_token:
                        self.token = new_token
                        await client.authorize_account(self.account_id, self.token)
                    else:
                        raise e
                else:
                    raise e
            
            # Use get_reconcile to fetch positions
            reconcile = await client.get_reconcile(self.account_id)
            
            if not hasattr(reconcile, 'position') or not reconcile.position:
                return []
                
            # Fetch symbols for naming
            symbols_list = await client.get_symbols_list(self.account_id)
            sym_map = {s.symbolId: s.symbolName for s in symbols_list}
            
            results = []
            for p in reconcile.position:
                from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOATradeSide
                
                s_name = sym_map.get(p.tradeData.symbolId, f"Unknown_{p.tradeData.symbolId}")
                units = p.tradeData.volume / 100.0 # cents to units
                
                results.append({
                    "id": str(p.positionId),
                    "broker_trade_id": str(p.positionId),
                    "symbol": s_name,
                    "units": units if p.tradeData.tradeSide == ProtoOATradeSide.BUY else -units,
                    "price": float(p.price) if hasattr(p, 'price') else 0.0,
                    "sl": float(p.stopLoss) if p.HasField("stopLoss") else None,
                    "tp": float(p.takeProfit) if p.HasField("takeProfit") else None,
                    "pnl": float(p.grossProfit) / 100.0 if p.HasField("grossProfit") else 0.0,
                    "side": "BUY" if p.tradeData.tradeSide == ProtoOATradeSide.BUY else "SELL",
                })
            return results
        except Exception as e:
            logger.error(f"Fetch open positions error: {e}")
            raise e
        finally:
            await client.disconnect()

    async def _refresh_token_and_update_db(self, client: AsyncCTraderClient) -> Optional[str]:
        """
        Internal helper to refresh token using existing refresh_token and update DB.
        """
        from app.database import SessionLocal
        from app.models import BrokerAccount, DataSource
        import json

        db = SessionLocal()
        try:
            # 1. Find the BrokerAccount
            account = db.query(BrokerAccount).filter(BrokerAccount.id == self.account_id).first()
            if not account:
                # Fallback: search by account_id in credentials if id is not UUID
                # (Some systems might use numeric ID in self.account_id)
                logger.warning(f"Account {self.account_id} not found by ID. Searching by account_id in credentials...")
                accounts = db.query(BrokerAccount).all()
                for acc in accounts:
                    try:
                        c = decrypt_data(acc.credentials_encrypted)
                        if str(c.get("account_id")) == str(self.account_id):
                            account = acc
                            break
                    except: continue

            if not account:
                logger.error(f"Could not find BrokerAccount for ID {self.account_id}")
                return None

            # 2. Get Refresh Token
            creds = decrypt_data(account.credentials_encrypted)
            refresh_token = creds.get("refresh_token")
            if not refresh_token:
                logger.error(f"No refresh_token found for account {self.account_id}")
                return None

            # 3. Request New Tokens
            logger.info(f"Requesting token refresh for account {self.account_id}...")
            new_access, new_refresh, expires_in, _ = await client.refresh_token(refresh_token)

            # 4. Update BrokerAccount
            creds["token"] = new_access
            creds["refresh_token"] = new_refresh
            account.credentials_encrypted = encrypt_data(creds)
            
            # 5. Update related DataSource(s)
            sources = db.query(DataSource).filter(DataSource.provider == "CTRADER").all()
            for src in sources:
                try:
                    # Use the jobs.py logic to handle nested/encrypted JSON
                    from app.scheduler.jobs import ensure_dict
                    config = ensure_dict(src.config_json)
                    if str(config.get("account_id")) == str(self.account_id):
                        config["token"] = new_access
                        config["refresh_token"] = new_refresh
                        # [ENCRYPTION-ENFORCEMENT] Encrypt before saving
                        src.config_json = encrypt_data(config)
                        db.add(src)
                except Exception as src_e:
                    logger.warning(f"Failed to update DataSource {src.id}: {src_e}")

            db.add(account)
            db.commit()
            logger.info(f"Successfully refreshed and persisted tokens for account {self.account_id}")
            return new_access

        except Exception as e:
            logger.error(f"Token refresh failed for account {self.account_id}: {e}")
            db.rollback()
            return None
        finally:
            db.close()
