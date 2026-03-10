import os
import httpx
from typing import Any, List, Dict, Optional, Type
from pydantic import BaseModel, Field
from app.core.base_tool import BaseTool
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class TradingPlanInput(BaseModel):
    symbol: str = Field(description="Trading symbol, e.g., 'XAU/USD'.")
    timeframe: str = Field(default="M15", description="Timeframe for analysis (e.g., 'M15', 'H1').")
    risk_percentage: Optional[float] = Field(default=None, description="Override risk percentage (e.g., 1.0 for 1%).")

class TradingPlanTool(BaseTool):
    name: str = "generate_trading_plan"
    description: str = (
        "Generates a professional trading plan for a symbol including Entry, SL, TP, and Lot Size "
        "based on Fund Risk Profile. Use this when the user asks for a 'trading plan' or 'buy/sell setup'."
    )
    args_schema: Type[BaseModel] = TradingPlanInput

    async def run_tool(self, input_data: Any, auth_token: str = None, **kwargs) -> str:
        symbol = "XAUUSD"
        timeframe = "M15"
        risk_percentage = None
        
        if isinstance(input_data, dict):
            symbol = input_data.get("symbol", symbol)
            timeframe = input_data.get("timeframe", timeframe)
            risk_percentage = input_data.get("risk_percentage")
        elif isinstance(input_data, str):
            symbol = input_data

        normalized_symbol = symbol.upper().replace("/", "").replace("_", "")
        headers = {}
        if auth_token:
            headers["Authorization"] = auth_token if auth_token.startswith("Bearer ") else f"Bearer {auth_token}"

        base_url = getattr(settings, "API_GATEWAY_URL", "http://api-gateway:8000")
        
        try:
            async with httpx.AsyncClient() as client:
                # 1. Fetch Setups
                signal_url = f"{base_url}/api/v1/signal/latest/{normalized_symbol}"
                sig_resp = await client.get(signal_url, params={"timeframe": timeframe}, headers=headers, timeout=10.0)
                if sig_resp.status_code != 200:
                    return f"Error fetching setups: {sig_resp.status_code}"
                
                sig_data = sig_resp.json().get("data", {})
                setups = sig_data.get("setups", [])
                if not setups:
                    return f"No actionable setups found for {normalized_symbol}."

                # 2. Fetch Equity & Risk
                acc_url = f"{base_url}/api/v1/execution/account/summary"
                acc_resp = await client.get(acc_url, headers=headers, timeout=5.0)
                equity = 10000.0
                if acc_resp.status_code == 200:
                    equity = float(acc_resp.json().get("data", {}).get("NAV", 10000.0))

                risk_pct = risk_percentage if risk_percentage is not None else 1.0

                # 3. Build Plan
                plan = [
                    f"### 🛡️ Institutional Trading Plan: {normalized_symbol} ({timeframe})",
                    f"- Equity: ${equity:,.2f} | Risk Target: {risk_pct:.1f}%",
                    "",
                    "| Type | Entry | SL | TP | R:R | Lot Size |",
                    "| :--- | :--- | :--- | :--- | :--- | :--- |"
                ]

                quant_size_url = f"{base_url}/api/v1/quant/size"
                for setup in setups:
                    # Call Quant Sizing
                    sizing_payload = {
                        "symbol": normalized_symbol,
                        "entry_price": float(setup["entry"]),
                        "stop_loss": float(setup["stop_loss"]),
                        "equity": equity,
                        "timeframe": timeframe
                    }
                    lots = 0.01
                    try:
                        sz_resp = await client.post(quant_size_url, json=sizing_payload, headers=headers, timeout=5.0)
                        if sz_resp.status_code == 200:
                            lots = sz_resp.json().get("data", {}).get("sizing", {}).get("lot_size_units", 0.01)
                    except: pass

                    plan.append(f"| {setup['type']} | {setup['entry']} | {setup['stop_loss']} | {setup['take_profit']} | {setup['rr']} | **{lots:.2f}** |")

                return "\n".join(plan)

        except Exception as e:
            logger.error(f"TradingPlanTool error: {e}")
            return f"Error: {str(e)}"
