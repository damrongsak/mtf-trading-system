import httpx
import os
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

STRATEGY_CORE_URL = os.getenv("STRATEGY_CORE_URL", "http://strategy-core:8000")
EXECUTION_SERVICE_URL = os.getenv("EXECUTION_SERVICE_URL", "http://execution:8000")

class StrategyClient:
    async def run_backtest(self, req: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            try:
                logger.info(f"Sending backtest request to {STRATEGY_CORE_URL}/api/v1/backtest")
                resp = await client.post(f"{STRATEGY_CORE_URL}/api/v1/backtest", json=req, timeout=60.0)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                logger.error(f"Backtest request failed: {e}", exc_info=True)
                raise

    async def run_custom_backtest(self, req: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            try:
                logger.info(f"Sending custom backtest request to {STRATEGY_CORE_URL}/api/v1/backtest/custom")
                resp = await client.post(f"{STRATEGY_CORE_URL}/api/v1/backtest/custom", json=req, timeout=600.0)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                logger.error(f"Custom backtest failed: {e}", exc_info=True)
                raise

    async def run_optimization(self, req: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            try:
                logger.info(f"Sending optimization request to {STRATEGY_CORE_URL}/api/v1/backtest/optimize")
                resp = await client.post(f"{STRATEGY_CORE_URL}/api/v1/backtest/optimize", json=req, timeout=300.0)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                logger.error(f"Optimization request failed: {e}", exc_info=True)
                raise

    async def run_monte_carlo(self, req: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            try:
                logger.info(f"Sending Monte Carlo request to {STRATEGY_CORE_URL}/api/v1/backtest/monte-carlo")
                resp = await client.post(f"{STRATEGY_CORE_URL}/api/v1/backtest/monte-carlo", json=req, timeout=60.0)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                logger.error(f"Monte Carlo request failed: {e}", exc_info=True)
                raise

    async def start_strategy(self, strategy_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            try:
                logger.info(f"Starting strategy {strategy_id} via {STRATEGY_CORE_URL}")
                resp = await client.post(f"{STRATEGY_CORE_URL}/api/v1/strategies/{strategy_id}/start", json=config, timeout=10.0)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                logger.error(f"Start strategy failed: {e}", exc_info=True)
                raise

    async def stop_strategy(self, strategy_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            try:
                logger.info(f"Stopping strategy {strategy_id} via {STRATEGY_CORE_URL}")
                resp = await client.post(f"{STRATEGY_CORE_URL}/api/v1/strategies/{strategy_id}/stop", timeout=10.0)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                logger.error(f"Stop strategy failed: {e}", exc_info=True)
                raise

INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "dev_secret_key")

_execution_client_session: Optional[httpx.AsyncClient] = None

def get_execution_session() -> httpx.AsyncClient:
    global _execution_client_session
    if _execution_client_session is None:
        limits = httpx.Limits(max_keepalive_connections=20, max_connections=100)
        timeout = httpx.Timeout(30.0, connect=5.0)
        _execution_client_session = httpx.AsyncClient(
            limits=limits,
            timeout=timeout,
            headers={"X-Internal-API-Key": INTERNAL_API_KEY}
        )
    return _execution_client_session

class ExecutionClient:
    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        client = get_execution_session()
        url = f"{EXECUTION_SERVICE_URL}{path}"
        for attempt in range(2):
            try:
                resp = await client.request(method, url, **kwargs)
                resp.raise_for_status()
                return resp
            except (httpx.ConnectError, httpx.RemoteProtocolError, ConnectionResetError) as e:
                if attempt == 0:
                    logger.warning(f"Execution API Retryable Error: {e}. Retrying {path}...")
                    continue
                raise
            except Exception:
                raise

    async def get_account_summary(self, broker_account_id: str) -> Dict[str, Any]:
        try:
            resp = await self._request(
                "POST", "/account/summary",
                json={"broker_account_id": str(broker_account_id)}
            )
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to get account summary: {e}")
            raise

    async def place_order(self, order_data: Dict[str, Any], broker_account_id: Optional[str] = None) -> Dict[str, Any]:
        try:
            if broker_account_id:
                order_data["broker_account_id"] = str(broker_account_id)
            resp = await self._request("POST", "/orders", json=order_data)
            return resp.json().get("data", {})
        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            raise

    async def get_trades(self, broker_account_id: str) -> List[Dict[str, Any]]:
        try:
            resp = await self._request("GET", "/trades", params={"broker_account_id": str(broker_account_id)})
            return resp.json().get("data", [])
        except Exception as e:
            logger.error(f"Failed to fetch trades: {e}")
            raise

    async def get_trade_details(self, trade_id: str, broker_account_id: str) -> Dict[str, Any]:
        try:
            resp = await self._request("GET", f"/trades/{trade_id}", params={"broker_account_id": str(broker_account_id)})
            return resp.json().get("data", {})
        except Exception as e:
            logger.error(f"Failed to fetch trade details: {e}")
            raise

    async def close_trade(self, trade_id: str, broker_account_id: str, units: Optional[float] = None) -> Dict[str, Any]:
        try:
            payload = {"broker_account_id": str(broker_account_id), "broker_trade_id": str(trade_id)}
            if units is not None:
                payload["units"] = units
            resp = await self._request("POST", "/trades/close", json=payload)
            return resp.json().get("data", {})
        except Exception as e:
            logger.error(f"Failed to close trade: {e}")
            raise

    async def place_smart_order(self, smart_order_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            resp = await self._request("POST", "/smart-orders", json=smart_order_data)
            return resp.json().get("data", {})
        except Exception as e:
            logger.error(f"Failed to place smart order: {e}")
            raise

    async def cancel_order(self, order_id: str, broker_account_id: str) -> Dict[str, Any]:
        try:
            resp = await self._request("DELETE", f"/orders/{order_id}", params={"broker_account_id": str(broker_account_id)})
            return resp.json().get("data", {})
        except Exception as e:
            logger.error(f"Failed to cancel order: {e}")
            raise

    async def get_pending_orders(self, broker_account_id: str) -> List[Dict[str, Any]]:
        try:
            resp = await self._request("GET", "/orders", params={"broker_account_id": str(broker_account_id)})
            return resp.json().get("data", [])
        except Exception as e:
            logger.error(f"Failed to fetch pending orders: {e}")
            raise

    async def close_all_trades(self, broker_account_id: str, symbol: str = None) -> Dict[str, Any]:
        try:
            payload = {"broker_account_id": str(broker_account_id)}
            if symbol:
                payload["symbol"] = symbol
            resp = await self._request("POST", "/trades/close-all", json=payload)
            return resp.json().get("data", {})
        except Exception as e:
            logger.error(f"Failed to close all trades: {e}")
            raise

    async def amend_order(self, order_id: str, broker_account_id: str, units: Optional[float] = None, price: Optional[float] = None, sl_price: Optional[float] = None, tp_price: Optional[float] = None) -> Dict[str, Any]:
        try:
            payload = {
                "broker_account_id": str(broker_account_id),
                "units": units,
                "price": price,
                "sl_price": sl_price,
                "tp_price": tp_price
            }
            # Remove None values
            payload = {k: v for k, v in payload.items() if v is not None}
            resp = await self._request("PUT", f"/orders/{order_id}", json=payload)
            return resp.json().get("data", {})
        except Exception as e:
            logger.error(f"Failed to amend order: {e}")
            raise

    async def get_open_trades(self, broker_account_id: str) -> List[Dict[str, Any]]:
        try:
            resp = await self._request("POST", "/trades/open", json={"broker_account_id": str(broker_account_id)})
            return resp.json().get("data", [])
        except Exception as e:
            logger.error(f"Failed to fetch open trades: {e}")
            raise

# Singleton instances for use across the application
strategy_client = StrategyClient()
execution_client = ExecutionClient()
