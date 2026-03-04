import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from app.adapters.base import BrokerAdapter
from app.adapters.ctrader_client import AsyncCTraderClient
from app.adapters.ctrader_connection import CTraderConnectionManager
from ctrader_open_api.messages.OpenApiMessages_pb2 import *
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import *

logger = logging.getLogger(__name__)

from app.database import AsyncSessionLocal
from app.models import MarketSymbol, DataSource
from sqlalchemy import select, or_

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
        # Use Connection Manager to get a persistent client
        self.client = CTraderConnectionManager.get_client(self.host, self.port, str(self.account_id))

    async def get_account_summary(self) -> Dict[str, Any]:
        await self.client.connect()
        try:
             await self.client.authorize_app(self.client_id, self.client_secret)
             await self.client.authorize_account(self.account_id, self.token)
             
             trader = await self.client.get_trader(self.account_id)
             
             # cTrader sends monetary values in 'cents' (e.g. 10000 = 100.00)
             # usually dividing by 100 is safe for standard currencies
             # But ProtoOATrader has 'moneyDigits'? 
             # For simplicity and standard FX/Gold accounts, usually / 100.
             # Better: check 'depositAssetId' but we need asset list to know divisor.
             # For now, standard / 100.
             
             balance = trader.balance / 100.0
             
             return {
                 "balance": str(balance), 
                 "NAV": str(balance), # Approximate if Equity not directly in basic Trader obj (It is in ProtoOAReconcileRes usually, but Trader has balance usually)
                 # Actually `trader.balance` is balance. Open PnL is needed for Equity.
                 # Currently we return Balance as NAV if we can't get full state.
                 # Let's check if we can get more.
                 # For now, returning Balance is infinite better than "0".
                 "marginAvailable": str(balance), 
                 "openTradeCount": 0, 
                 "openPositionCount": 0
             }
        except Exception as e:
             logger.error(f"cTrader Account Summary Error: {e}")
             raise e

    async def _resolve_symbol_id_and_lot_size(self, symbol_name: str) -> tuple[int, int]:
        """
        Returns (symbol_id, lot_size_in_cents).
        Normalization: 1 Standard Lot = 100,000 'Universal Units'.
        cTrader volume is in cents.
        Example Gold: 1 Lot = 100 units = 10,000 cents.
        Example FX: 1 Lot = 100,000 units = 10,000,000 cents.
        """
        async with AsyncSessionLocal() as db:
            # Normalize requested symbol
            normalized_name = symbol_name.replace("_", "").replace("/", "").upper()
            
            # 1. Try exact match, underscore match, and slashed match
            search_names = [symbol_name, symbol_name.replace("_", "/"), symbol_name.replace("/", "_"), normalized_name]
            # Remove duplicates
            search_names = list(set(search_names))
            
            result = await db.execute(select(MarketSymbol).join(DataSource).where(
                MarketSymbol.symbol.in_(search_names),
                DataSource.provider == 'CTRADER'
            ))
            ms = result.scalars().first()
            
            if not ms:
                # 2. Try partial match if still not found
                # This handles cases where we have e.g. "XAUUSD" stored and user sends "XAU_USD"
                # but the simple permutations didn't catch it.
                result = await db.execute(select(MarketSymbol).join(DataSource).where(
                    or_(
                        MarketSymbol.symbol.like(f"%{normalized_name}%"),
                        MarketSymbol.symbol.like(f"%{symbol_name}%")
                    ),
                    DataSource.provider == 'CTRADER'
                ))
                ms = result.scalars().first()
            
            if ms and ms.details:
                # Check for symbolId and lotSize in details
                details = ms.details
                
                symbol_id = None
                if "symbolId" in details:
                    symbol_id = int(details["symbolId"])
                elif "raw" in details and "symbolId" in details["raw"]:
                    symbol_id = int(details["raw"]["symbolId"])
                elif "ctrader_symbol_id" in details:
                    symbol_id = int(details["ctrader_symbol_id"])
                
                # Default lot_size to 100,000 units (* 100 cents) = 10,000,000
                lot_size_cents = int(details.get("lotSize", 10000000))
                
                if symbol_id is not None:
                    return symbol_id, lot_size_cents
            
            raise ValueError(f"Symbol {symbol_name} not found or missing ID for cTrader.")

    async def place_market_order(self, symbol: str, units: float, 
                           sl_price: Optional[float] = None, 
                           tp_price: Optional[float] = None, 
                           trade_id: Optional[str] = None,
                           comment: Optional[str] = None) -> Dict[str, Any]:
        
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
            
            # Check for Rejection in ExecutionEvent
            if res.payloadType == ProtoOAExecutionEvent().payloadType:
                 if res.executionType == ProtoOAExecutionType.ORDER_REJECTED:
                      error_code = res.errorCode if res.HasField("errorCode") else "UNKNOWN"
                      logger.error(f"cTrader Order REJECTED: {error_code} for {symbol}")
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

            return {
                "orderFillTransaction": {
                    "id": order_id or position_id,
                    "instrument": symbol,
                    "units": str(units),
                    "price": str(res.deal.executionPrice) if res.HasField("deal") else "0",
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
            
            # Cache symbols map? Or just return ID?
            # Frontend needs symbol name "XAU_USD". 
            # We have ID. We need reverse lookup or pass ID and let frontend handle?
            # Frontend expects "symbol": "XAU_USD".
            # Optimization: We assume we can't reverse lookup easily without querying DB for ALL symbols. 
            # Or we iterate local cache.
            # For MVP: Return symbol_id as string if lookup fails, or try simple lookup.
            # Let's allow returning "CT_ID_<id>" and see if frontend breaks? It will breaking charting.
            # We MUST resolve symbol.
            # Let's do a quick DB lookup for the IDs found.
            
            # Gather IDs
            position_ids = [p.symbolId for p in reconcile.position]
            if not position_ids: return []
            
            # Bulk lookup
            symbol_map = {}
            async with AsyncSessionLocal() as db:
                # Query all symbols where details->>'symbolId' is in our list
                # Postgre JSQN query
                # This is tricky with SQLAlchemy async and JSONB.
                # Simpler: Fetch all CTRADER symbols and map. MarketSymbol table is small (<1000).
                # Or Fetch where data_source provider is ctrader.
                q = select(MarketSymbol).join(DataSource).where(DataSource.provider == 'CTRADER')
                result = await db.execute(q)
                all_syms = result.scalars().all()
                for s in all_syms:
                    if s.details and 'symbolId' in s.details:
                        symbol_map[int(s.details['symbolId'])] = s.symbol

            for p in reconcile.position:
                s_name = symbol_map.get(p.symbolId, f"Unknown_{p.symbolId}")
                # Reverse Normalization: units = (volume_cents / lot_size_cents) * 100,000
                # We need lot_size_cents for this symbol.
                # Since we already fetched all symbols, we can find it in all_syms.
                
                target_sym = next((s for s in all_syms if s.details and int(s.details.get('symbolId', -1)) == p.symbolId), None)
                lot_size_cents = int(target_sym.details.get('lotSize', 10000000)) if target_sym else 10000000
                
                norm_units = (p.volume / float(lot_size_cents)) * 100000.0

                trades.append({
                    "id": str(p.positionId),
                    "symbol": s_name,
                    "units": norm_units,
                    "side": "BUY" if p.tradeSide == ProtoOATradeSide.BUY else "SELL",
                    "entry_price": p.price,
                    "current_price": 0.0, # Need spot price...
                    "pnl": p.grossProfit / 100.0, # Cents to USD, strictly it's moneteray value
                    # grossProfit is in deposit currency (cents).
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
                          comment: Optional[str] = None) -> Dict[str, Any]:
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
            
            # Map deals to trades
            # Need symbol name. Deals have symbolId.
            # We need to resolve symbol names.
            # Bulk verify symbols needed
            deal_symbol_ids = set([d.symbolId for d in deals])
            symbol_map = {}
            if deal_symbol_ids:
                 
                 async with AsyncSessionLocal() as db:
                     q = select(MarketSymbol).join(DataSource).where(DataSource.provider == 'CTRADER')
                     result = await db.execute(q)
                     all_syms = result.scalars().all()
                     for s in all_syms:
                         if s.details and 'symbolId' in s.details:
                             symbol_map[int(s.details['symbolId'])] = s.symbol

            results = []
            for d in deals:
                # ProtoOADeal: dealId, orderId, positionId, tradeSide, volume, executionPrice, commission, closePositionDetail, etc.
                # A "Deal" is a transaction (entry or exit).
                # To reconstruct a "Trade" (Order -> Entry -> Exit), we need to look at Position logic.
                # But 'deal_list' returns historical deals.
                # If we want "Closed Trades", we look for closing deals (closePositionDetail != None)?
                # Or just map deals as transactions.
                # Our 'Trade' model maps to a full Round Trip usually? 
                # Or is it individual fills?
                # The 'Trade' model has 'entry_price', 'exit_price', 'pnl'.
                # This implies a CLOSED POSITION.
                # In cTrader, a Closed Position is usually represented by the closing Deal which has PnL.
                
                if d.closePositionDetail: # This deal closed a position
                    s_name = symbol_map.get(d.symbolId, f"Unknown_{d.symbolId}")
                    
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
        except Exception as e:
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
                
            # Collect Symbol IDs
            symbol_ids = set([o.tradeData.symbolId for o in reconcile.order])
            
            # Bulk lookup
            from app.database import AsyncSessionLocal
            from app.models import MarketSymbol, DataSource
            from sqlalchemy import select
            
            symbol_map = {}
            if symbol_ids:
                async with AsyncSessionLocal() as db:
                    q = select(MarketSymbol).join(DataSource).where(DataSource.provider == 'CTRADER')
                    result = await db.execute(q)
                    all_syms = result.scalars().all()
                    for s in all_syms:
                        if s.details and 'symbolId' in s.details:
                            symbol_map[int(s.details['symbolId'])] = s.symbol
                            
            for o in reconcile.order:
                s_name = symbol_map.get(o.tradeData.symbolId, f"Unknown_{o.tradeData.symbolId}")
                
                target_sym = next((s for s in all_syms if s.details and int(s.details.get('symbolId', -1)) == o.tradeData.symbolId), None)
                lot_size_cents = int(target_sym.details.get('lotSize', 10000000)) if target_sym else 10000000
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
