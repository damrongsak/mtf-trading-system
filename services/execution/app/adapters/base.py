from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime

class BrokerAdapter(ABC):
    """
    Abstract Base Class for all broker integrations.
    Defines the standard interface for trading operations.
    """

    @abstractmethod
    async def get_account_summary(self) -> Dict[str, Any]:
        """Fetch account balance, margin, and summary metrics."""
        pass

    @abstractmethod
    async def get_open_trades(self) -> List[Dict[str, Any]]:
        """Fetch currently active trades/positions."""
        pass

    @abstractmethod
    async def place_market_order(self, symbol: str, units: float, side: str,
                           sl_price: Optional[float] = None, 
                           tp_price: Optional[float] = None, 
                           trade_id: Optional[str] = None,
                           comment: Optional[str] = None,
                           tag: Optional[str] = None) -> Dict[str, Any]:
        """Place a market execution order."""
        pass

    @abstractmethod
    async def place_limit_order(self, symbol: str, units: float, side: str, price: float,
                          sl_price: Optional[float] = None, 
                          tp_price: Optional[float] = None, 
                          time_in_force: str = "GTC",
                          trade_id: Optional[str] = None,
                          comment: Optional[str] = None,
                          tag: Optional[str] = None,
                          stop_price: Optional[float] = None,
                          order_type: Any = None) -> Dict[str, Any]:
        """Place a limit, stop, or stop-limit order."""
        pass

    @abstractmethod
    async def get_order_book(self, symbol: str) -> Dict[str, Any]:
        """Fetch order book snapshot."""
        pass

    @abstractmethod
    async def close_trade(self, broker_trade_id: str, units: Optional[float] = None) -> Dict[str, Any]:
        """Close an existing trade."""
        pass

    @abstractmethod
    async def get_current_price(self, symbol: str) -> float:
        """
        Fetch the current market price for a symbol.
        Used for risk calculation (distance to SL).
        """
        pass

    @abstractmethod
    async def get_trade_history(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """
        Fetch historical closed trades within a date range.
        Returns a list of dicts mapped to the system's Trade model fields.
        """
        pass

    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel a pending order.
        Optional to implement.
        """
        raise NotImplementedError("Cancel order not implemented for this broker")

    async def get_pending_orders(self) -> List[Dict[str, Any]]:
        """
        Fetch all pending orders.
        Optional to implement.
        """
        raise NotImplementedError("Get pending orders not implemented for this broker")

    async def amend_order(self, order_id: str, units: Optional[float] = None, 
                    price: Optional[float] = None, 
                    sl_price: Optional[float] = None, 
                    tp_price: Optional[float] = None,
                    stop_price: Optional[float] = None,
                    trailing_sl: Optional[bool] = None) -> Dict[str, Any]:
        """
        Amend a pending order (units, price, SL, TP, Stop Price, Trailing SL).
        """
        raise NotImplementedError("Amend order not implemented for this broker")

    async def amend_position(self, broker_trade_id: str, 
                        sl_price: Optional[float] = None, 
                        tp_price: Optional[float] = None,
                        trailing_sl: Optional[bool] = None,
                        units: Optional[float] = None) -> Dict[str, Any]:
        """
        Amend an open position (SL, TP, Trailing SL, Partial Close).
        """
        raise NotImplementedError("Amend position not implemented for this broker")
