from typing import Any, Optional
import aiohttp
from app.core.config import settings
from app.core.base_tool import BaseTool

class PredictorForecastTool(BaseTool):
    name: str = "get_predictor_forecast"
    description: str = "Fetches price forecasts and volatility metrics from the Olympus Predictor model for XAUUSD."

    async def run_tool(self, input_data: Any, auth_token: str = None, request_id: str = None) -> str:
        symbol = "XAUUSD"
        steps = 5
        timeframe = "M15"
        if isinstance(input_data, dict):
            symbol = input_data.get("symbol", "XAUUSD")
            timeframe = input_data.get("timeframe", "M15")
            try:
                steps = int(input_data.get("steps", 5))
            except (ValueError, TypeError):
                steps = 5
        elif isinstance(input_data, str) and input_data:
            symbol = input_data
        
        async with aiohttp.ClientSession() as session:
            try:
                url = f"{settings.OLYMPUS_PREDICTOR_URL}/predict"
                payload = {"symbol": symbol, "steps": steps, "timeframe": timeframe}
                async with session.post(url, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        prices = data.get("prices", [])
                        sigma = data.get("sigma_lr", [])
                        # Format prices for readability (2 decimal places)
                        prices_fmt = [f"{p:.2f}" for p in prices]
                        return (
                            f"Forecast for {symbol} ({timeframe}) (next {len(prices)} steps):\n"
                            f"Price Path: {', '.join(prices_fmt)}\n"
                            f"Volatility (Sigma): {sigma}\n"
                            f"Model Version: {data.get('model_version')}"
                        )
                    else:
                        err_text = await resp.text()
                        return f"Error fetching forecast: {resp.status} - {err_text}"
            except Exception as e:
                return f"Failed to connect to Predictor Service: {e}"

class PredictorSignalTool(BaseTool):
    name: str = "get_predictor_signal"
    description: str = "Gets a confidence-weighted trading signal (Direction, Target, Stop Loss) from the Olympus Predictor for a specific timeframe."

    async def run_tool(self, input_data: Any, auth_token: str = None, request_id: str = None) -> str:
        symbol = "XAUUSD"
        timeframe = "M15"
        if isinstance(input_data, dict):
            symbol = input_data.get("symbol", "XAUUSD")
            timeframe = input_data.get("timeframe", "M15")
        elif isinstance(input_data, str) and input_data:
            symbol = input_data
        
        async with aiohttp.ClientSession() as session:
            try:
                url = f"{settings.OLYMPUS_PREDICTOR_URL}/signal"
                payload = {"symbol": symbol, "timeframe": timeframe}
                async with session.post(url, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        direction = data.get('direction', 'NEUTRAL')
                        confidence = data.get('confidence', 0.0)
                        target = data.get('target', 0.0)
                        sl = data.get('stop_loss', 0.0)
                        sentiment = data.get('sentiment_score', 0.0)
                        
                        return (
                            f"Olympus ML Signal for {symbol}:\n"
                            f"Direction: {direction}\n"
                            f"Confidence: {confidence:.2f}\n"
                            f"Target: {target:.2f}\n"
                            f"Stop Loss: {sl:.2f}\n"
                            f"Sentiment Context: {sentiment:.2f}"
                        )
                    else:
                        err_text = await resp.text()
                        return f"Error fetching signal: {resp.status} - {err_text}"
            except Exception as e:
                return f"Failed to connect to Predictor Service: {e}"
