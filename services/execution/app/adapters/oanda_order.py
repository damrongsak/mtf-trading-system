from oandapyV20 import API
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.trades as trades
import oandapyV20.endpoints.accounts as accounts
import oandapyV20.endpoints.pricing as pricing
import oandapyV20.endpoints.instruments as instruments
from app.adapters.base import BrokerAdapter
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class OandaOrderAdapter(BrokerAdapter):
    def __init__(self, api_key: str, account_id: str, environment: str = "practice"):
        self.client = API(access_token=api_key, environment=environment)
        self.account_id = account_id

    async def get_account_summary(self) -> Dict[str, Any]:
        """Fetch account balance, margin, and summary metrics from OANDA."""
        try:
            r = accounts.AccountSummary(accountID=self.account_id)
            self.client.request(r)
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
        order_body = {
            "order": {
                "type": "MARKET",
                "instrument": symbol,
                "units": str(units),
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
            self.client.request(r)
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
        order_body = {
            "order": {
                "type": "LIMIT",
                "instrument": symbol,
                "units": str(units),
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
            self.client.request(r)
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
            self.client.request(r)
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
            self.client.request(r)
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
            self.client.request(r)
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
            self.client.request(r)
            
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


