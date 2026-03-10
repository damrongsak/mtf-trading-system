import logging
import json
from typing import Any, Dict
from app.core.base_tool import BaseTool
from app.agents.efp_analyst import efp_analyst

logger = logging.getLogger(__name__)

class EFPCalibrationTool(BaseTool):
    name: str = "calibrate_efp_parameters"
    description: str = """
    Calibrates the Exchange for Physical (EFP) model parameters for a given symbol (default: XAUUSD).
    Analyzes historical spot and futures data to estimate mean-reversion speed (kappa) and volatility (sigma).
    Input JSON (optional): {"symbol": "XAUUSD", "timeframe": "H1", "days": 30}
    Updates the market symbol metadata with the newly calibrated parameters.
    """

    async def run_tool(self, input_data: Any, auth_token: str = None, request_id: str = None) -> str:
        symbol = "XAUUSD"
        timeframe = "H1"
        days = 30
        
        if isinstance(input_data, str):
            symbol = input_data.strip().upper() or "XAUUSD"
        elif isinstance(input_data, dict):
            symbol = input_data.get("symbol") or "XAUUSD"
            timeframe = input_data.get("timeframe") or "H1"
            days = input_data.get("days") or input_data.get("period_days") or 30
        
        # Robust handling for nested dicts if AI provides them
        if isinstance(symbol, dict):
            symbol = symbol.get("symbol") or "XAUUSD"

        logger.info(f"EFP Tool triggered for {symbol} ({timeframe}, {days} days)")
        
        try:
            result = await efp_analyst.calibrate_parameters(
                symbol=symbol, 
                timeframe=timeframe,
                days=days
            )
            if result.get("status") == "success":
                params = result.get("params", {})
                return f"✅ EFP Calibration Successful for {symbol}.\nNew Parameters: {json.dumps(params, indent=2)}"
            else:
                return f"❌ EFP Calibration Failed for {symbol}: {result.get('reason') or result.get('detail')}"
        except Exception as e:
            logger.error(f"EFP Tool error: {e}")
            return f"❌ Error during EFP calibration: {str(e)}"
