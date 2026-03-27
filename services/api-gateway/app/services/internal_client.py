import httpx
import os
from typing import Dict, Any, List, Optional
import logging
from app.utils.http_client import get_internal_client

logger = logging.getLogger(__name__)

STRATEGY_CORE_URL = os.getenv("STRATEGY_CORE_URL", "http://strategy-core:8000")
EXECUTION_SERVICE_URL = os.getenv("EXECUTION_SERVICE_URL", "http://execution:8000")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "dev_secret_key")

class BaseInternalClient:
    """Base class for internal service clients with a persistent AsyncClient."""
    
    _client_instance: Optional[httpx.AsyncClient] = None

    def __init__(self, base_url: str, headers: Optional[Dict[str, str]] = None):
        self.base_url = base_url
        self.headers = headers or {}

    @classmethod
    async def get_shared_client(cls) -> httpx.AsyncClient:
        if cls._client_instance is None or cls._client_instance.is_closed:
            # Using standard transport with retries for internal reliability
            transport = httpx.AsyncHTTPTransport(retries=3, trust_env=False)
            cls._client_instance = httpx.AsyncClient(
                transport=transport,
                timeout=600.0,
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
            )
        return cls._client_instance

    async def _request(
        self, 
        method: str, 
        path: str, 
        timeout: Optional[float] = None, 
        **kwargs
    ) -> httpx.Response:
        client = await self.get_shared_client()
        url = f"{self.base_url}{path}"
        
        # Merge headers
        request_headers = self.headers.copy()
        if "headers" in kwargs:
            request_headers.update(kwargs.pop("headers"))
            
        resp = await client.request(
            method, 
            url, 
            timeout=timeout, 
            headers=request_headers, 
            **kwargs
        )
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            # Distinguish between client errors (Expected rejections) and server errors (Failures)
            if e.response.status_code < 500:
                logger.warning(f"Internal Service Validation ({method} {path}): {e.response.status_code} - See detail in router logs")
            else:
                logger.error(f"Internal Service Failure ({method} {path}): {e.response.status_code} - {e.response.text}")
            raise e
        return resp

class StrategyClient(BaseInternalClient):
    def __init__(self):
        super().__init__(STRATEGY_CORE_URL)

    async def run_backtest(self, req: Dict[str, Any]) -> Dict[str, Any]:
        try:
            logger.info(f"Sending backtest request to {self.base_url}/api/v1/backtest")
            resp = await self._request("POST", "/api/v1/backtest", json=req, timeout=60.0)
            return resp.json()
        except Exception as e:
            logger.error(f"Backtest request failed: {e}", exc_info=True)
            raise

    async def run_custom_backtest(self, req: Dict[str, Any]) -> Dict[str, Any]:
        try:
            logger.info(f"Sending custom backtest request to {self.base_url}/api/v1/backtest/custom")
            resp = await self._request("POST", "/api/v1/backtest/custom", json=req, timeout=600.0)
            return resp.json()
        except Exception as e:
            logger.error(f"Custom backtest failed: {e}", exc_info=True)
            raise

    async def run_optimization(self, req: Dict[str, Any]) -> Dict[str, Any]:
        try:
            logger.info(f"Sending optimization request to {self.base_url}/api/v1/backtest/optimize")
            resp = await self._request("POST", "/api/v1/backtest/optimize", json=req, timeout=300.0)
            return resp.json()
        except Exception as e:
            logger.error(f"Optimization request failed: {e}", exc_info=True)
            raise

    async def run_monte_carlo(self, req: Dict[str, Any]) -> Dict[str, Any]:
        try:
            logger.info(f"Sending Monte Carlo request to {self.base_url}/api/v1/backtest/monte-carlo")
            resp = await self._request("POST", "/api/v1/backtest/monte-carlo", json=req, timeout=60.0)
            return resp.json()
        except Exception as e:
            logger.error(f"Monte Carlo request failed: {e}", exc_info=True)
            raise

    async def start_strategy(self, strategy_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        try:
            logger.info(f"Starting strategy {strategy_id} via {self.base_url}")
            resp = await self._request("POST", f"/api/v1/strategies/{strategy_id}/start", json=config, timeout=10.0)
            return resp.json()
        except Exception as e:
            logger.error(f"Start strategy failed: {e}", exc_info=True)
            raise

    async def stop_strategy(self, strategy_id: str) -> Dict[str, Any]:
        try:
            logger.info(f"Stopping strategy {strategy_id} via {self.base_url}")
            resp = await self._request("POST", f"/api/v1/strategies/{strategy_id}/stop", timeout=10.0)
            return resp.json()
        except Exception as e:
            logger.error(f"Stop strategy failed: {e}", exc_info=True)
            raise

    async def get_volatility(self, symbol: str, timeframe: str, limit: int) -> Dict[str, Any]:
        resp = await self._request(
            "GET",
            "/api/v1/analytics/volatility",
            params={"symbol": symbol, "timeframe": timeframe, "limit": limit},
            timeout=10.0
        )
        return resp.json()

    async def get_var(self, symbol: str, timeframe: str, limit: int) -> Dict[str, Any]:
        resp = await self._request(
            "GET",
            "/api/v1/analytics/var",
            params={"symbol": symbol, "timeframe": timeframe, "limit": limit},
            timeout=10.0
        )
        return resp.json()

    async def get_factors(self, symbol: str, timeframe: str, limit: int) -> Dict[str, Any]:
        resp = await self._request(
            "GET",
            "/api/v1/analytics/factors",
            params={"symbol": symbol, "timeframe": timeframe, "limit": limit},
            timeout=10.0
        )
        return resp.json()

    async def list_active_strategies(self) -> Dict[str, Any]:
        try:
            resp = await self._request("GET", "/api/v1/strategies/active", timeout=10.0)
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to fetch active strategies: {e}")
            raise

    async def trigger_manual_tick(self, strategy_id: str) -> Dict[str, Any]:
        try:
            resp = await self._request("POST", f"/api/v1/strategies/{strategy_id}/tick", timeout=15.0)
            return resp.json()
        except Exception as e:
            logger.error(f"Manual tick failed for {strategy_id}: {e}")
            raise

    async def get_strategy_logs(self, strategy_id: str, limit: int = 50) -> Dict[str, Any]:
        try:
            resp = await self._request(
                "GET", f"/api/v1/strategies/{strategy_id}/logs", 
                params={"limit": limit},
                timeout=10.0
            )
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to fetch strategy logs for {strategy_id}: {e}")
            raise

    async def get_drawdown(self, symbol: str, timeframe: str, limit: int) -> Dict[str, Any]:
        resp = await self._request(
            "GET",
            "/api/v1/analytics/drawdown",
            params={"symbol": symbol, "timeframe": timeframe, "limit": limit},
            timeout=10.0
        )
        return resp.json()

class ExecutionClient(BaseInternalClient):
    def __init__(self):
        super().__init__(
            EXECUTION_SERVICE_URL, 
            headers={"X-Internal-API-Key": INTERNAL_API_KEY}
        )

    async def get_account_summary(self, broker_account_id: str) -> Dict[str, Any]:
        try:
            resp = await self._request(
                "POST", "/account/summary",
                json={"broker_account_id": str(broker_account_id)},
                timeout=30.0
            )
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to get account summary: {e}")
            raise

    async def place_order(self, order_data: Dict[str, Any], broker_account_id: Optional[str] = None) -> Dict[str, Any]:
        try:
            if broker_account_id:
                order_data["broker_account_id"] = str(broker_account_id)
            resp = await self._request("POST", "/orders", json=order_data, timeout=30.0)
            return resp.json().get("data", {})
        except httpx.HTTPStatusError:
            # Silence redundant ERROR logging for validation failures here; handled by _request (WARNING) and router.
            raise
        except Exception as e:
            logger.error(f"Failed to place order (System Error): {e}")
            raise

    async def get_trades(self, broker_account_id: str) -> List[Dict[str, Any]]:
        try:
            resp = await self._request(
                "GET", "/trades", 
                params={"broker_account_id": str(broker_account_id)},
                timeout=30.0
            )
            return resp.json().get("data", [])
        except Exception as e:
            logger.error(f"Failed to fetch trades: {e}")
            raise

    async def get_trade_details(self, trade_id: str, broker_account_id: str) -> Dict[str, Any]:
        try:
            resp = await self._request(
                "GET", f"/trades/{trade_id}", 
                params={"broker_account_id": str(broker_account_id)},
                timeout=30.0
            )
            return resp.json().get("data", {})
        except Exception as e:
            logger.error(f"Failed to fetch trade details: {e}")
            raise

    async def close_trade(self, trade_id: str, broker_account_id: str, units: Optional[float] = None) -> Dict[str, Any]:
        try:
            payload = {"broker_account_id": str(broker_account_id), "broker_trade_id": str(trade_id)}
            if units is not None:
                payload["units"] = units
            resp = await self._request("POST", "/trades/close", json=payload, timeout=30.0)
            return resp.json().get("data", {})
        except Exception as e:
            logger.error(f"Failed to close trade: {e}")
            raise

    async def place_smart_order(self, smart_order_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            resp = await self._request("POST", "/smart-orders", json=smart_order_data, timeout=30.0)
            return resp.json().get("data", {})
        except Exception as e:
            logger.error(f"Failed to place smart order: {e}")
            raise

    async def cancel_order(self, order_id: str, broker_account_id: str) -> Dict[str, Any]:
        try:
            resp = await self._request(
                "DELETE", f"/orders/{order_id}", 
                params={"broker_account_id": str(broker_account_id)},
                timeout=30.0
            )
            return resp.json().get("data", {})
        except Exception as e:
            logger.error(f"Failed to cancel order: {e}")
            raise

    async def get_pending_orders(self, broker_account_id: str) -> List[Dict[str, Any]]:
        try:
            resp = await self._request(
                "GET", "/orders", 
                params={"broker_account_id": str(broker_account_id)},
                timeout=30.0
            )
            return resp.json().get("data", [])
        except Exception as e:
            logger.error(f"Failed to fetch pending orders: {e}")
            raise

    async def close_all_trades(self, broker_account_id: str, symbol: str = None) -> Dict[str, Any]:
        try:
            payload = {"broker_account_id": str(broker_account_id)}
            if symbol:
                payload["symbol"] = symbol
            resp = await self._request("POST", "/trades/close-all", json=payload, timeout=30.0)
            return resp.json().get("data", {})
        except Exception as e:
            logger.error(f"Failed to close all trades: {e}")
            raise

    async def amend_order(self, order_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            resp = await self._request("PUT", f"/orders/{order_id}", json=payload, timeout=30.0)
            return resp.json().get("data", {})
        except Exception as e:
            logger.error(f"Failed to amend order: {e}")
            raise

    async def amend_position(self, trade_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Amend an open trade's SL/TP.
        Payload should contain broker_account_id and optionally sl_price, tp_price.
        """
        try:
            resp = await self._request("PUT", f"/positions/{trade_id}", json=payload, timeout=30.0)
            return resp.json().get("data", {})
        except Exception as e:
            logger.error(f"Failed to amend position: {e}")
            raise

    async def get_open_trades(self, broker_account_id: str) -> List[Dict[str, Any]]:
        try:
            resp = await self._request(
                "POST", "/trades/open", 
                json={"broker_account_id": str(broker_account_id)},
                timeout=30.0
            )
            return resp.json().get("data", [])
        except Exception as e:
            logger.error(f"Failed to fetch open trades: {e}")
            raise

    async def sync_trades(self, broker_account_id: str, lookback_days: int = 30) -> Dict[str, Any]:
        """Trigger historical trade sync from broker to internal DB."""
        try:
            resp = await self._request(
                "POST", "/trades/sync",
                json={"broker_account_id": str(broker_account_id), "lookback_days": lookback_days},
                timeout=300.0 # Historical sync can be slow
            )
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to sync trades: {e}")
            raise

    async def inspect_execution(self, broker_account_id: str, symbol: str) -> Dict[str, Any]:
        """Diagnostic endpoint to explain normalization logic"""
        try:
            resp = await self._request(
                "GET", f"/inspect/account/{broker_account_id}/symbol/{symbol}",
                timeout=30.0
            )
            return resp.json().get("data", {})
        except Exception as e:
            logger.error(f"Failed to inspect execution: {e}")
            raise

# Singleton instances for use across the application
strategy_client = StrategyClient()
execution_client = ExecutionClient()
