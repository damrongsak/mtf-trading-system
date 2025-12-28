from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type
import aiohttp
from app.core.config import settings
import json

class StrategyInput(BaseModel):
    symbol: str = Field(description="The trading symbol to test, e.g., 'XAU/USD'.")
    code: str = Field(description="The Python code implementing the strategy. Must use 'vectorbt' and define 'strategy(data)' or similar.")
    timeframe: str = Field(default="1h", description="Timeframe for the backtest (e.g. '15m', '1h').")

class StrategyBacktestTool(BaseTool):
    name: str = "run_strategy_backtest"
    description: str = "Executes a Python strategy using vectorbt on historical data and returns performance metrics (Sharpe, PnL)."
    args_schema: Type[BaseModel] = StrategyInput

    def _run(self, symbol: str, code: str, timeframe: str = "1h"):
        raise NotImplementedError("Use _arun instead")

    async def _arun(self, symbol: str, code: str, timeframe: str = "1h"):
        url = f"{settings.STRATEGY_CORE_URL}/api/v1/backtest/custom"
        
        # Prepare payload for Strategy Core
        payload = {
            "symbol": symbol,
            "timeframe": timeframe,
            "code": code,
            "start_date": "2024-01-01T00:00:00", # Default to YTD or dynamic
            "end_date": "2024-12-31T23:59:59",
            "initial_capital": 10000.0,
            "fees": 0.0001,
            "slippage": 0.0001
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=payload, timeout=60) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        metrics = data.get("metrics", {})
                        status = data.get("status", "UNKNOWN")
                        
                        if status != "COMPLETED":
                             return f"Backtest Failed: {status}"
                        
                        summary = (
                            f"Backtest Results for {symbol}:\n"
                            f"- Total Return: {metrics.get('total_return_percent', 0):.2f}%\n"
                            f"- Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}\n"
                            f"- Max Drawdown: {metrics.get('max_drawdown_percent', 0):.2f}%\n"
                            f"- Win Rate: {metrics.get('win_rate', 0):.2f}%\n"
                            f"- Trades: {metrics.get('total_trades', 0)}"
                        )
                        return summary
                    else:
                        err_text = await resp.text()
                        return f"Strategy Core Error ({resp.status}): {err_text}"
            except Exception as e:
                return f"Failed to execute backtest: {e}"
