from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

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
    async def place_market_order(self, symbol: str, units: float, 
                           sl_price: Optional[float] = None, 
                           tp_price: Optional[float] = None, 
                           trade_id: Optional[str] = None) -> Dict[str, Any]:
        """Place a market execution order."""
        pass

    @abstractmethod
    async def place_limit_order(self, symbol: str, units: float, entry_price: float,
                          sl_price: Optional[float] = None, 
                          tp_price: Optional[float] = None, 
                          time_in_force: str = "GTC",
                          trade_id: Optional[str] = None) -> Dict[str, Any]:
        """Place a limit order."""
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
