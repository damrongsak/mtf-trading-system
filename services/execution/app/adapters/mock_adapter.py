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

    async def place_market_order(self, symbol: str, units: float, side: str,
                           sl_price: Optional[float] = None, 
                           tp_price: Optional[float] = None, 
                           trade_id: Optional[str] = None,
                           comment: Optional[str] = None,
                           tag: Optional[str] = None) -> Dict[str, Any]:
        
        mock_id = str(uuid.uuid4())
        price = await self.get_current_price(symbol)
        
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

    async def place_limit_order(self, symbol: str, units: float, side: str, price: float,
                          sl_price: Optional[float] = None, 
                          tp_price: Optional[float] = None, 
                          time_in_force: str = "GTC",
                          trade_id: Optional[str] = None,
                          comment: Optional[str] = None,
                          tag: Optional[str] = None,
                          stop_price: Optional[float] = None,
                          order_type: Any = None) -> Dict[str, Any]:
        mock_id = str(uuid.uuid4())
        # Store the trade internally
        self.trades[mock_id] = {
            "id": mock_id,
            "instrument": symbol,
            "units": units,
            "side": side,
            "price": price,
            "time": datetime.utcnow().isoformat(),
            "sl_price": sl_price,
            "tp_price": tp_price,
            "stop_price": stop_price,
            "time_in_force": time_in_force,
            "type": str(order_type) if order_type else "LIMIT",
            "status": "PENDING"
        }
        return {
            "orderCreateTransaction": {
                "id": mock_id,
                "instrument": symbol,
                "units": str(units),
                "price": str(price),
                "stopPrice": str(stop_price) if stop_price else None,
                "time": datetime.utcnow().isoformat(),
                "timeInForce": time_in_force,
                "type": str(order_type) if order_type else "LIMIT"
            }
        }

    async def get_order_book(self, symbol: str) -> Dict[str, Any]:
        price = await self.get_current_price(symbol)
        return {
            "bids": [{"price": str(price - 0.1), "liquidity": "1000000"}],
            "asks": [{"price": str(price + 0.1), "liquidity": "1000000"}]
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
            return 2050.00
        elif "EUR" in symbol:
            return 1.0500
        elif "JPY" in symbol:
            return 150.00
        return 100.00

    async def get_trade_history(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        # Return some mock trades
        return [
            {
                "trade_id": str(uuid.uuid4()),
                "symbol": "XAU_USD",
                "strategy_name": "Manual",
                "signal_timestamp": datetime.utcnow(),
                "status": "CLOSED",
                "direction": "LONG",
                "entry_price": 2000.0,
                "exit_price": 2010.0,
                "sl_price": 1990.0,
                "tp_price": 2020.0,
                "lot_size": 0.1,
                "risk_usd": 10.0,
                "pnl_usd": 100.0,
                "exit_timestamp": datetime.utcnow()
            }
        ]
    
    async def get_pending_orders(self) -> List[Dict[str, Any]]:
        """
        Fetch all mock pending orders.
        """
        return [
            {
                "id": str(uuid.uuid4()),
                "instrument": "XAU_USD",
                "units": "10",
                "price": "2600.00",
                "time": datetime.utcnow().isoformat(),
                "status": "PENDING"
            }
        ]
    
    # Optional dynamic method if needed
    async def get_summary(self):
        return await self.get_account_summary()

    async def amend_position(self, broker_trade_id: str, 
                        sl_price: Optional[float] = None, 
                        tp_price: Optional[float] = None,
                        trailing_sl: Optional[bool] = None,
                        units: Optional[float] = None) -> Dict[str, Any]:
        return {"status": "amended", "position_id": broker_trade_id}
