from oandapyV20 import API
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.trades as trades
import oandapyV20.endpoints.accounts as accounts
import oandapyV20.endpoints.pricing as pricing
import oandapyV20.endpoints.instruments as instruments
from app.adapters.base import BrokerAdapter
import logging
from typing import List, Dict, Any, Optional
from typing import List, Dict, Any, Optional
from fastapi.concurrency import run_in_threadpool
from datetime import datetime

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
            return {
                "balance": acc.get("balance", "0"),
                "NAV": acc.get("NAV", "0"),
                "marginAvailable": acc.get("marginAvailable", "0"),
                "openTradeCount": acc.get("openTradeCount", 0),
                "openPositionCount": acc.get("openPositionCount", 0)
            }
        except Exception as e:
            logger.error(f"OANDA Account Summary Error: {e}")
            raise e

    async def place_market_order(self, symbol: str, units: float, 
                           sl_price: Optional[float] = None, 
                           tp_price: Optional[float] = None, 
                           trade_id: Optional[str] = None) -> Dict[str, Any]:
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
                "tag": "MTF_AUTO",
                "comment": "Automated entry via Execution Service"
            }
            order_body["order"]["clientExtensions"] = client_ext

        try:
            r = orders.OrderCreate(accountID=self.account_id, data=order_body)
            # Run blocking call in threadpool
            await run_in_threadpool(self.client.request, r)
            return r.response
        except Exception as e:
            logger.error(f"Failed to place OANDA order for {symbol}: {e}")
            raise e

    async def place_limit_order(self, symbol: str, units: float, entry_price: float,
                          sl_price: Optional[float] = None, 
                          tp_price: Optional[float] = None, 
                          time_in_force: str = "GTC",
                          trade_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Place a Limit Order with optional SL/TP.
        """
        # Diagnostic logging for Unit Sign issue
        logger.info(f"OANDA: Placing limit order for {symbol}, units={units}, price={entry_price}")

        units_str = str(float(units))
        if units < 0 and not units_str.startswith("-"):
             units_str = f"-{abs(units)}"

        order_body = {
            "order": {
                "type": "LIMIT",
                "instrument": symbol,
                "units": units_str,
                "price": str(entry_price),
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
                "tag": "MTF_LIMIT",
                "comment": "Limit Order via MTF"
            }

        try:
            r = orders.OrderCreate(accountID=self.account_id, data=order_body)
            # Run blocking call in threadpool
            await run_in_threadpool(self.client.request, r)
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
                ct_str = t.get("closeTime", "")
                if not ct_str: continue
                
                # Parse "2016-06-22T18:41:35.433291884Z" -> remove fractions for simple parse
                # Using simple string slice to avoid libraries if possible
                try:
                    ts_clean = ct_str.split(".")[0] # "2016-06-22T18:41:35"
                    dt = datetime.strptime(ts_clean, "%Y-%m-%dT%H:%M:%S")
                    # Assuming naive UTC
                    
                    if start_date <= dt <= end_date:
                        from app.models import TradeStatus, TradeDirection

                        initial_units = float(t.get("initialUnits", 0))
                        direction = TradeDirection.LONG if initial_units > 0 else TradeDirection.SHORT
                        
                        results.append({
                            "trade_id": t.get("id"),
                            "symbol": t.get("instrument"),
                            "strategy_name": "Imported",
                            "signal_timestamp": dt, # Use close time as signal time for imported? Or 'openTime'
                            "signal_timestamp": dt, # Fallback
                            "status": TradeStatus.CLOSED,
                            "direction": direction,
                            "entry_price": float(t.get("price", 0)),
                            "exit_price": float(t.get("averageClosePrice", 0)),
                            "sl_price": 0.0, # Not always available
                            "tp_price": 0.0,
                            "lot_size": abs(initial_units),
                            "risk_usd": 0.0,
                            "pnl_usd": float(t.get("realizedPL", 0)),
                            "exit_timestamp": dt,
                            "metadata_json": {"raw": t}
                        })
                except Exception as parse_e:
                    logger.warning(f"Failed to parse trade time {ct_str}: {parse_e}")
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
            await run_in_threadpool(self.client.request, r)
            return r.response
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
