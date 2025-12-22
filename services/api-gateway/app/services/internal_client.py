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
                resp = await client.post(f"{STRATEGY_CORE_URL}/api/v1/backtest", json=req, timeout=120.0)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                logger.error(f"Backtest request failed: {e}", exc_info=True)
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

class ExecutionClient:
    async def get_account_summary(self, broker_config: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            try:
                # Changed to POST to send broker config
                logger.info(f"Fetching account summary from {EXECUTION_SERVICE_URL}/account/summary")
                resp = await client.post(f"{EXECUTION_SERVICE_URL}/account/summary", json={"broker": broker_config}, timeout=10.0)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                logger.error(f"Failed to fetch account summary: {e}", exc_info=True)
                raise

    async def place_order(self, order_data: Dict[str, Any], broker_config: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            try:
                payload = {
                    "broker": broker_config,
                    **order_data
                }
                logger.info(f"Placing order at {EXECUTION_SERVICE_URL}/orders")
                resp = await client.post(f"{EXECUTION_SERVICE_URL}/orders", json=payload, timeout=10.0)
                resp.raise_for_status()
                result = resp.json()
                logger.info(f"Order placed successfully: {result}")
                return result
            except Exception as e:
                logger.error(f"Failed to place order: {e}", exc_info=True)
                raise

    async def get_open_trades(self, broker_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            try:
                # Changed to POST to send broker config
                logger.info(f"Fetching open trades from {EXECUTION_SERVICE_URL}/trades/open")
                resp = await client.post(f"{EXECUTION_SERVICE_URL}/trades/open", json={"broker": broker_config}, timeout=30.0)
                resp.raise_for_status()
                return resp.json().get("data", [])
            except Exception as e:
                logger.error(f"Failed to fetch open trades: {e}", exc_info=True)
                raise
    
    async def close_trade(self, trade_id: str, broker_config: Dict[str, Any], units: float = None) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            try:
                payload = {
                    "broker": broker_config,
                    "broker_trade_id": trade_id,
                    "units": units
                }
                logger.info(f"Closing trade {trade_id} at {EXECUTION_SERVICE_URL}/trades/close")
                resp = await client.post(f"{EXECUTION_SERVICE_URL}/trades/close", json=payload, timeout=10.0)
                resp.raise_for_status()
                return resp.json().get("data", {})
            except Exception as e:
                logger.error(f"Failed to close trade: {e}", exc_info=True)
                raise

strategy_client = StrategyClient()
execution_client = ExecutionClient()
