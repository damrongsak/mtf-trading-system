from app.core.base_tool import BaseTool
from typing import Any
import aiohttp
from app.core.config import settings
import json


class StrategyBacktestTool(BaseTool):
    name: str = "backtest_runner"
    description: str = "Executes a Python strategy using vectorbt on historical data and returns performance metrics (Sharpe, PnL, MDD). WARNING: This is a high-latency tool for historical auditing only. NEVER use for real-time risk or immediate drawdown queries."

    async def run_tool(self, input_data: Any, auth_token: str = None, request_id: str = None) -> str:
        url = f"{settings.STRATEGY_CORE_URL}/api/v1/backtest/custom"

        payload = {}
        if isinstance(input_data, str):
            try:
                payload = json.loads(input_data)
            except Exception:
                return "Error: invalid JSON input for backtest."
        elif isinstance(input_data, dict):
            payload = input_data

        if not payload:
            return "Error: Backtest configuration required (symbol, timeframe, code)."

        from datetime import datetime, timedelta
        if "start_date" not in payload:
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=30)
            payload.setdefault("start_date", start_dt.isoformat())
            payload.setdefault("end_date", end_dt.isoformat())
        payload.setdefault("initial_capital", 10000.0)
        payload.setdefault("fees", 0.0001)
        payload.setdefault("slippage", 0.0001)

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=payload, timeout=120) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        metrics = data.get("metrics", {})
                        status = data.get("status", "UNKNOWN")

                        if status != "COMPLETED":
                            return f"Backtest Failed: {status}"

                        return (
                            f"**Backtest Results** for {payload.get('symbol', 'N/A')}:\n"
                            f"- Total Return: {metrics.get('total_return_percent', 0):.2f}%\n"
                            f"- Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}\n"
                            f"- Max Drawdown: {metrics.get('max_drawdown_percent', 0):.2f}%\n"
                            f"- Win Rate: {metrics.get('win_rate', 0):.2f}%\n"
                            f"- Profit Factor: {metrics.get('profit_factor', 0):.2f}\n"
                            f"- Total Trades: {metrics.get('total_trades', 0)}"
                        )
                    else:
                        err_text = await resp.text()
                        return f"Strategy Core Error ({resp.status}): {err_text}"
            except Exception as e:
                return f"Failed to execute backtest: {e}"
