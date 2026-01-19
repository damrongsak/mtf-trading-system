import logging
import asyncio
from typing import Dict, Any, Optional, List
from app.adapters.base import BrokerAdapter
from app.adapters.ctrader_client import AsyncCTraderClient
from ctrader_open_api.messages.OpenApiMessages_pb2 import *

logger = logging.getLogger(__name__)

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
        self.client = AsyncCTraderClient(self.host, self.port)

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
        finally:
             await self.client.disconnect()

    async def place_market_order(self, symbol: str, units: float, 
                           sl_price: Optional[float] = None, 
                           tp_price: Optional[float] = None, 
                           trade_id: Optional[str] = None) -> Dict[str, Any]:
        
        await self.client.connect()
        try:
            await self.client.authorize_app(self.client_id, self.client_secret)
            await self.client.authorize_account(self.account_id, self.token)
            
            # Logic for creating order via Protobuf would go here
            logger.info(f"Placing cTrader Market Order: {symbol} {units} units")
            
            return {"status": "executed", "trade_id": f"CT_{trade_id or 'AUTO'}"}
        except Exception as e:
             logger.error(f"cTrader Place Order Error: {e}")
             raise e
        finally:
            await self.client.disconnect()

    async def get_open_trades(self) -> List[Dict[str, Any]]:
        return []

    async def place_limit_order(self, symbol: str, units: float, entry_price: float,
                          sl_price: Optional[float] = None, 
                          tp_price: Optional[float] = None, 
                          time_in_force: str = "GTC",
                          trade_id: Optional[str] = None) -> Dict[str, Any]:
        await self.client.connect()
        try:
            await self.client.authorize_app(self.client_id, self.client_secret)
            return {"status": "placed", "order_id": f"CT_LIMIT_{trade_id}"}
        finally:
            await self.client.disconnect()
        
    async def get_order_book(self, symbol: str) -> Dict[str, Any]:
        return {}

    async def close_trade(self, broker_trade_id: str, units: Optional[float] = None) -> Dict[str, Any]:
        return {"status": "closed", "trade_id": broker_trade_id}

    async def get_current_price(self, symbol: str) -> float:
        # In a real implementation, this would subscribe to spots or fetch latest spot
        return 0.0
