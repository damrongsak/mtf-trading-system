import os
import httpx
from typing import Any, List, Dict, Optional
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
    description: str = "Generates a professional trading plan for a symbol including Entry, SL, TP, and Lot Size based on Fund Risk Profile. Use this when the user asks for a 'trading plan' or 'buy/sell setup'."
    args_schema: Any = TradingPlanInput

    async def run(self, input_data: Any, auth_token: str = None, request_id: str = None) -> str:
        symbol = input_data.get("symbol", "XAUUSD").upper().replace("/", "").replace("_", "")
        timeframe = input_data.get("timeframe", "M15")
        override_risk = input_data.get("risk_percentage")

        headers = {}
        if auth_token:
            headers["Authorization"] = auth_token if auth_token.startswith("Bearer ") else f"Bearer {auth_token}"

        base_url = getattr(settings, "API_GATEWAY_URL", "http://api-gateway:8000")
        
        try:
            # 1. Fetch SMC Setups from Strategy Core
            # We call the /api/v1/signal/latest endpoint which now includes 'setups'
            signal_url = f"{base_url}/api/v1/signal/latest/{symbol}"
            async with httpx.AsyncClient() as client:
                sig_resp = await client.get(signal_url, params={"timeframe": timeframe}, headers=headers, timeout=15.0)
                if sig_resp.status_code != 200:
                    return f"Error fetching setups: {sig_resp.status_code} - {sig_resp.text}"
                
                sig_data = sig_resp.json().get("data", {})
                setups = sig_data.get("setups", [])
                
                if not setups:
                    return f"No actionable SMC setups found for {symbol} on {timeframe} timeframe."

                # 2. Fetch Account Equity
                acc_url = f"{base_url}/api/v1/execution/account/summary"
                acc_resp = await client.get(acc_url, headers=headers, timeout=10.0)
                equity = 10000.0 # Fallback
                if acc_resp.status_code == 200:
                    acc_data = acc_resp.json().get("data", {})
                    # Balance or NAV
                    equity = float(acc_data.get("NAV") or acc_data.get("balance") or 10000.0)

                # 3. Fetch Fund Risk Profile
                fund_url = f"{base_url}/api/v1/funds"
                fund_resp = await client.get(fund_url, headers=headers, timeout=10.0)
                risk_pct = 1.0 # Default 1%
                fund_name = "Default"
                
                if fund_resp.status_code == 200:
                    funds = fund_resp.json().get("data", [])
                    if funds:
                        # Use the first fund or one matching the active trading intent
                        # For now, we take the one where the user is OWNER or the first one
                        fund = next((f for f in funds if f.get("role") == "OWNER"), funds[0])
                        risk_pct = float(fund.get("risk_percentage", 0.01)) * 100.0
                        fund_name = fund.get("name", "Active Fund")

                if override_risk is not None:
                    risk_pct = override_risk

                # 4. Calculate Lot Sizes for each setup using RiskCheckTool logic or direct calc
                # Lot = (Equity * Risk%) / (SL Distance * ContractSize)
                # ContractSize for XAUUSD is 100. For others usually 100,000 (standard lot).
                contract_size = 100 if "XAU" in symbol else 100000
                
                plan_table = [
                    f"### 🛡️ Institutional Trading Plan: {symbol} ({timeframe})",
                    f"- **Fund**: {fund_name}",
                    f"- **Equity**: ${equity:,.2f}",
                    f"- **Risk per Trade**: {risk_pct:.1f}%",
                    "",
                    "| Direction | Type | Entry | Stop Loss | Take Profit | R:R | Lot Size |",
                    "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
                ]

                for setup in setups:
                    entry = setup["entry"]
                    sl = setup["stop_loss"]
                    tp = setup["take_profit"]
                    rr = setup["rr"]
                    
                    sl_dist = abs(entry - sl)
                    if sl_dist > 0:
                        risk_usd = equity * (risk_pct / 100.0)
                        lots = risk_usd / (sl_dist * contract_size)
                        lots = round(lots, 2)
                    else:
                        lots = 0.01
                    
                    plan_table.append(
                        f"| {setup['type']} | {setup['status']} | {entry} | {sl} | {tp} | {rr} | **{lots}** |"
                    )

                plan_table.append("\n**Reasoning**: " + sig_data.get("reason", "Based on SMC structural confluence."))
                
                return "\n".join(plan_table)

        except Exception as e:
            logger.error(f"Trading plan generation error: {e}")
            return f"Error generating professional trading plan: {str(e)}"
