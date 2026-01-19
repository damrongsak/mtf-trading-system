import httpx
import os
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

STRATEGY_CORE_URL = os.getenv("STRATEGY_CORE_URL", "http://strategy-core:8000")
EXECUTION_SERVICE_URL = os.getenv("EXECUTION_SERVICE_URL", "http://execution:8000")

class StrategyClient:
    async def run_backtest(self, req: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            # Pass timeout for long running backtests
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
                # Long timeout for optimization
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
                # Need to use query params for ID or path param?
                # strategy-core defines: @router.post("/strategies/{strategy_id}/start")
                # and takes 'config' as Body (config: dict) since it doesn't specify Query or Body explicitly, default is Body for pydantic/dict.
                # However, FastAPI rule: if dict without Body(), it expects Body.
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

class ExecutionClient:
    async def get_account_summary(self, broker_account_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            try:
                logger.info(f"Fetching account summary from {EXECUTION_SERVICE_URL}/account/summary for {broker_account_id}")
                resp = await client.post(f"{EXECUTION_SERVICE_URL}/account/summary", json={"broker_account_id": str(broker_account_id)}, timeout=30.0)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                logger.error(f"Failed to fetch account summary: {e}", exc_info=True)
                raise

    async def place_order(self, order_data: Dict[str, Any], broker_account_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            try:
                payload = {
                    "broker_account_id": str(broker_account_id),
                    **order_data
                }
                logger.info(f"Placing order at {EXECUTION_SERVICE_URL}/orders")
                resp = await client.post(f"{EXECUTION_SERVICE_URL}/orders", json=payload, timeout=30.0)
                resp.raise_for_status()
                result = resp.json()
                logger.info(f"Order placed successfully: {result}")
                return result
            except Exception as e:
                logger.error(f"Failed to place order: {e}", exc_info=True)
                raise

    async def get_open_trades(self, broker_account_id: str) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            try:
                logger.info(f"Fetching open trades from {EXECUTION_SERVICE_URL}/trades/open")
                resp = await client.post(f"{EXECUTION_SERVICE_URL}/trades/open", json={"broker_account_id": str(broker_account_id)}, timeout=30.0)
                resp.raise_for_status()
                return resp.json().get("data", [])
            except Exception as e:
                logger.error(f"Failed to fetch open trades: {e}", exc_info=True)
                raise
    
    async def close_trade(self, trade_id: str, broker_account_id: str, units: float = None) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            try:
                payload = {
                    "broker_account_id": str(broker_account_id),
                    "broker_trade_id": trade_id,
                    "units": units
                }
                logger.info(f"Closing trade {trade_id} at {EXECUTION_SERVICE_URL}/trades/close")
                resp = await client.post(f"{EXECUTION_SERVICE_URL}/trades/close", json=payload, timeout=30.0)
                resp.raise_for_status()
                return resp.json().get("data", {})
            except Exception as e:
                logger.error(f"Failed to close trade: {e}", exc_info=True)
                raise

    async def place_smart_order(self, smart_order_data: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            try:
                logger.info(f"Placing smart order at {EXECUTION_SERVICE_URL}/smart-orders")
                resp = await client.post(f"{EXECUTION_SERVICE_URL}/smart-orders", json=smart_order_data, timeout=30.0)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                logger.error(f"Failed to place smart order: {e}", exc_info=True)
                raise

strategy_client = StrategyClient()
execution_client = ExecutionClient()
