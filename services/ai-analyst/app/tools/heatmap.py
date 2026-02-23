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
                # 1. Fetch Current Spot Price — Multi-layer fallback for reliability
                # Layer 1: data-pipeline candles (primary)
                current_price = 0.0
                try:
                    data_pipeline_url = f"{settings.DATA_PIPELINE_URL}/api/v1"
                    price_url = f"{data_pipeline_url}/candles"
                    price_params = {"symbol": symbol, "timeframe": "H1", "page_size": 1}
                    async with session.get(price_url, params=price_params, headers=headers, timeout=aiohttp.ClientTimeout(total=5.0)) as resp:
                        if resp.status == 200:
                            candle_data = await resp.json()
                            candles = candle_data.get("data", [])
                            if candles:
                                current_price = float(candles[0].get("close") or 0.0)
                except Exception as e:
                    logger.warning(f"Layer 1 (data-pipeline) price fetch failed: {e}")

                # Layer 2: strategy-core candles (fallback)
                if current_price <= 0:
                    try:
                        sc_url = f"{strategy_core_url}/market/candles"
                        async with session.get(sc_url, params={"symbol": symbol, "timeframe": "H1", "limit": 1}, headers=headers, timeout=aiohttp.ClientTimeout(total=5.0)) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                bars = data.get("data", data.get("candles", []))
                                if bars:
                                    current_price = float(bars[-1].get("close") or 0.0)
                    except Exception as e:
                        logger.warning(f"Layer 2 (strategy-core) price fetch failed: {e}")

                if current_price > 0:
                    logger.info(f"Heatmap using spot price: {current_price:.2f} for {symbol}")
                else:
                    logger.warning(f"Could not fetch spot price for {symbol} heatmap — basis offset will be 0")

                # 2. Fetch Gamma Levels — always pass current_price (even 0) so API knows we tried

                url = f"{strategy_core_url}/analysis/gamma/levels"
                params = {"symbol": symbol}
                if current_price > 0:
                    params["current_price"] = str(current_price)

                async with session.get(url, params=params, headers=headers, timeout=10.0) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        heatmap = data.get("heatmap") or []
                        max_pain = data.get("max_pain") or 0.0
                        # underlying_price in DB is NULL — use our locally-fetched spot price
                        underlying = data.get("underlying_price") or current_price or 0.0
                        
                        if not heatmap:
                            return "No liquidity heatmap data available currently."
                        
                        spot_label = f"{underlying:.2f}" if underlying > 0 else "N/A"
                        report = [f"### 🌡️ Gold Liquidity Heatmap (Spot: {spot_label})"]
                        report.append(f"\n**Max Pain (Gravity Center): {max_pain:.2f}**")
                        if underlying > 0:
                            report.append(f"> Reference spot price: {underlying:.2f} | CME Options Strikes mapped relative to spot")
                        report.append("\n| Strike | Relative Density | Actionable Bias |")
                        report.append("| :--- | :--- | :--- |")
                        
                        # Sort heatmap by strike descending
                        sorted_heatmap = sorted(heatmap, key=lambda x: x['strike'], reverse=True)
                        
                        # Prune: Only show ±500 points around spot to keep output focused (~20-30 rows)
                        if underlying > 0:
                            sorted_heatmap = [
                                h for h in sorted_heatmap 
                                if abs(h['strike'] - underlying) <= 500
                            ]
                        
                        for entry in sorted_heatmap:
                            density = entry.get('relative_density', 0.0)
                            strike = entry.get('strike', 0.0)
                            
                            bar_len = int(density * 10)
                            bar = "█" * bar_len + "░" * (10 - bar_len)
                            
                            bias = "Neutral"
                            if underlying > 0:
                                if strike > underlying:
                                    bias = "Resistance (Calls)"
                                else:
                                    bias = "Support (Puts)"
                                    
                            if max_pain > 0 and abs(strike - max_pain) < 25:
                                bias = "🎯 **MAGNET ZONE**"
                                
                            report.append(f"| {strike:.2f} | {bar} ({density*100:.0f}%) | {bias} |")

                        
                        report.append("\n> **Interpretation**: Areas with >70% density represent institutional 'walls'. Price tends to be sucked towards Max Pain during option expiry.")
                        return "\n".join(report)
                    else:
                        return f"Failed to fetch heatmap data ({resp.status})"
            except Exception as e:
                logger.error(f"Heatmap Tool Failed: {e}")
                return f"Heatmap Tool Error: {str(e)}"
