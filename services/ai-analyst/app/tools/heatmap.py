import logging
import json
from typing import Any, Optional
import aiohttp
from app.core.config import settings
from app.core.base_tool import BaseTool

logger = logging.getLogger(__name__)

class LiquidityHeatmapTool(BaseTool):
    name: str = "liquidity_heatmap"
    description: str = """
    Provides a spatial view of Gold (XAUUSD) liquidity density (Heatmap).
    Identifies 'Gravity Zones' where price is likely to be pinned or rejected.
    Input JSON: {"symbol": "XAUUSD"}
    """

    async def run(self, input_data: Any = None, auth_token: str = None, request_id: str = None) -> str:
        strategy_core_url = f"{settings.STRATEGY_CORE_URL}/api/v1"
        symbol = "XAUUSD"
        
        if isinstance(input_data, dict):
            symbol = input_data.get("symbol", symbol)
        
        headers = {}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}" if not auth_token.startswith("Bearer ") else auth_token

        async with aiohttp.ClientSession() as session:
            try:
                # 1. Fetch Current Spot Price for Symbol (Same logic as in OpenInterest tool)
                current_price = 0.0
                try:
                    data_pipeline_url = f"{settings.DATA_PIPELINE_URL}/api/v1"
                    price_url = f"{data_pipeline_url}/candles"
                    price_params = {"symbol": symbol, "timeframe": "H1", "page_size": 1}
                    async with session.get(price_url, params=price_params, headers=headers, timeout=5.0) as resp:
                        if resp.status == 200:
                            candle_data = await resp.json()
                            candles = candle_data.get("data", [])
                            if candles:
                                current_price = float(candles[0].get("close") or 0.0)
                except Exception as e:
                    logger.warning(f"Failed to fetch live spot price for heatmap: {e}")

                # 2. Fetch Gamma Levels with current_price
                url = f"{strategy_core_url}/analysis/gamma/levels"
                params = {"symbol": symbol}
                if current_price > 0:
                    params["current_price"] = str(current_price)

                async with session.get(url, params=params, headers=headers, timeout=10.0) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        heatmap = data.get("heatmap") or []
                        max_pain = data.get("max_pain") or 0.0
                        underlying = data.get("underlying_price") or 0.0
                        
                        if not heatmap:
                            return "No liquidity heatmap data available currently."
                        
                        report = [f"### 🌡️ Gold Liquidity Heatmap (Spot: {underlying:.2f})"]
                        report.append(f"\n**Max Pain (Gravity Center): {max_pain:.2f}**")
                        report.append("\n| Strike | Relative Density | Actionable Bias |")
                        report.append("| :--- | :--- | :--- |")
                        
                        # Sort heatmap by strike for better visualization
                        sorted_heatmap = sorted(heatmap, key=lambda x: x['strike'], reverse=True)
                        
                        # Prune: Only show ±15 strikes around spot to save space (approx 30 rows max)
                        if underlying > 0:
                            sorted_heatmap = [
                                h for h in sorted_heatmap 
                                if abs(h['strike'] - underlying) <= 50 # 50 points = 10-20 strikes for Gold
                            ]
                        
                        for entry in sorted_heatmap:
                            density = entry.get('relative_density', 0.0)
                            strike = entry.get('strike', 0.0)
                            
                            # Create a simple bar for density
                            bar_len = int(density * 10)
                            bar = "█" * bar_len + "░" * (10 - bar_len)
                            
                            bias = "Neutral"
                            if strike > underlying:
                                bias = "Resistance (Calls)"
                            else:
                                bias = "Support (Puts)"
                                
                            if abs(strike - max_pain) < 5:
                                bias = "🎯 **MAGNET ZONE**"
                                
                            report.append(f"| {strike:.2f} | {bar} ({density*100:.0f}%) | {bias} |")
                        
                        report.append("\n> **Interpretation**: Areas with >70% density represent institutional 'walls'. Price tends to be sucked towards Max Pain during option expiry.")
                        return "\n".join(report)
                    else:
                        return f"Failed to fetch heatmap data ({resp.status})"
            except Exception as e:
                logger.error(f"Heatmap Tool Failed: {e}")
                return f"Heatmap Tool Error: {str(e)}"
