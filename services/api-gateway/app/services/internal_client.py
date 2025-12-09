import httpx
import os
from typing import Dict, Any

STRATEGY_CORE_URL = os.getenv("STRATEGY_CORE_URL", "http://strategy-core:8000")
EXECUTION_SERVICE_URL = os.getenv("EXECUTION_SERVICE_URL", "http://execution:8000")

class StrategyClient:
    async def run_backtest(self, req: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            # Pass timeout for long running backtests
            resp = await client.post(f"{STRATEGY_CORE_URL}/backtest", json=req, timeout=120.0)
            resp.raise_for_status()
            return resp.json()

class ExecutionClient:
    async def get_account_summary(self) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{EXECUTION_SERVICE_URL}/account/summary", timeout=10.0)
            resp.raise_for_status()
            return resp.json()

    async def place_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{EXECUTION_SERVICE_URL}/orders", json=order_data, timeout=10.0)
            resp.raise_for_status()
            return resp.json()

strategy_client = StrategyClient()
execution_client = ExecutionClient()
