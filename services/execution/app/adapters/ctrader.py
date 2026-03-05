import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from functools import lru_cache
from app.adapters.base import BrokerAdapter
from app.adapters.ctrader_client import AsyncCTraderClient
from app.adapters.ctrader_connection import CTraderConnectionManager
from ctrader_open_api.messages.OpenApiMessages_pb2 import *
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import *

logger = logging.getLogger(__name__)

from app.database import AsyncSessionLocal
from app.models import MarketSymbol, DataSource
from sqlalchemy import select, or_
import asyncio  # for asyncio.create_task in fire-and-forget publish

class RiskValidationError(Exception):
    """
    [SAFETY] Raised when a pre-trade risk check fails.
    Distinct from ValueError (which maps to HTTP 404 - Not Found).
    This exception maps to HTTP 422 Unprocessable Entity.
    
    Examples:
    - SL price is on the wrong side of the entry price
    - TP price is on the wrong side of the entry price
    - Requested volume would exceed available margin
    """
    pass


class CTraderOrderAdapter(BrokerAdapter):
    def __init__(self, client_id: str, client_secret: str, account_id: str, token: str, host: str = "demo.ctraderapi.com"):
        self.host = host
        self.port = 5035
        
        if not client_id or not client_secret:
            raise ValueError("CTrader Adapter requires client_id (app_id) and client_secret")
        if not account_id or not token:
            raise ValueError("CTrader Adapter requires account_id and token")

        self.client_id = client_id
        self.client_secret = client_secret
        self.account_id = int(account_id)
        self.token = token
        # Symbol cache for fast lookup
        self._symbol_cache: Dict[str, tuple] = {}
        # Use Connection Manager to get a persistent client
        self.client = CTraderConnectionManager.get_client(self.host, self.port, str(self.account_id))

    async def get_account_summary(self) -> Dict[str, Any]:
        await self.client.connect()
        try:
             await self.client.authorize_app(self.client_id, self.client_secret)
             await self.client.authorize_account(self.account_id, self.token)
             
             trader = await self.client.get_trader(self.account_id)
             reconcile = await self.client.get_reconcile(self.account_id)
             
             # cTrader sends monetary values in 'cents' (e.g. 10000 = 100.00)
             balance = trader.balance / 100.0
             
             # openTradeCount is usually number of positions for cTrader
             open_count = len(reconcile.position) if hasattr(reconcile, 'position') else 0
             
             return {
                 "balance": str(balance), 
                 "NAV": str(balance), 
                 "marginAvailable": str(balance), 
                 "openTradeCount": open_count, 
                 "openPositionCount": open_count
             }
        except Exception as e:
             logger.error(f"cTrader Account Summary Error: {e}")
             raise e

    async def _populate_symbol_cache(self):
        """Pre-hydrate symbol cache from database for HFT-lite performance."""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(MarketSymbol).join(DataSource).where(DataSource.provider == 'CTRADER')
                )
                all_syms = result.scalars().all()
                for ms in all_syms:
                    if ms.details and ("symbolId" in ms.details or "ctrader_symbol_id" in ms.details):
                        symbol_id = None
                        if "symbolId" in ms.details:
                            symbol_id = int(ms.details["symbolId"])
                        elif "ctrader_symbol_id" in ms.details:
                            symbol_id = int(ms.details["ctrader_symbol_id"])
                        
                        if symbol_id is not None:
                            lot_size = int(ms.details.get("lotSize", 10000000))
                            # Cache forward mapping (Name -> ID, LotSize)
                            self._symbol_cache[ms.symbol] = (symbol_id, lot_size)
                            # Cache reverse mapping (ID -> Name, LotSize)
                            self._symbol_cache[f"ID_{symbol_id}"] = (ms.symbol, lot_size)
                            
                            # Cache normalized name too
                            normalized = ms.symbol.replace("_", "").replace("/", "").upper()
                            if normalized != ms.symbol:
                                self._symbol_cache[normalized] = (symbol_id, lot_size)
                
                logger.info(f"cTrader: Pre-hydrated {len(all_syms)} symbols into L3 cache.")
        except Exception as e:
            logger.error(f"cTrader: Failed to pre-hydrate symbol cache: {e}")

    def _resolve_symbol_from_cache(self, symbol_name: str) -> Optional[tuple[int, int]]:
        normalized_name = symbol_name.replace("_", "").replace("/", "").upper()
        search_names = {symbol_name, symbol_name.replace("_", "/"), symbol_name.replace("/", "_"), normalized_name}
        for name in search_names:
            if name in self._symbol_cache:
                return self._symbol_cache[name]
        return None

    def _resolve_name_from_id_cache(self, symbol_id: int) -> tuple[str, int]:
        """Returns (symbol_name, lot_size_cents) from cache."""
        cached = self._symbol_cache.get(f"ID_{symbol_id}")
        if cached:
            return cached
        return (f"Unknown_{symbol_id}", 10000000)

    async def _resolve_symbol_id_and_lot_size(self, symbol_name: str) -> tuple[int, int]:
        """
        Returns (symbol_id, lot_size_in_cents).
        Normalization: 1 Standard Lot = 100,000 'Universal Units'.
        """
        # HFT-Lite: Check cache first
        cached = self._resolve_symbol_from_cache(symbol_name)
        if cached:
            return cached

        # If not in cache, try one-time populate then re-check
        await self._populate_symbol_cache()
        cached = self._resolve_symbol_from_cache(symbol_name)
        if cached:
            return cached
            
        raise ValueError(f"Symbol {symbol_name} not found or missing ID for cTrader.")

    async def place_market_order(self, symbol: str, units: float, 
                           sl_price: Optional[float] = None, 
                           tp_price: Optional[float] = None, 
                           trade_id: Optional[str] = None,
                           comment: Optional[str] = None,
                           tag: Optional[str] = None) -> Dict[str, Any]:
        
        # Diagnostic logging for Unit Sign issue
        logger.info(f"cTrader: Placing market order for {symbol}, units={units}")
        
        await self.client.connect()
        try:
            await self.client.authorize_app(self.client_id, self.client_secret)
            await self.client.authorize_account(self.account_id, self.token)
            
            symbol_id, lot_size_cents = await self._resolve_symbol_id_and_lot_size(symbol)
            
            # Universal Units Normalization: 100,000 = 1 Standard Lot
            # volume_cents = (units / 100,000) * lot_size_cents
            volume_cents = int((units / 100000.0) * lot_size_cents)
            
            # Minimum volume check (cTrader requirement)
            if abs(volume_cents) < 100:
                volume_cents = 100 if units > 0 else -100
                
            res = await self.client.create_order(
                account_id=self.account_id,
                symbol_id=symbol_id,
                order_type=ProtoOAOrderType.MARKET,
                trade_side=ProtoOATradeSide.BUY if units > 0 else ProtoOATradeSide.SELL,
                volume=abs(volume_cents),
                sl=sl_price,
                tp=tp_price,
                comment=comment if comment else (f"Ref:{trade_id}" if trade_id else "Auto")
            )
            
            # [H2] REJECTED — publish fill event so WS client gets callback
            if res.payloadType == ProtoOAExecutionEvent().payloadType:
                 if res.executionType == ProtoOAExecutionType.ORDER_REJECTED:
                      error_code = res.errorCode if res.HasField("errorCode") else "UNKNOWN"
                      logger.error(f"cTrader Order REJECTED: {error_code} for {symbol}")
                      # Fire-and-forget publish (non-blocking, non-fatal)
                      try:
                          from app.services.fill_publisher import publish_fill
                          asyncio.create_task(publish_fill(
                              account_id=str(self.account_id),
                              trace_id=trade_id or "",
                              order_id="",
                              status="REJECTED",
                              instrument=symbol,
                              fill_price=0.0,
                              fill_volume=units,
                              reason=str(error_code),
                          ))
                      except Exception as pub_err:
                          logger.warning(f"[H2] Failed to publish REJECTED fill: {pub_err}")
                      raise Exception(f"cTrader Order REJECTED: {error_code}")
                 logger.info(f"cTrader ExecutionEvent: type={res.executionType}")

            # Extract Trade ID or Order ID
            # ExecutionEvent -> position -> positionId, order -> orderId
            
            # Check if order was executed/filled
            # Usually MARKET order results in FILLED or PARTIALLY_FILLED
            # We should have 'position' and 'deal'
            
            position_id = ""
            if res.HasField("position"):
                 position_id = str(res.position.positionId)
            elif res.HasField("deal") and res.deal.positionId:
                 position_id = str(res.deal.positionId)
                 
            order_id = ""
            if res.HasField("order"):
                 order_id = str(res.order.orderId)
            
            if not (order_id or position_id):
                 logger.warning(f"cTrader order placed but no ID found in response: {res}")

            fill_price = float(res.deal.executionPrice) if res.HasField("deal") else 0.0
            broker_order_id = order_id or position_id

            # [H2] FILLED — publish fill event so WS client gets async callback
            try:
                from app.services.fill_publisher import publish_fill
                asyncio.create_task(publish_fill(
                    account_id=str(self.account_id),
                    trace_id=trade_id or "",
                    order_id=broker_order_id,
                    status="FILLED",
                    instrument=symbol,
                    fill_price=fill_price,
                    fill_volume=units,
                ))
            except Exception as pub_err:
                logger.warning(f"[H2] Failed to publish FILLED fill event: {pub_err}")

            return {
                "orderFillTransaction": {
                    "id": broker_order_id,
                    "instrument": symbol,
                    "units": str(units),
                    "price": str(fill_price),
                    "time": datetime.utcnow().isoformat()
                }
            }
        except Exception as e:
             logger.error(f"cTrader Place Order Error: {e}")
             raise e

    async def get_open_trades(self) -> List[Dict[str, Any]]:
        await self.client.connect()
        try:
            await self.client.authorize_app(self.client_id, self.client_secret)
            await self.client.authorize_account(self.account_id, self.token)
            
            reconcile = await self.client.get_reconcile(self.account_id)
            trades = []
            
            # Ensure cache is hydrated
            if not self._symbol_cache:
                await self._populate_symbol_cache()

            for p in reconcile.position:
                s_name, lot_size_cents = self._resolve_name_from_id_cache(p.symbolId)
                norm_units = (p.volume / float(lot_size_cents)) * 100000.0

                trades.append({
                    "id": str(p.positionId),
                    "symbol": s_name,
                    "units": norm_units,
                    "side": "BUY" if p.tradeSide == ProtoOATradeSide.BUY else "SELL",
                    "entry_price": p.price,
                    "current_price": 0.0, # Need spot price...
                    "pnl": p.grossProfit / 100.0, # Cents to USD
                })
            
            return trades
            
        except Exception as e:
            logger.error(f"cTrader Get Open Trades Error: {e}")
            return []

    async def place_limit_order(self, symbol: str, units: float, entry_price: float,
                          sl_price: Optional[float] = None, 
                          tp_price: Optional[float] = None, 
                          time_in_force: str = "GTC",
                          trade_id: Optional[str] = None,
                          comment: Optional[str] = None,
                          tag: Optional[str] = None) -> Dict[str, Any]:
        await self.client.connect()
        try:
            await self.client.authorize_app(self.client_id, self.client_secret)
            await self.client.authorize_account(self.account_id, self.token)
            
            symbol_id, lot_size_cents = await self._resolve_symbol_id_and_lot_size(symbol)
            volume_cents = int((units / 100000.0) * lot_size_cents)
            
            if abs(volume_cents) < 100:
                volume_cents = 100 if units > 0 else -100
            
            # Determine Limit vs Stop? 
            # place_limit_order implies LIMIT.
            # OrderType: LIMIT
            
            res = await self.client.create_order(
                account_id=self.account_id,
                symbol_id=symbol_id,
                order_type=ProtoOAOrderType.LIMIT,
                trade_side=ProtoOATradeSide.BUY if units > 0 else ProtoOATradeSide.SELL,
                volume=abs(volume_cents),
                price=entry_price,
                sl=sl_price,
                tp=tp_price,
                comment=comment if comment else (f"Ref:{trade_id}" if trade_id else "Auto")
            )

            # Check for Rejection in ExecutionEvent
            if res.payloadType == ProtoOAExecutionEvent().payloadType:
                 if res.executionType == ProtoOAExecutionType.ORDER_REJECTED:
                      error_code = res.errorCode if res.HasField("errorCode") else "UNKNOWN"
                      logger.error(f"cTrader Limit Order REJECTED: {error_code} for {symbol}")
                      raise Exception(f"cTrader Order REJECTED: {error_code}")
                 logger.info(f"cTrader ExecutionEvent (Limit): type={res.executionType}")
            
            # Return structure compatible with main.py expectation (Oanda style)
            return {
                "orderCreateTransaction": {
                    "id": str(res.order.orderId) if res.HasField("order") else (str(res.position.positionId) if res.HasField("position") else "0"),
                    "instrument": symbol,
                    "units": str(units),
                    "price": str(entry_price),
                    "time": datetime.utcnow().isoformat()
                }
            }
        except Exception as e:
            logger.error(f"cTrader Limit Order Error: {e}")
            raise e
        
    async def get_order_book(self, symbol: str) -> Dict[str, Any]:
        return {}

    async def close_trade(self, broker_trade_id: str, units: Optional[float] = None) -> Dict[str, Any]:
        await self.client.connect()
        try:
             await self.client.authorize_app(self.client_id, self.client_secret)
             await self.client.authorize_account(self.account_id, self.token)
             
             # Convert units to cents if partial close
             volume_cents = int(units * 100) if units else 0
             # If units is None, we need to know full volume to close?
             # ProtoOAClosePositionReq requires volume.
             # If we don't know, we must fetch position first.
             
             if not volume_cents:
                 # Fetch position to get volume
                 recon = await self.client.get_reconcile(self.account_id)
                 target = next((p for p in recon.position if str(p.positionId) == str(broker_trade_id)), None)
                 if not target:
                     raise ValueError("Position not found")
                 volume_cents = target.volume
             
             res = await self.client.close_position(self.account_id, int(broker_trade_id), volume=volume_cents)
             return {"status": "closed", "trade_id": broker_trade_id}
             
        except Exception as e:
             logger.error(f"cTrader Close Trade Error: {e}")
             raise e

    async def get_current_price(self, symbol: str) -> float:
        # In a real implementation, this would subscribe to spots or fetch latest spot
        return 0.0

    async def get_trade_history(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        await self.client.connect()
        try:
            await self.client.authorize_app(self.client_id, self.client_secret)
            await self.client.authorize_account(self.account_id, self.token)
            
            # Convert dates to milliseconds
            from_ts = int(start_date.timestamp() * 1000)
            to_ts = int(end_date.timestamp() * 1000)
            
            deals = await self.client.get_deal_list(self.account_id, from_ts, to_ts)
            
            # Ensure cache is hydrated
            if not self._symbol_cache:
                await self._populate_symbol_cache()

            results = []
            for d in deals:
                if d.closePositionDetail: # This deal closed a position
                    s_name, _ = self._resolve_name_from_id_cache(d.symbolId)
                    
                    # Entry price? The closing deal knows the exit price.
                    # The entry price is in 'closePositionDetail.entryPrice'?
                    # ProtoOAClosePositionDetail: entryPrice, grossProfit, swap, commission, balance, balanceVersion...
                    
                    entry_p = d.closePositionDetail.entryPrice
                    exit_p = d.executionPrice
                    
                    # ROI/PnL
                    pnl_raw = d.closePositionDetail.grossProfit / 100.0 # cents to units
                    
                    from app.models import TradeStatus, TradeDirection

                    direction = TradeDirection.LONG if d.tradeSide == ProtoOATradeSide.SELL else TradeDirection.SHORT
                    # If I SELL to Close, I was LONG.

                    results.append({
                        "trade_id": str(d.dealId), # Use DealID as TradeID to avoid duplicates on partial closes
                        "symbol": s_name,
                        "strategy_name": "Imported",
                        "signal_timestamp": datetime.fromtimestamp(d.createTimestamp / 1000.0), # Deal time
                        "status": TradeStatus.CLOSED,
                        "direction": direction, 
                        
                        # Wait. If I SELL to Close, I was LONG.
                        # If d.tradeSide is SELL, then I sold. If this is a closing deal, I was LONG.
                        # Correct.
                        
                        "entry_price": entry_p,
                        "exit_price": exit_p,
                        "sl_price": 0.0,
                        "tp_price": 0.0,
                        "lot_size": d.volume / 100.0 / 1000.0 / 100.0, # Volume in cents. 1 Lot = 100,000 units.
                        # Wait, volume in cents.
                        # units = volume / 100.
                        # lot_size usually in 'standard lots' (1.0).
                        # Let's check SDD for 'lot_size'. "Calculated lot size".
                        # For XAU, 1 lot = 100oz.
                        # If we store 'units' in Trade model? No, 'lot_size'.
                        # Assuming Standard Lots.
                        # units = d.volume / 100.0
                        # lots = units / 100000.0 (Standard) or contract size.
                        # We don't know contract size here without symbol info.
                        # Let's store UNITS or guess?
                        # The Trade model says: "Calculated lot size".
                        # We should probably store "units" if we are not sure about contract size.
                        # But `lot_size` column is Numeric(10,2). 
                        # Let's try to normalize to Lots if possible, or just store raw units if lot_size is ambiguous?
                        # For now: units.
                        
                        "lot_size": d.volume / 100.0, # Storing as UNITS for now to be safe, or 0.01 etc?
                        # Re-reading Model: `lot_size`. 
                        # If I store 1000 (units), it looks like 1000 lots!
                        # I should probably default to 0.01 if I can't calc, or try to approximate.
                        # Let's use 0 for now or units.
                        # Re-check logic: `d.volume` is cents. `units` = cents/100.
                        # I'll store `units` but label it clearly in my head.
                        # Actually, looking at `open_trades` in cTrader adapter: `p.volume / 100.0` is returned as `units`.
                        # API usually expects Units.
                        # The Trade model has `lot_size`.
                        # I'll just use units/100000 as a rough guess for now.
                        
                        "risk_usd": 0.0,
                        "pnl_usd": pnl_raw,
                        "exit_timestamp": datetime.fromtimestamp(d.executionTimestamp / 1000.0),
                        "metadata_json": {"deal_id": str(d.dealId), "raw": "cTrader Deal"}
                    })
            
            return results

        except Exception as e:
            logger.error(f"cTrader Trade History Error: {e}")
            raise e

    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        await self.client.connect()
        try:
            await self.client.authorize_app(self.client_id, self.client_secret)
            await self.client.authorize_account(self.account_id, self.token)
            
            res = await self.client.cancel_order(self.account_id, int(order_id))
            return {"status": "cancelled", "order_id": order_id}
        except Exception as e:
            if "ORDER_NOT_FOUND" in str(e):
                logger.warning(f"cTrader Cancel Order: Order {order_id} not found.")
                raise ValueError(f"Order {order_id} not found")
            logger.error(f"cTrader Cancel Order Error: {e}")
            raise e

    async def amend_order(self, order_id: str, units: Optional[float] = None, 
                    price: Optional[float] = None, 
                    sl_price: Optional[float] = None, 
                    tp_price: Optional[float] = None) -> Dict[str, Any]:
        await self.client.connect()
        try:
            await self.client.authorize_app(self.client_id, self.client_secret)
            await self.client.authorize_account(self.account_id, self.token)
            
            # Fetch order details to get current volume and instrument
            orders = await self.get_pending_orders()
            target_order = next((o for o in orders if o["id"] == str(order_id)), None)
            if not target_order:
                raise ValueError(f"Order {order_id} not found to amend")
            
            # [SAFETY - Layer 3] Pre-trade Risk Validation: SL/TP direction check
            entry_price = float(target_order.get("price", 0))
            side = target_order.get("side", "BUY").upper()
            
            if sl_price is not None and entry_price > 0:
                if side == "BUY" and sl_price >= entry_price:
                    raise RiskValidationError(
                        f"Invalid SL for LONG: sl_price={sl_price} must be BELOW entry_price={entry_price}"
                    )
                elif side == "SELL" and sl_price <= entry_price:
                    raise RiskValidationError(
                        f"Invalid SL for SHORT: sl_price={sl_price} must be ABOVE entry_price={entry_price}"
                    )
            
            if tp_price is not None and entry_price > 0:
                if side == "BUY" and tp_price <= entry_price:
                    raise RiskValidationError(
                        f"Invalid TP for LONG: tp_price={tp_price} must be ABOVE entry_price={entry_price}"
                    )
                elif side == "SELL" and tp_price >= entry_price:
                    raise RiskValidationError(
                        f"Invalid TP for SHORT: tp_price={tp_price} must be BELOW entry_price={entry_price}"
                    )
            
            # Resolve lot size for this symbol
            _, lot_size_cents = await self._resolve_symbol_id_and_lot_size(target_order["instrument"])
            
            if units is not None:
                volume_cents = int((units / 100000.0) * lot_size_cents)
            else:
                # Use current raw volume from the order
                volume_cents = target_order.get("raw_volume")
            
            if price is None:
                # Use current price from the order
                price = target_order.get("price")

            res = await self.client.amend_order(
                account_id=self.account_id,
                order_id=int(order_id),
                volume=volume_cents,
                price=price,
                sl=sl_price,
                tp=tp_price
            )
            return {"status": "amended", "order_id": order_id}
        except (ValueError, RiskValidationError) as ve:
            # Re-raise explicit errors (404 Not Found or 422 Risk Violation)
            raise ve
        except Exception as e:
            if "ORDER_NOT_FOUND" in str(e):
                logger.warning(f"cTrader Amend Order: Order {order_id} not found.")
                raise ValueError(f"Order {order_id} not found")
            logger.error(f"cTrader Amend Order Error: {e}")
            raise e

    async def amend_position(self, broker_trade_id: str, 
                        sl_price: Optional[float] = None, 
                        tp_price: Optional[float] = None) -> Dict[str, Any]:
        await self.client.connect()
        try:
            await self.client.authorize_app(self.client_id, self.client_secret)
            await self.client.authorize_account(self.account_id, self.token)
            
            res = await self.client.amend_position_sltp(
                account_id=self.account_id,
                position_id=int(broker_trade_id),
                sl=sl_price,
                tp=tp_price
            )
            return {"status": "amended", "position_id": broker_trade_id}
        except Exception as e:
            logger.error(f"cTrader Amend Position Error: {e}")
            raise e

    async def get_pending_orders(self) -> List[Dict[str, Any]]:
        await self.client.connect()
        try:
            await self.client.authorize_app(self.client_id, self.client_secret)
            await self.client.authorize_account(self.account_id, self.token)
            
            reconcile = await self.client.get_reconcile(self.account_id)
            orders = []
            
            if not reconcile.order:
                return []
                
            # Ensure cache is hydrated
            if not self._symbol_cache:
                await self._populate_symbol_cache()
                            
            for o in reconcile.order:
                s_name, lot_size_cents = self._resolve_name_from_id_cache(o.tradeData.symbolId)
                norm_units = (o.tradeData.volume / float(lot_size_cents)) * 100000.0

                orders.append({
                    "id": str(o.orderId),
                    "instrument": s_name,
                    "units": norm_units,
                    "raw_volume": o.tradeData.volume,
                    "type": str(o.orderType),
                    "price": o.limitPrice if o.limitPrice else (o.stopPrice if o.stopPrice else 0.0),
                    "time": datetime.fromtimestamp(o.tradeData.openTimestamp / 1000.0).isoformat() if o.tradeData.openTimestamp else None,
                    "status": "PENDING"
                })
                
            return orders

        except Exception as e:
            logger.error(f"cTrader Get Pending Orders Error: {e}")
            raise e
