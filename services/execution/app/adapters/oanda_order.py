from oandapyV20 import API
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.trades as trades
import oandapyV20.endpoints.accounts as accounts
import oandapyV20.endpoints.pricing as pricing
import oandapyV20.endpoints.instruments as instruments
from oandapyV20.exceptions import V20Error
from app.adapters.base import BrokerAdapter
import logging
from typing import List, Dict, Any, Optional
from fastapi.concurrency import run_in_threadpool
from datetime import datetime
from app.utils.normalization import parse_iso_timestamp, units_to_standard_lots

logger = logging.getLogger(__name__)

class OandaOrderAdapter(BrokerAdapter):
    def __init__(self, api_key: str, account_id: str, environment: str = "practice"):
        self.client = API(access_token=api_key, environment=environment)
        self.account_id = account_id

    async def get_account_summary(self) -> Dict[str, Any]:
        """Fetch account balance, margin, and summary metrics from OANDA."""
        try:
            r = accounts.AccountSummary(accountID=self.account_id)
            # Run blocking call in threadpool
            await run_in_threadpool(self.client.request, r)
            acc = r.response.get("account", {})
            
            # OANDA provides these as strings
            balance = float(acc.get("balance", "0"))
            equity = float(acc.get("NAV", "0"))
            used_margin = float(acc.get("marginUsed", "0"))
            free_margin = float(acc.get("marginAvailable", "0"))
            unrealized_net = float(acc.get("unrealizedPL", "0"))
            margin_call_pct = float(acc.get("marginCallPercent", "0")) * 100 if acc.get("marginCallPercent") else None
            
            return {
                "balance": balance,
                "equity": equity,
                "NAV": equity,
                "used_margin": used_margin,
                "marginUsed": used_margin,
                "free_margin": free_margin,
                "marginAvailable": free_margin,
                "margin_level": margin_call_pct,
                "unrealized_gross": unrealized_net, # OANDA usually combines these
                "unrealized_net": unrealized_net,
                "unrealizedPL": unrealized_net,
                "openTradeCount": int(acc.get("openTradeCount", 0)),
                "openPositionCount": int(acc.get("openPositionCount", 0))
            }
        except Exception as e:
            logger.error(f"OANDA Account Summary Error: {e}")
            raise e

    async def place_market_order(self, symbol: str, units: float, 
                           sl_price: Optional[float] = None, 
                           tp_price: Optional[float] = None, 
                           trade_id: Optional[str] = None,
                           comment: Optional[str] = None,
                           tag: Optional[str] = None) -> Dict[str, Any]:
        """
        Place a Market Order with optional SL/TP and Client Tags.
        """
        # Diagnostic logging for Unit Sign issue
        logger.info(f"OANDA: Placing market order for {symbol}, units={units}")
        
        # Ensure units is stringified correctly and preserves negative sign
        units_str = str(float(units))
        if units < 0 and not units_str.startswith("-"):
             # Extrememly rare edge case with some float types/libs, but better safe for HFT
             units_str = f"-{abs(units)}"
             logger.warning(f"OANDA: Corrected missing negative sign for units: {units_str}")

        order_body = {
            "order": {
                "type": "MARKET",
                "instrument": symbol,
                "units": units_str,
                "timeInForce": "FOK", # Fill or Kill for immediate execution
                "positionFill": "DEFAULT"
            }
        }

        # Add Bracket Orders (SL/TP)
        if sl_price:
            order_body["order"]["stopLossOnFill"] = {
                "price": str(sl_price),
                "timeInForce": "GTC" # Good Till Cancelled
            }
        
        if tp_price:
            order_body["order"]["takeProfitOnFill"] = {
                "price": str(tp_price),
                "timeInForce": "GTC"
            }

        # Add Client Tags (for reconciliation)
        if trade_id:
            client_ext = {
                "id": trade_id,
                "tag": tag if tag else "MTF_AUTO",
                "comment": comment if comment else "Automated entry via Execution Service"
            }
            order_body["order"]["clientExtensions"] = client_ext

        try:
            r = orders.OrderCreate(accountID=self.account_id, data=order_body)
            # Run blocking call in threadpool
            await run_in_threadpool(self.client.request, r)
            resp = r.response
            logger.info(f"OANDA Market Order Response: {resp}")
            
            # Check for immediate cancellation (e.g. STOP_LOSS_ON_FILL_LOSS)
            if "orderCancelTransaction" in resp:
                reason = resp.get("orderCancelTransaction", {}).get("reason", "UNKNOWN_CANCEL")
                msg = f"OANDA order cancelled immediately: {reason}"
                logger.error(msg)
                raise ValueError(msg)
                
            if "orderFillTransaction" not in resp:
                # If it's a Market order and not filled, it failed
                msg = "OANDA Market order failed to fill (no orderFillTransaction)"
                logger.error(msg)
                raise ValueError(msg)
                
            return resp
        except Exception as e:
            logger.error(f"Failed to place OANDA order for {symbol}: {e}")
            raise e

    async def place_limit_order(self, symbol: str, units: float, price: float,
                          sl_price: Optional[float] = None, 
                          tp_price: Optional[float] = None, 
                          time_in_force: str = "GTC",
                          trade_id: Optional[str] = None,
                          comment: Optional[str] = None,
                          tag: Optional[str] = None,
                          stop_price: Optional[float] = None,
                          order_type: Any = None) -> Dict[str, Any]:
        """
        Place a Limit or Stop Order with optional SL/TP.
        OANDA REST v20 handles STOP/LIMIT via the same endpoint but different 'type' in body.
        """
        # Diagnostic logging for Unit Sign issue
        logger.info(f"OANDA: Placing order for {symbol}, units={units}, price={price}, type={order_type}")

        units_str = str(float(units))
        if units < 0 and not units_str.startswith("-"):
             units_str = f"-{abs(units)}"

        # Determine OANDA order type
        oanda_type = "LIMIT"
        if order_type == "STOP":
             oanda_type = "STOP"
        elif order_type == "MARKET_IF_TOUCHED":
             oanda_type = "MARKET_IF_TOUCHED"
        
        # Note: OANDA STOP_LIMIT is not directly supported via a single 'STOP_LIMIT' type in the same way 
        # but can be simulated or ignored for now if not available in basic v20.
        # For simplicity, treat STOP_LIMIT as LIMIT or STOP if requested, or raise if unsupported.

        order_body = {
            "order": {
                "type": oanda_type,
                "instrument": symbol,
                "units": units_str,
                "price": str(price),
                "timeInForce": time_in_force,
                "positionFill": "DEFAULT"
            }
        }

        if sl_price:
            order_body["order"]["stopLossOnFill"] = {
                "price": str(sl_price),
                "timeInForce": "GTC"
            }
        
        if tp_price:
            order_body["order"]["takeProfitOnFill"] = {
                "price": str(tp_price),
                "timeInForce": "GTC"
            }

        if trade_id:
            order_body["order"]["clientExtensions"] = {
                "id": trade_id,
                "tag": tag if tag else "MTF_LIMIT",
                "comment": comment if comment else "Limit Order via MTF"
            }

        try:
            r = orders.OrderCreate(accountID=self.account_id, data=order_body)
            # Run blocking call in threadpool
            await run_in_threadpool(self.client.request, r)
            logger.info(f"OANDA Limit Order Response: {r.response}")
            return r.response
        except Exception as e:
            logger.error(f"Failed to place OANDA limit order for {symbol}: {e}")
            raise e

    async def get_order_book(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch order book snapshot from Oanda.
        """
        try:
            r = instruments.InstrumentOrderBook(instrument=symbol)
            # Run blocking call in threadpool
            await run_in_threadpool(self.client.request, r)
            return r.response.get("orderBook", {})
        except Exception as e:
            logger.error(f"Failed to fetch OANDA order book for {symbol}: {e}")
            raise e

    async def get_open_trades(self) -> List[Dict[str, Any]]:
        """
        Fetch all open trades from Oanda.
        """
        try:
            r = trades.TradesList(accountID=self.account_id, params={"state": "OPEN"})
            # Run blocking call in threadpool
            await run_in_threadpool(self.client.request, r)
            return r.response.get("trades", [])
        except Exception as e:
            logger.error(f"Failed to fetch open OANDA trades: {e}")
            raise e

    async def close_trade(self, broker_trade_id: str, units: Optional[float] = None) -> Dict[str, Any]:
        """
        Close an existing trade on OANDA.
        """
        try:
            # If units is None, OANDA closes the entire position by default if using TradeClose
            data = {}
            if units:
                data["units"] = str(abs(units))
            else:
                data["units"] = "ALL"

            r = trades.TradeClose(accountID=self.account_id, tradeID=broker_trade_id, data=data)
            # Run blocking call in threadpool
            await run_in_threadpool(self.client.request, r)
            return r.response
        except V20Error as e:
            # Handle idempotency: if trade is already closed, OANDA returns 404 (NO_SUCH_TRADE)
            if e.code == 404:
                logger.warning(f"OANDA Trade {broker_trade_id} already closed or not found (Idempotency).")
                return {"id": broker_trade_id, "status": "ALREADY_CLOSED"}
            logger.error(f"OANDA V20 Error closing trade {broker_trade_id}: {e}")
            raise e
        except Exception as e:
            logger.error(f"Failed to close OANDA trade {broker_trade_id}: {e}")
            raise e

    async def get_current_price(self, symbol: str) -> float:
        """
        Fetch the current market price (midpoint) for a symbol.
        """
        try:
            params = {"instruments": symbol}
            r = pricing.PricingInfo(accountID=self.account_id, params=params)
            # Run blocking call in threadpool
            await run_in_threadpool(self.client.request, r)
            
            prices = r.response.get("prices", [])
            if not prices:
                raise ValueError(f"No pricing data returned for {symbol}")
                
            price_data = prices[0]
            # Calculate mid price
            bid = float(price_data["bids"][0]["price"])
            ask = float(price_data["asks"][0]["price"])
            return (bid + ask) / 2.0
            
        except Exception as e:
            logger.error(f"Failed to fetch price for {symbol}: {e}")
            raise e




    async def get_trade_history(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """
        Fetch historical closed trades within a date range via OANDA API.
        LIMITATION: Fetches last 500 closed trades and filters client-side.
        """
        try:
            params = {
                "state": "CLOSED",
                "count": 500
            }
            r = trades.TradesList(accountID=self.account_id, params=params)
            await run_in_threadpool(self.client.request, r)
            
            raw_trades = r.response.get("trades", [])
            results = []
            
            for t in raw_trades:
                ct_str = t.get("closeTime")
                ot_str = t.get("openTime")
                if not ct_str: continue
                
                try:
                    close_dt = parse_iso_timestamp(ct_str)
                    open_dt = parse_iso_timestamp(ot_str) if ot_str else close_dt
                    
                    # Filtering by close time against start_date/end_date (assuming UTC)
                    if start_date <= close_dt <= end_date:
                        from app.models import TradeStatus, TradeDirection

                        initial_units = float(t.get("initialUnits", 0))
                        direction = TradeDirection.LONG if initial_units > 0 else TradeDirection.SHORT
                        
                        # Normalize to Standard Lots
                        std_lots = units_to_standard_lots(abs(initial_units))

                        results.append({
                            "trade_id": str(t.get("id")),
                            "symbol": t.get("instrument"),
                            "strategy_name": "Imported",
                            "signal_timestamp": open_dt,
                            "status": TradeStatus.CLOSED,
                            "direction": direction,
                            "entry_price": float(t.get("price", 0)),
                            "exit_price": float(t.get("averageClosePrice", 0)),
                            "sl_price": 0.0, 
                            "tp_price": 0.0,
                            "lot_size": std_lots,
                            "risk_usd": 0.0,
                            "pnl_usd": float(t.get("realizedPL", 0)),
                            "exit_timestamp": close_dt,
                            "metadata_json": {"raw": t}
                        })
                except Exception as parse_e:
                    logger.warning(f"OANDA: Failed to process trade history item {ct_str}: {parse_e}")
                    continue
                    
            return results
        except Exception as e:
            logger.error(f"OANDA Trade History Error: {e}")
            raise e

    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel a pending order on OANDA.
        """
        try:
            r = orders.OrderCancel(accountID=self.account_id, orderID=order_id)
            # Run blocking call in threadpool
            await run_in_threadpool(self.client.request, r)
            return r.response
        except V20Error as e:
            # Handle idempotency: if order is already cancelled/filled, OANDA might return 404
            if e.code == 404:
                logger.warning(f"OANDA Order {order_id} already cancelled or not found (Idempotency).")
                return {"id": order_id, "status": "ALREADY_CANCELLED"}
            raise e
        except Exception as e:
            logger.error(f"Failed to cancel OANDA order {order_id}: {e}")
            raise e

    async def get_pending_orders(self) -> List[Dict[str, Any]]:
        """
        Fetch all pending orders (LIMIT, STOP, MARKET_IF_TOUCHED) from OANDA.
        """
        try:
            r = orders.OrdersPending(accountID=self.account_id)
            await run_in_threadpool(self.client.request, r)
            pending = r.response.get("orders", [])
            for o in pending:
                o["status"] = "PENDING"
            return pending
        except Exception as e:
            logger.error(f"Failed to fetch pending OANDA orders: {e}")
            raise e

    async def amend_order(self, order_id: str, units: Optional[float] = None, 
                    price: Optional[float] = None, 
                    sl_price: Optional[float] = None, 
                    tp_price: Optional[float] = None,
                    stop_price: Optional[float] = None,
                    trailing_sl: Optional[bool] = None) -> Dict[str, Any]:
        """
        Amend a pending order on OANDA by replacing it.
        Requires fetching the existing order first if partial update.
        """
        try:
            # For OANDA OrderReplace, we must provide the full order payload.
            # We fetch the current state first.
            pending = await self.get_pending_orders()
            target = next((o for o in pending if o["id"] == order_id), None)
            if not target:
                raise ValueError(f"Order {order_id} not found to amend")

            # Deep copy or construct new payload from target
            order_body = {"order": {
                "type": target.get("type", "LIMIT"),
                "instrument": target["instrument"],
                "units": str(float(units)) if units is not None else target["units"],
                "timeInForce": target.get("timeInForce", "GTC")
            }}
            
            # Use new price or existing price
            if price is not None:
                order_body["order"]["price"] = str(price)
            elif "price" in target:
                order_body["order"]["price"] = target["price"]

            # SL
            new_sl = sl_price if sl_price is not None else float(target.get("stopLossOnFill", {}).get("price", 0))
            if new_sl > 0:
                order_body["order"]["stopLossOnFill"] = {"price": str(new_sl), "timeInForce": "GTC"}

            # TP
            new_tp = tp_price if tp_price is not None else float(target.get("takeProfitOnFill", {}).get("price", 0))
            if new_tp > 0:
                order_body["order"]["takeProfitOnFill"] = {"price": str(new_tp), "timeInForce": "GTC"}

            r = orders.OrderReplace(accountID=self.account_id, orderID=order_id, data=order_body)
            await run_in_threadpool(self.client.request, r)
            
            new_order_id = r.response.get("orderCreateTransaction", {}).get("id", order_id)
            return {"status": "amended", "order_id": new_order_id}

        except ValueError as ve:
            raise ve
        except Exception as e:
            # OANDA returns HTTP 404 for order not found if we didn't catch it
            if "Order doesn't exist" in str(e) or "404" in str(e):
                raise ValueError(f"Order {order_id} not found")
            logger.error(f"Failed to amend OANDA order {order_id}: {e}")
            raise e

    async def amend_position(self, broker_trade_id: str, 
                        sl_price: Optional[float] = None, 
                        tp_price: Optional[float] = None,
                        trailing_sl: Optional[bool] = None,
                        units: Optional[float] = None) -> Dict[str, Any]:
        """
        Amend an open trade's SL/TP on OANDA using TradeCRCDO.
        """
        try:
            data = {}
            if sl_price is not None:
                data["stopLoss"] = {"price": str(sl_price), "timeInForce": "GTC"}
            if tp_price is not None:
                data["takeProfit"] = {"price": str(tp_price), "timeInForce": "GTC"}

            if not data:
                return {"status": "no_changes_requested", "position_id": broker_trade_id}

            r = trades.TradeCRCDO(accountID=self.account_id, tradeID=broker_trade_id, data=data)
            await run_in_threadpool(self.client.request, r)
            return {"status": "amended", "position_id": broker_trade_id}

        except Exception as e:
            if "Trade doesn't exist" in str(e) or "NoSuchTrade" in str(e) or "404" in str(e):
                raise ValueError(f"Position/Trade {broker_trade_id} not found")
            logger.error(f"Failed to amend OANDA position {broker_trade_id}: {e}")
            raise e

    async def get_order_book(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch Order Book for OANDA. 
        NOTE: OANDA REST v20 provides historical sentiment (OrderBook) but not real-time L2 depth 
        via REST. We return the Top-of-Book (Spot) price as a 1-level depth book for parity.
        """
        try:
            params = {"instruments": symbol}
            r = pricing.PricingInfo(accountID=self.account_id, params=params)
            await run_in_threadpool(self.client.request, r)
            
            prices = r.response.get("prices", [])
            if not prices:
                return {"bids": [], "asks": []}
            
            p = prices[0]
            # OANDA prices are strings in v20
            bids = [{"price": float(b.get("price")), "volume": 0.0} for b in p.get("bids", [])]
            asks = [{"price": float(a.get("price")), "volume": 0.0} for a in p.get("asks", [])]
            
            return {"bids": bids, "asks": asks}
        except Exception as e:
            logger.error(f"OANDA Get Order Book (Top-of-Book) Error: {e}")
            return {"bids": [], "asks": []}
