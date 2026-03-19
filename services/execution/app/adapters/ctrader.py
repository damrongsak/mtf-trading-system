import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from app.adapters.base import BrokerAdapter
from app.adapters.ctrader_connection import CTraderConnectionManager
from ctrader_open_api.messages.OpenApiMessages_pb2 import *
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import *
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOAExecutionType
from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOAExecutionEvent
from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import ProtoMessage
from app.utils.normalization import parse_iso_timestamp, units_to_standard_lots

logger = logging.getLogger(__name__)


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
             
             # Calculate unrealized from positions
             positions = reconcile.position if hasattr(reconcile, 'position') else []
             unrealized_gross = sum(float(getattr(p, 'grossProfit', 0.0)) / 100.0 for p in positions)
             unrealized_net = sum((float(getattr(p, 'grossProfit', 0.0)) + float(getattr(p, 'swap', 0.0)) + float(getattr(p, 'commission', 0.0))) / 100.0 for p in positions)
             used_margin = sum(float(getattr(p, 'usedMargin', 0.0)) / 100.0 for p in positions)
             
             equity = balance + unrealized_net
             free_margin = equity - used_margin
             margin_level = (equity / used_margin * 100) if used_margin > 0 else None
             
             # openTradeCount is usually number of positions for cTrader
             open_count = len(positions)
             
             return {
                 "balance": balance, 
                 "equity": equity,
                 "NAV": equity,
                 "used_margin": used_margin,
                 "marginUsed": used_margin,
                 "free_margin": free_margin,
                 "marginAvailable": free_margin,
                 "margin_level": margin_level,
                 "unrealized_gross": unrealized_gross,
                 "unrealized_net": unrealized_net,
                 "unrealizedPL": unrealized_net,
                 "openTradeCount": open_count, 
                 "openPositionCount": open_count
             }
        except Exception as e:
             logger.error(f"cTrader Account Summary Error: {e}")
             raise e

    async def _populate_symbol_cache(self):
        """Pre-hydrate symbol cache from execution cache / HTTP fallback for HFT-lite performance."""
        try:
            from app.services.cache_service import execution_cache
            symbols = await execution_cache.get_symbols("CTRADER")
            if not symbols:
                 logger.error("cTrader: Failed to fetch symbols from cache/HTTP.")
                 return
                 
            # API Gateway JSON is typically {"status": "success", "data": [...]}
            if isinstance(symbols, dict) and "data" in symbols:
                symbols_list = symbols["data"]
            elif isinstance(symbols, list):
                symbols_list = symbols
            else:
                logger.error(f"cTrader: Unexpected format for symbols response: {type(symbols)}")
                return

            for ms in symbols_list:
                details = ms.get("details") or {}
                symbol = ms.get("symbol", "").upper()
                
                # [DIAGNOSTIC] Log symbol being processed
                logger.debug(f"cTrader Hydrating: {symbol} with details {details}")

                # Find Symbol ID - try multiple keys for robustness
                symbol_id = None
                if isinstance(details, dict):
                    symbol_id = details.get("symbol_id") or details.get("symbolId") or details.get("ctrader_symbol_id")
                
                if symbol_id is not None:
                    try:
                        symbol_id = int(symbol_id)
                        lot_size = int(details.get("lotSize") or details.get("lot_size") or 10000000)
                        
                        # Step volume is usually in 'cents' in the API, or 'units'. 
                        # We prefer cents for math. Default to 100 cents (1 unit).
                        step_cents = int(details.get("step_volume_cents") or (float(details.get("step_volume", 0.01)) * 100) or 100)

                        # Cache forward mapping (Name -> ID, LotSize, StepSize)
                        self._symbol_cache[symbol] = (symbol_id, lot_size, step_cents)
                        # Cache reverse mapping (ID -> Name, LotSize, StepSize)
                        self._symbol_cache[f"ID_{symbol_id}"] = (symbol, lot_size, step_cents)
                        
                        # Cache normalized names
                        normalized = symbol.replace("_", "").replace("/", "").upper()
                        self._symbol_cache[normalized] = (symbol_id, lot_size, step_cents)
                    except (ValueError, TypeError) as e:
                        logger.warning(f"cTrader: Invalid symbol metadata for {symbol}: {e}")
                else:
                    logger.warning(f"cTrader: Symbol {symbol} has no ID in details: {details}")
            
            logger.info(f"cTrader: Pre-hydrated {len(self._symbol_cache)//2} symbols into L3 cache.")
            
            logger.info(f"cTrader: Pre-hydrated {len(symbols)} symbols into L3 cache.")
        except Exception as e:
            logger.error(f"cTrader: Failed to pre-hydrate symbol cache: {e}", exc_info=True)

    def _resolve_symbol_from_cache(self, symbol_name: str) -> Optional[tuple[int, int]]:
        normalized_name = symbol_name.replace("_", "").replace("/", "").upper()
        search_names = {symbol_name, symbol_name.replace("_", "/"), symbol_name.replace("/", "_"), normalized_name}
        for name in search_names:
            if name in self._symbol_cache:
                return self._symbol_cache[name]
        return None

    def _resolve_name_from_id_cache(self, symbol_id: int) -> tuple[str, int, int]:
        """Returns (symbol_name, lot_size_cents, step_cents) from cache."""
        cached = self._symbol_cache.get(f"ID_{symbol_id}")
        if cached:
            return cached
        return (f"Unknown_{symbol_id}", 10000000, 100)

    async def _resolve_symbol_id_and_lot_size(self, symbol_name: str) -> tuple[int, int, int]:
        """
        Returns (symbol_id, lot_size_in_cents, step_size_in_cents).
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
                           tag: Optional[str] = None,
                           signal_timestamp_ns: Optional[float] = None,
                           is_shadow: bool = False) -> Dict[str, Any]:
        
        # Diagnostic logging for Unit Sign issue
        logger.info(f"cTrader: Placing market order for {symbol}, units={units}")
        
        await self.client.connect()
        try:
            await self.client.authorize_app(self.client_id, self.client_secret)
            await self.client.authorize_account(self.account_id, self.token)
            
            symbol_id, lot_size_cents, step_cents = await self._resolve_symbol_id_and_lot_size(symbol)
            
            # [VOL-Normalization] Universal units to cTrader cents
            # units: 100,000 = 1 Standard Lot
            # formula: (units / 100,000) * lot_size_cents
            raw_volume = (abs(units) / 100000.0) * lot_size_cents
            
            # Step size validation & rounding to nearest step
            multiple = round(raw_volume / step_cents)
            volume_cents = int(multiple * step_cents)
            
            # Absolute minimum check (broker usually enforces 100,000 cents for FX)
            if volume_cents < step_cents:
                volume_cents = int(step_cents)
                
            logger.info(f"cTrader Normalized: units={units} -> volume_cents={volume_cents} (lot_size={lot_size_cents}, step={step_cents})")
                
                
            res = await self.client.create_order(
                account_id=self.account_id,
                symbol_id=symbol_id,
                order_type=ProtoOAOrderType.MARKET,
                trade_side=ProtoOATradeSide.BUY if units > 0 else ProtoOATradeSide.SELL,
                volume=abs(volume_cents),
                # SL/TP for Market orders often must be set after fill in Open API
                sl=None,
                tp=None,
                comment=comment if comment else (f"Ref:{trade_id}" if trade_id else "Auto")
            )
            
            # [H2] REJECTED — publish fill event so WS client gets callback
            if getattr(res, "payloadType", None) == 2186:
                 if res.executionType == ProtoOAExecutionType.ORDER_REJECTED:
                      error_code = res.errorCode if res.HasField("errorCode") else "UNKNOWN"
                      logger.error(f"cTrader Order REJECTED: {error_code} for {symbol}")
                      # Fire-and-forget publish (non-blocking, non-fatal)
                      try:
                          from app.services.fill_publisher import publish_fill
                          # Rule 7: publish_fill is async and does I/O (Redis)
                          # Using create_task to avoid blocking the hot loop
                          asyncio.create_task(publish_fill(
                              account_id=str(self.account_id),
                              trace_id=trade_id or "",
                              order_id="",
                              status="REJECTED",
                              instrument=symbol,
                              fill_price=0.0,
                               fill_volume=units,
                               reason=str(error_code),
                               signal_timestamp_ns=signal_timestamp_ns,
                               is_shadow=is_shadow,
                           ))
                      except Exception as pub_err:
                          logger.warning(f"[H2] Failed to publish REJECTED fill: {pub_err}")
                      raise Exception(f"cTrader Order REJECTED: {error_code}")
            logger.info(f"cTrader ExecutionEvent: type={res.executionType}")
            
            # Extract IDs promptly so they are available for logic below
            order_id = str(res.order.orderId) if res.HasField("order") else None
            
            # Robust Position ID extraction across different ExecutionEvent structures
            position_id = None
            if res.HasField("position"):
                position_id = str(res.position.positionId)
            elif res.HasField("deal"):
                position_id = str(res.deal.positionId)
            elif res.HasField("order") and res.order.HasField("positionId"):
                position_id = str(res.order.positionId)
            
            # [PHASE 15] Stable ID Mapping: Prioritize position_id for MARKET fills
            is_filled = res.executionType in [
                ProtoOAExecutionType.ORDER_FILLED, 
                ProtoOAExecutionType.ORDER_PARTIAL_FILL
            ]
            
            broker_order_id = position_id or order_id
            
            # If we finally found a position_id, ensure it's used for the local SL/TP logic below
            if not position_id:
                if is_filled:
                    logger.warning(f"cTrader: Order {order_id} FILLED but no position_id found yet.")
                position_id = order_id

            fill_price = float(res.deal.executionPrice) if res.HasField("deal") else 0.0
                  
            # If SL/TP provided, validate against fill_price before amending
            if position_id and (sl_price or tp_price) and is_filled:
                 is_buy = units > 0
                 valid_sl = sl_price
                 valid_tp = tp_price
                 
                 if fill_price > 0:
                      if is_buy:
                           if tp_price and tp_price <= fill_price:
                                logger.warning(f"cTrader: TP {tp_price} <= fill_price {fill_price} for BUY — skipping TP")
                                valid_tp = None
                           if sl_price and sl_price >= fill_price:
                                logger.warning(f"cTrader: SL {sl_price} >= fill_price {fill_price} for BUY — skipping SL")
                                valid_sl = None
                      else:
                           if tp_price and tp_price >= fill_price:
                                logger.warning(f"cTrader: TP {tp_price} >= fill_price {fill_price} for SELL — skipping TP")
                                valid_tp = None
                           if sl_price and sl_price <= fill_price:
                                logger.warning(f"cTrader: SL {sl_price} <= fill_price {fill_price} for SELL — skipping SL")
                                valid_sl = None
                 
                 if valid_sl or valid_tp:
                      try:
                           logger.info(f"cTrader: Amending SL={valid_sl}, TP={valid_tp} for Position {position_id}")
                           await self.client.amend_position_sltp(
                               account_id=self.account_id,
                               position_id=int(position_id),
                               sl=valid_sl,
                               tp=valid_tp
                           )
                      except Exception as am_err:
                           logger.warning(f"cTrader: Failed to set SL/TP after market fill: {am_err}")

            # [HFT-lite] Save context for Async Fill Router
            # This allows the global ExecutionEvent handler to find the original trace_id and metadata
            try:
                from app.services.cache_service import execution_cache
                context = {
                    "trace_id": trade_id or "",
                    "signal_timestamp_ns": signal_timestamp_ns,
                    "sl_price": sl_price or 0.0,
                    "tp_price": tp_price or 0.0,
                    "comment": comment or "",
                    "is_shadow": is_shadow,
                    "symbol": symbol
                }
                # Expire after 1 hour — should be filled or manually dealt with by then
                await execution_cache.set_order_context(broker_order_id, context, expire=3600)
                logger.debug(f"cTrader: Saved order context for {broker_order_id}")
            except Exception as ctx_err:
                logger.warning(f"cTrader: Failed to save order context for {broker_order_id}: {ctx_err}")

            if is_filled:
                logger.info(f"cTrader: Order {broker_order_id} filled immediately (Sync Path).")
                # We still publish but the router might also see it. 
                # To prevent duplicates, publish_fill or the router should check if already processed.
                # However, usually cTrader sends FILLED as a separate unsolicited message.
                pass 
            else:
                logger.info(f"cTrader: Order {broker_order_id} {res.executionType} - waiting for async fill event.")

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
                # symbolId, volume, tradeSide are in p.tradeData
                symbol_id = p.tradeData.symbolId
                volume = p.tradeData.volume
                trade_side = p.tradeData.tradeSide
                
                s_name = await self._resolve_symbol_name(p.tradeData.symbolId)
                
                # Convert units from cents
                norm_units = p.tradeData.volume / 100.0
                tsl_status = p.trailingStopLoss if p.HasField("trailingStopLoss") else False
                
                # Force print to stdout for docker compose logs visibility
                print(f"!!! JANITOR_DEBUG !!! Position {p.positionId} trailingStopLoss={tsl_status}", flush=True)

                trades.append({
                    "id": str(p.positionId),
                    "symbol": s_name,
                    "units": norm_units,
                    "side": "BUY" if trade_side == ProtoOATradeSide.BUY else "SELL",
                    "entry_price": p.price,
                    "sl": p.stopLoss if p.HasField("stopLoss") else None,
                    "tp": p.takeProfit if p.HasField("takeProfit") else None,
                    "trailing_sl": tsl_status,
                    "trailing_stop": tsl_status,
                    "current_price": 0.0,
                    "pnl": (float(getattr(p, 'swap', 0.0)) + float(getattr(p, 'commission', 0.0))) / 100.0,
                    "type": "POSITION"
                })

            # [PHASE 15] Include Pending Orders in reconciliation to prevent Janitor from pruning them
            for o in reconcile.order:
                # status 1=ACCEPTED (Pending), 2=FILLED (but maybe waiting?), etc.
                # We only want those that are effectively "working"
                if o.orderStatus == ProtoOAOrderStatus.ORDER_STATUS_ACCEPTED:
                    s_name = await self._resolve_symbol_name(o.tradeData.symbolId)
                    norm_units = o.tradeData.volume / 100.0
                    
                    trades.append({
                        "id": str(o.orderId),
                        "symbol": s_name,
                        "units": norm_units,
                        "side": "BUY" if o.tradeData.tradeSide == ProtoOATradeSide.BUY else "SELL",
                        "entry_price": o.limitPrice if o.HasField("limitPrice") else (o.stopPrice if o.HasField("stopPrice") else 0.0),
                        "sl": o.stopLoss if o.HasField("stopLoss") else None,
                        "tp": o.takeProfit if o.HasField("takeProfit") else None,
                        "status": "PENDING",
                        "type": "ORDER"
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
            
            symbol_id, lot_size_cents, step_cents = await self._resolve_symbol_id_and_lot_size(symbol)
            
            # [VOL-Normalization] Universal units to cTrader cents
            raw_volume = (abs(units) / 100000.0) * lot_size_cents
            
            # Step size validation & rounding to nearest step
            multiple = round(raw_volume / step_cents)
            volume_cents = int(multiple * step_cents)
            
            if volume_cents < step_cents:
                volume_cents = int(step_cents)
            
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
        """
        Fetch Depth of Market (Order Book) for a symbol.
        """
        await self.client.connect()
        await self.client.authorize_app(self.client_id, self.client_secret)
        await self.client.authorize_account(self.account_id, self.token)

        symbol_id, _, _ = await self._resolve_symbol_id_and_lot_size(symbol)
        return await self.client.get_order_book(self.account_id, symbol_id)

    async def close_trade(self, broker_trade_id: str, units: Optional[float] = None) -> Dict[str, Any]:
        await self.client.connect()
        try:
             await self.client.authorize_app(self.client_id, self.client_secret)
             await self.client.authorize_account(self.account_id, self.token)
             
             # Convert units to cents if partial close
             # We need to resolve lot details for symbol
             symbol_id, lot_size_cents, step_cents = await self._resolve_symbol_id_and_lot_size("XAUUSD") # Fallback, but closer logic needs resolving
             # Better: fetch position first to get symbol
             # If units is None, we need to know full volume to close?
             # ProtoOAClosePositionReq requires volume.
             # If we don't know, we must fetch position first.
             
             if units is None:
                 # Fetch position to get volume and symbol
                 recon = await self.client.get_reconcile(self.account_id)
                 target = next((p for p in recon.position if str(p.positionId) == str(broker_trade_id)), None)
                 if not target:
                     raise ValueError(f"Position {broker_trade_id} not found")
                 volume_cents = target.tradeData.volume
             else:
                 # Need to know which symbol to resolve lot size for
                 recon = await self.client.get_reconcile(self.account_id)
                 target = next((p for p in recon.position if str(p.positionId) == str(broker_trade_id)), None)
                 if not target:
                      raise ValueError(f"Position {broker_trade_id} not found")
                 
                 s_name = await self._resolve_symbol_name(target.tradeData.symbolId)
                 _, _, step_cents = await self._resolve_symbol_id_and_lot_size(s_name)
                 
                 # Convert units to volume_cents
                 multiple = units * 100  # 0.01 lot = 1 unit = 100 cents
                 volume_cents = int(multiple * step_cents)
                 if volume_cents < step_cents:
                     volume_cents = int(step_cents)
             
             res = await self.client.close_position(self.account_id, int(broker_trade_id), volume=volume_cents)
             return {"status": "closed", "trade_id": broker_trade_id}
             
        except Exception as e:
             logger.error(f"cTrader Close Trade Error: {e}")
             raise e

    async def get_current_price(self, symbol: str) -> float:
        """
        Fetch the current market midpoint price for a symbol via one-shot spot subscription.
        Resolves symbol to cTrader symbolId from L3 cache, then uses ProtoOASubscribeSpotsReq.
        Returns (bid + ask) / 2.0
        Raises ValueError if symbol not found in cache or spot price times out.
        """
        await self.client.connect()
        await self.client.authorize_app(self.client_id, self.client_secret)
        await self.client.authorize_account(self.account_id, self.token)

        # Resolve symbol to cTrader ID using L3 cache
        symbol_id, _, _ = await self._resolve_symbol_id_and_lot_size(symbol)

        bid, ask = await self.client.get_spot_price(self.account_id, symbol_id)
        if bid == 0.0 and ask == 0.0:
            raise ValueError(f"cTrader returned zero prices for {symbol}, symbolId={symbol_id}")
        return (bid + ask) / 2.0


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
                    s_name, lot_size_cents, step_cents = self._resolve_name_from_id_cache(d.symbolId)
                    
                    entry_p = d.closePositionDetail.entryPrice
                    exit_p = d.executionPrice
                    
                    # ROI/PnL
                    pnl_raw = float(getattr(d.closePositionDetail, 'grossProfit', 0.0)) / 100.0
                    
                    from app.models import TradeStatus, TradeDirection

                    direction = TradeDirection.LONG if d.tradeSide == ProtoOATradeSide.SELL else TradeDirection.SHORT
                    
                    # Normalization
                    close_dt = parse_iso_timestamp(d.executionTimestamp)
                    open_dt = parse_iso_timestamp(d.createTimestamp)
                    
                    # volume is in cents in cTrader Protobuf
                    units = (d.volume / float(lot_size_cents)) * 100000.0
                    std_lots = units_to_standard_lots(units)

                    results.append({
                        "trade_id": str(d.dealId),
                        "symbol": s_name,
                        "strategy_name": "Imported",
                        "signal_timestamp": open_dt,
                        "status": TradeStatus.CLOSED,
                        "direction": direction, 
                        "entry_price": entry_p,
                        "exit_price": exit_p,
                        "sl_price": 0.0,
                        "tp_price": 0.0,
                        "lot_size": std_lots,
                        "risk_usd": 0.0,
                        "pnl_usd": pnl_raw,
                        "exit_timestamp": close_dt,
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
                    tp_price: Optional[float] = None,
                    trailing_sl: Optional[bool] = None) -> Dict[str, Any]:
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
            
            # Resolve lot details for this symbol
            _, lot_size_cents, step_cents = await self._resolve_symbol_id_and_lot_size(target_order["instrument"])
            
            if units is not None:
                # [VOL-Normalization] Universal units to cTrader cents
                raw_volume = (abs(units) / 100000.0) * lot_size_cents
                
                # Step size validation & rounding to nearest step
                multiple = round(raw_volume / step_cents)
                volume_cents = int(multiple * step_cents)
                
                if volume_cents < step_cents:
                    volume_cents = int(step_cents)
            else:
                # Use current raw volume from the order
                volume_cents = target_order.get("raw_volume")
            
            if price is None:
                # Use current price from the order
                price = target_order.get("price")

            # Preserve existing SL/TP if not explicitly provided
            final_sl = sl_price if sl_price is not None else target_order.get("sl")
            final_tp = tp_price if tp_price is not None else target_order.get("tp")
            final_trailing = trailing_sl if trailing_sl is not None else target_order.get("trailing_sl", False)

            res = await self.client.amend_order(
                account_id=self.account_id,
                order_id=int(order_id),
                volume=volume_cents,
                price=price,
                sl=final_sl,
                tp=final_tp,
                trailing_sl=final_trailing
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
                        tp_price: Optional[float] = None,
                        trailing_sl: Optional[bool] = None) -> Dict[str, Any]:
        await self.client.connect()
        try:
            await self.client.authorize_app(self.client_id, self.client_secret)
            await self.client.authorize_account(self.account_id, self.token)

            # [SAFETY - Layer 3] Fetch position to validate SL/TP direction before amending
            reconcile = await self.client.get_reconcile(self.account_id)
            
            target = next(
                (p for p in reconcile.position if str(p.positionId) == str(broker_trade_id)),
                None
            )
            if not target:
                raise ValueError(f"Position {broker_trade_id} not found to amend")

            # Determine position side and entry price for validation
            is_buy = target.tradeData.tradeSide == ProtoOATradeSide.BUY
            entry_price = float(target.price) if target.price else 0.0

            if entry_price > 0:
                if sl_price is not None:
                    if is_buy and sl_price >= entry_price:
                        raise RiskValidationError(
                            f"Invalid SL for LONG: sl_price={sl_price} must be BELOW entry_price={entry_price}"
                        )
                    elif not is_buy and sl_price <= entry_price:
                        raise RiskValidationError(
                            f"Invalid SL for SHORT: sl_price={sl_price} must be ABOVE entry_price={entry_price}"
                        )
                if tp_price is not None:
                    if is_buy and tp_price <= entry_price:
                        raise RiskValidationError(
                            f"Invalid TP for LONG: tp_price={tp_price} must be ABOVE entry_price={entry_price}"
                        )
                    elif not is_buy and tp_price >= entry_price:
                        raise RiskValidationError(
                            f"Invalid TP for SHORT: tp_price={tp_price} must be BELOW entry_price={entry_price}"
                        )

            # Preserve existing SL/TP if not explicitly provided
            # target is ProtoOAPosition from get_reconcile
            final_sl = sl_price if sl_price is not None else (float(target.stopLoss) if target.HasField("stopLoss") else None)
            final_tp = tp_price if tp_price is not None else (float(target.takeProfit) if target.HasField("takeProfit") else None)
            final_trailing = trailing_sl if trailing_sl is not None else (bool(target.trailingStopLoss) if target.HasField("trailingStopLoss") else False)

            res = await self.client.amend_position_sltp(
                account_id=self.account_id,
                position_id=int(broker_trade_id),
                sl=final_sl,
                tp=final_tp,
                trailing_sl=final_trailing
            )
            return {"status": "amended", "position_id": broker_trade_id}
        except (ValueError, RiskValidationError) as ve:
            raise ve
        except Exception as e:
            logger.error(f"cTrader Amend Position Error: {e}")
            raise e

    async def get_open_trades(self) -> List[Dict[str, Any]]:
        """
        Fetch all open positions from cTrader.
        Maps ProtoOAPosition to system trade dict.
        """
        await self.client.connect()
        try:
            await self.client.authorize_app(self.client_id, self.client_secret)
            await self.client.authorize_account(self.account_id, self.token)
            
            reconcile = await self.client.get_reconcile(self.account_id)
            positions = []
            
            if not hasattr(reconcile, 'position') or not reconcile.position:
                return []
                
            # Ensure cache is hydrated
            if not self._symbol_cache:
                await self._populate_symbol_cache()
                            
            for p in reconcile.position:
                s_name, lot_size_cents, step_cents = self._resolve_name_from_id_cache(p.tradeData.symbolId)
                
                # [VOL-Reverse-Normalization] cTrader cents to Universal units
                units = (p.tradeData.volume / float(lot_size_cents)) * 100000.0
                
                positions.append({
                    "id": str(p.positionId),
                    "broker_trade_id": str(p.positionId),
                    "symbol": s_name,
                    "instrument": s_name,
                    "units": units if p.tradeData.tradeSide == ProtoOATradeSide.BUY else -units,
                    "price": float(p.price) if hasattr(p, 'price') else 0.0,
                    "sl": float(p.stopLoss) if p.HasField("stopLoss") else None,
                    "tp": float(p.takeProfit) if p.HasField("takeProfit") else None,
                    "currentUnits": units,
                    "side": "BUY" if p.tradeData.tradeSide == ProtoOATradeSide.BUY else "SELL",
                    "pnl": float(getattr(p, 'grossProfit', 0.0)) / 100.0,
                    "unrealizedPL": float(getattr(p, 'grossProfit', 0.0)) / 100.0,
                })
                
            pending = await self.get_pending_orders()
            
            # Label types for consistent frontend/logic handling
            for p in positions:
                p["type"] = "POSITION"
            for o in pending:
                o["type"] = "ORDER"
                
            return positions + pending
        except Exception as e:
            logger.error(f"cTrader Get Open Trades Error: {e}")
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
                s_name, lot_size_cents, step_cents = self._resolve_name_from_id_cache(o.tradeData.symbolId)
                norm_units = (o.tradeData.volume / float(lot_size_cents)) * 100000.0

                orders.append({
                    "id": str(o.orderId),
                    "instrument": s_name,
                    "units": norm_units,
                    "raw_volume": o.tradeData.volume,
                    "side": "BUY" if o.tradeData.tradeSide == ProtoOATradeSide.BUY else "SELL",
                    "type": str(o.orderType),
                    "price": o.limitPrice if o.limitPrice else (o.stopPrice if o.stopPrice else 0.0),
                    "sl": o.stopLoss if o.HasField("stopLoss") else None,
                    "tp": o.takeProfit if o.HasField("takeProfit") else None,
                    "trailing_sl": o.trailingStopLoss if o.HasField("trailingStopLoss") else False,
                    "trailing_stop": o.trailingStopLoss if o.HasField("trailingStopLoss") else False,
                    "time": datetime.fromtimestamp(o.tradeData.openTimestamp / 1000.0).isoformat() if o.tradeData.openTimestamp else None,
                    "status": "PENDING"
                })
                
            return orders

        except Exception as e:
            logger.error(f"cTrader Get Pending Orders Error: {e}")
            raise e

class CTraderMessageRouter:
    """
    [HFT-lite] Global Router for unsolicited cTrader messages.
    Handles ExecutionEvents (Fills) across all active connections.
    """
    @staticmethod
    def handle_unsolicited_message(msg: ProtoMessage):
        """Main entry point from AsyncCTraderClient"""
        # 2126 = ProtoOAExecutionEvent
        if msg.payloadType == 2126:
            asyncio.create_task(CTraderMessageRouter._process_execution_event(msg))
        elif msg.payloadType == 2121: # ProtoOASpotEvent (Example)
             # Route to price stream or indicator engines if needed
             pass

    @staticmethod
    async def _process_execution_event(msg: ProtoMessage):
        try:
            from app.services.fill_publisher import publish_fill
            from app.services.cache_service import execution_cache
            
            event = ProtoOAExecutionEvent()
            event.ParseFromString(msg.payload)
            
            account_id = str(event.ctidTraderAccountId)
            exec_type = event.executionType
            
            # We only care about fills for now
            if exec_type != ProtoOAExecutionType.ORDER_FILLED:
                # logger.debug(f"cTrader: Async ExecutionEvent {exec_type} for acc {account_id} - ignoring.")
                return

            broker_order_id = str(event.order.orderId)
            logger.info(f"cTrader: Async Fill received for Order {broker_order_id} (Acc: {account_id})")
            
            # 1. Fetch Context from Redis
            context = await execution_cache.get_order_context(broker_order_id)
            if not context:
                logger.warning(f"cTrader: No context found for filled order {broker_order_id}. Manual or external order?")
                # We should still try to find symbol from symbol_id
                # but we'll miss trace_id/metadata
                return

            # 2. Extract Data
            trace_id = context.get("trace_id", "")
            symbol = context.get("symbol", "UNKNOWN")
            units = float(event.order.volume) / 100.0 # cTrader units to standard
            
            # Prices
            # Deal has the actual execution price
            fill_price = 0.0
            deal_id = None
            if event.HasField("deal"):
                 fill_price = float(event.deal.executionPrice)
                 deal_id = str(event.deal.dealId)
            
            sl_price = context.get("sl_price", 0.0)
            tp_price = context.get("tp_price", 0.0)
            
            # Logic: If SL/TP were hit, we might need to handle them differently
            # but usually this flow is for Entry Fills.
            
            # 3. Publish Fill
            await publish_fill(
                account_id=account_id,
                trace_id=trace_id,
                order_id=broker_order_id,
                status="FILLED",
                instrument=symbol,
                fill_price=fill_price,
                fill_volume=units,
                sl_price=sl_price,
                tp_price=tp_price,
                direction=context.get("direction", "LONG" if units > 0 else "SHORT"),
                comment=context.get("comment", ""),
                deal_id=deal_id,
                signal_timestamp_ns=context.get("signal_timestamp_ns"),
                is_shadow=context.get("is_shadow", False)
            )
            
            # 4. Cleanup context
            await execution_cache.delete_order_context(broker_order_id)
            
        except Exception as e:
            logger.error(f"cTrader Router Error: {e}", exc_info=True)
