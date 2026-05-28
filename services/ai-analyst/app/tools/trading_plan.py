import os
import httpx
import json
from typing import Any, List, Dict, Optional, Type
from pydantic import BaseModel, Field
from app.core.base_tool import BaseTool
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class TradingPlanInput(BaseModel):
    symbol: Optional[str] = Field(default="XAUUSD", description="Trading symbol, e.g., 'XAU/USD'.")
    timeframe: str = Field(default="M15", description="Timeframe for analysis (e.g., 'M15', 'H1').")
    risk_percentage: Optional[float] = Field(default=None, description="Override risk percentage (e.g., 1.0 for 1%).")

class TradingPlanTool(BaseTool):
    name: str = "generate_trading_plan"
    description: str = (
        "Generates a professional trading plan for a symbol including Entry, SL, TP, and Lot Size "
        "based on Fund Risk Profile. Use this when the user asks for a 'trading plan' or 'buy/sell setup'."
    )
    args_schema: Type[BaseModel] = TradingPlanInput

    timeout: int = 150
    async def run_tool(self, input_data: Any, auth_token: str = None, fund_id: str = None, **kwargs) -> str:
        symbol = "XAUUSD"
        timeframe = "M15"
        risk_percentage = None
        
        if isinstance(input_data, dict):
            symbol = input_data.get("symbol", symbol)
            timeframe = input_data.get("timeframe", timeframe)
            risk_percentage = input_data.get("risk_percentage")
        elif isinstance(input_data, str):
            # Attempt to parse as JSON if it looks like a dict
            if input_data.strip().startswith("{"):
                try:
                    data = json.loads(input_data)
                    symbol = data.get("symbol", symbol)
                    timeframe = data.get("timeframe", timeframe)
                    risk_percentage = data.get("risk_percentage")
                except json.JSONDecodeError:
                    symbol = input_data
            else:
                symbol = input_data

        normalized_symbol = symbol.upper().replace("/", "").replace("_", "")
        headers = {}
        if auth_token:
            headers["Authorization"] = auth_token if auth_token.startswith("Bearer ") else f"Bearer {auth_token}"
        
        # Propagate User and Fund IDs for data isolation
        user_id = kwargs.get("user_id")
        if user_id:
            headers["X-User-Id"] = str(user_id)
        if fund_id:
            headers["X-Fund-ID"] = str(fund_id)

        data_url = f"{settings.DATA_PIPELINE_URL}/api/v1/candles"
        smc_url = f"{settings.STRATEGY_CORE_URL}/api/v1/calculate/smc"
        acc_url = f"{settings.EXECUTION_SERVICE_URL}/account/summary"
        quant_size_url = f"{settings.STRATEGY_CORE_URL}/api/v1/quant/size"
        
        try:
            async with httpx.AsyncClient() as client:
                # 1. Fetch Candles & Analyze Signal directly (Orchestration)
                # Fetch 100 candles
                params = {"symbol": normalized_symbol, "timeframe": timeframe, "page_size": 100}
                candles_resp = await client.get(data_url, params=params, headers=headers, timeout=30.0)
                if candles_resp.status_code != 200:
                    return f"Error fetching candles from Data Pipeline: {candles_resp.status_code} - {candles_resp.text}"
                
                candles_data = candles_resp.json().get("data", [])
                if not candles_data:
                    return f"No candle data available for {normalized_symbol} on {timeframe}."
                
                # Reverse to ascending order for analysis
                candles_data.reverse()
                
                # Analyze with Strategy Core
                smc_payload = {
                    "symbol": normalized_symbol,
                    "timeframe": timeframe,
                    "fund_id": fund_id,
                    "open": [float(c["open"]) for c in candles_data],
                    "high": [float(c["high"]) for c in candles_data],
                    "low": [float(c["low"]) for c in candles_data],
                    "close": [float(c["close"]) for c in candles_data],
                    "volume": [float(c["volume"]) for c in candles_data],
                    "timestamps": [c["timestamp"] for c in candles_data]
                }
                
                sig_resp = await client.post(smc_url, json=smc_payload, headers=headers, timeout=30.0)
                if sig_resp.status_code != 200:
                    return f"Error from Strategy Core (SMC): {sig_resp.status_code} - {sig_resp.text}"
                
                sig_data = sig_resp.json()
                setups = sig_data.get("setups", [])
                if not setups:
                    return f"No actionable setups found for {normalized_symbol} in SMC analysis."

                # 2. Fetch Equity & Risk
                from app.utils.tracing import get_account_id
                acc_id = get_account_id()
                
                equity = 10000.0
                if acc_id:
                    try:
                        acc_payload = {"broker_account_id": acc_id}
                        acc_resp = await client.post(acc_url, json=acc_payload, headers=headers, timeout=20.0)
                        if acc_resp.status_code == 200:
                            equity = float(acc_resp.json().get("data", {}).get("NAV", 10000.0))
                    except Exception as ex:
                        logger.warning(f"Failed to fetch account equity: {repr(ex)}")
                else:
                    logger.warning("No Broker-Account-ID found in context for TradingPlanTool sizing.")

                risk_pct = risk_percentage if risk_percentage is not None else 1.0

                # 3. Build Plan
                plan = [
                    f"### 🛡️ Institutional Trading Plan: {normalized_symbol} ({timeframe})",
                    f"- Equity: ${equity:,.2f} | Risk Target: {risk_pct:.1f}%",
                    "",
                    "| Type | Entry | SL | TP | R:R | Lot Size |",
                    "| :--- | :--- | :--- | :--- | :--- | :--- |"
                ]

                # 4. Calculate Sizing for each setup
                for setup in setups:
                    sizing_payload = {
                        "symbol": normalized_symbol,
                        "entry_price": float(setup["entry"]),
                        "stop_loss": float(setup["stop_loss"]),
                        "equity": equity,
                        "timeframe": timeframe,
                        "fund_id": fund_id
                    }
                    lots = 0.01
                    try:
                        sz_resp = await client.post(quant_size_url, json=sizing_payload, headers=headers, timeout=20.0)
                        if sz_resp.status_code == 200:
                            lots = sz_resp.json().get("data", {}).get("sizing", {}).get("lot_size_units", 0.01)
                    except: pass

                    plan.append(f"| {setup['type']} | {setup['entry']} | {setup['stop_loss']} | {setup['take_profit']} | {setup['rr']} | **{lots:.2f}** |")

                return "\n".join(plan)

        except Exception as e:
            logger.error("TradingPlanTool error", exc_info=True)
            return f"Trading Plan Tool Error: {repr(e)}"
