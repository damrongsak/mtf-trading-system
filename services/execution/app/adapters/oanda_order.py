from oandapyV20 import API
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.trades as trades
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class OandaOrderAdapter:
    def __init__(self):
        self.client = API(access_token=settings.OANDA_API_KEY, environment=settings.OANDA_ENV)
        self.account_id = settings.OANDA_ACCOUNT_ID

    def place_market_order(self, symbol: str, units: float, sl_price: float = None, tp_price: float = None, trade_id: str = None):
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
            logger.error(f"Failed to place order for {symbol}: {e}")
            raise e

    def get_open_trades(self):
        """
        Fetch all open trades from Oanda.
        """
        try:
            r = trades.TradesList(accountID=self.account_id, params={"state": "OPEN"})
            self.client.request(r)
            return r.response.get("trades", [])
        except Exception as e:
            logger.error(f"Failed to fetch open trades: {e}")
            raise e

