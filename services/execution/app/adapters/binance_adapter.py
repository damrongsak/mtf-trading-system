import time
import hmac
import hashlib
import httpx
from typing import Optional, Dict, Any, List
from app.adapters.base import BrokerAdapter
import logging

logger = logging.getLogger(__name__)

class BinanceAdapter(BrokerAdapter):
    def __init__(self, api_key: str, secret_key: str, is_live: bool = False):
        self.api_key = api_key
        self.secret_key = secret_key
        # Use Testnet if not live (check URLs)
        self.base_url = "https://api.binance.com" if is_live else "https://testnet.binance.vision"

    def _sign(self, params: Dict[str, Any]) -> str:
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        signature = hmac.new(
            self.secret_key.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        return signature

    async def get_account_summary(self) -> Dict[str, Any]:
        """
        Fetch account summary including NAV and margin availability.
        Note: Calculating exact NAV requires ticker prices for all assets.
        For MVP, we return USDT balance or empty.
        """
        endpoint = "/api/v3/account"
        params = {"timestamp": int(time.time() * 1000)}
        params['signature'] = self._sign(params)
        
        headers = {"X-MBX-APIKEY": self.api_key}
        
        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=10.0) as client:
                resp = await client.get(endpoint, headers=headers, params=params)
                
                if resp.status_code != 200:
                    logger.error(f"Binance API Error: {resp.text}")
                    # Return zero keys to avoid crashing frontend
                    return {
                        "balance": "0.00",
                        "NAV": "0.00",
                        "marginAvailable": "0.00",
                        "openTradeCount": 0,
                        "openPositionCount": 0
                    }
                
                data = resp.json()
                
                # Calculate Total Balance (USDT approximation)
                balances = data.get('balances', [])
                usdt_bal = next((b for b in balances if b['asset'] == 'USDT'), {'free': '0', 'locked': '0'})
                total_usdt = float(usdt_bal['free']) + float(usdt_bal['locked'])
                
                # Check for other significant assets?
                # For now just USDT
                
                return {
                    "balance": f"{total_usdt:.2f} USDT",
                    "NAV": f"{total_usdt:.2f} USDT", 
                    "marginAvailable": f"{usdt_bal['free']} USDT",
                    "openTradeCount": 0, # Need openOrders for this
                    "openPositionCount": len([b for b in balances if float(b['free']) > 0 or float(b['locked']) > 0])
                }
        except Exception as e:
            logger.error(f"Binance Account Summary Failed: {e}")
            # return fallback to avoid 500 crash
            return {
                "balance": "Error",
                "NAV": "Error",
                "marginAvailable": "Error",
                "openTradeCount": 0,
                "openPositionCount": 0
            }

    async def get_open_trades(self) -> List[Dict[str, Any]]:
        # Placeholder
        return []

    async def place_market_order(self, symbol: str, units: float, sl_price: Optional[float] = None, tp_price: Optional[float] = None, trade_id: Optional[str] = None, comment: Optional[str] = None, tag: Optional[str] = None) -> Dict[str, Any]:
        raise NotImplementedError("Binance Execution not yet implemented")

    async def place_limit_order(self, symbol: str, units: float, price: float,
                          sl_price: Optional[float] = None, 
                          tp_price: Optional[float] = None, 
                          time_in_force: str = "GTC",
                          trade_id: Optional[str] = None,
                          comment: Optional[str] = None,
                          tag: Optional[str] = None,
                          stop_price: Optional[float] = None,
                          order_type: Any = None) -> Dict[str, Any]:
        raise NotImplementedError("Binance Limit Order not yet implemented")

    async def get_order_book(self, symbol: str) -> Dict[str, Any]:
        # Placeholder
        return {"bids": [], "asks": []}

    async def close_trade(self, broker_trade_id: str, units: Optional[float] = None) -> Dict[str, Any]:
        raise NotImplementedError("Binance Execution not yet implemented")

    async def get_current_price(self, symbol: str) -> float:
        # Placeholder
        return 0.0
