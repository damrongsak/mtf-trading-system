from app.adapters.base import BrokerAdapter
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime

class MockAdapter(BrokerAdapter):
    """
    Mock Adapter for simulating broker interactions.
    """
    def __init__(self, **kwargs):
        self.balance = 100000.0
        self.equity = 100000.0
        self.margin = 0.0

    async def get_account_summary(self) -> Dict[str, Any]:
        return {
            "balance": str(self.balance),
            "NAV": str(self.equity),
            "equity": str(self.equity),
            "marginAvailable": str(self.equity - self.margin),
            "margin_used": str(self.margin),
            "openTradeCount": 0,
            "openPositionCount": 0,
            "open_positions": [], # For detail view
            "currency": "USD" 
        }

    async def get_open_trades(self) -> List[Dict[str, Any]]:
        return []

    async def place_market_order(self, symbol: str, units: float, 
                           sl_price: Optional[float] = None, 
                           tp_price: Optional[float] = None, 
                           trade_id: Optional[str] = None) -> Dict[str, Any]:
        
        mock_id = str(uuid.uuid4())
        price = self.get_current_price(symbol)
        
        return {
            "orderFillTransaction": {
                "id": mock_id,
                "instrument": symbol,
                "units": str(units),
                "price": str(price),
                "time": datetime.utcnow().isoformat(),
                "pl": "0.0",
                "financing": "0.0",
                "commission": "0.0",
                "accountBalance": str(self.balance),
            }
        }

    async def place_limit_order(self, symbol: str, units: float, entry_price: float,
                          sl_price: Optional[float] = None, 
                          tp_price: Optional[float] = None, 
                          time_in_force: str = "GTC",
                          trade_id: Optional[str] = None) -> Dict[str, Any]:
        mock_id = str(uuid.uuid4())
        return {
            "orderCreateTransaction": {
                "id": mock_id,
                "instrument": symbol,
                "units": str(units),
                "price": str(entry_price),
                "time": datetime.utcnow().isoformat(),
                "timeInForce": time_in_force
            }
        }

    async def get_order_book(self, symbol: str) -> Dict[str, Any]:
        return {
            "bids": [{"price": str(self.get_current_price(symbol)-0.1), "liquidity": "1000000"}],
            "asks": [{"price": str(self.get_current_price(symbol)+0.1), "liquidity": "1000000"}]
        }

    async def close_trade(self, broker_trade_id: str, units: Optional[float] = None) -> Dict[str, Any]:
        return {
            "tradeCloseTransaction": {
                "tradeID": broker_trade_id,
                "price": "2000.00",
                "units": str(units) if units else "ALL",
                "pl": "50.00"
            }
        }

    async def get_current_price(self, symbol: str) -> float:
        # Static prices for testing
        if "XAU" in symbol:
            return 2650.00
        elif "EUR" in symbol:
            return 1.0500
        elif "JPY" in symbol:
            return 150.00
        return 100.00
    
    # Optional dynamic method if needed
    def get_summary(self):
        return self.get_account_summary()
