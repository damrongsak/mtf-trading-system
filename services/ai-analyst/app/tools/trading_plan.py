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

                # 4. Institutional Sizing & Risk Map Integration
                plan_table = [
                    f"### 🛡️ Institutional Trading Plan: {symbol} ({timeframe})",
                    f"- **Fund**: {fund_name}",
                    f"- **Equity**: ${equity:,.2f}",
                    f"- **Risk Target**: {risk_pct:.1f}%",
                    "",
                    "| Direction | Type | Entry | Stop Loss | Take Profit | R:R | Lot Size | Quant Score |",
                    "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
                ]

                # We iterate setups and call the institutional sizing API for each
                quant_size_url = f"{base_url}/api/v1/quant/size"
                
                for setup in setups:
                    entry = float(setup["entry"])
                    sl = float(setup["stop_loss"])
                    tp = float(setup["take_profit"])
                    rr = float(setup["rr"])
                    
                    # Call Quant Layer for intelligent sizing
                    sizing_payload = {
                        "symbol": symbol,
                        "entry_price": entry,
                        "stop_loss": sl,
                        "equity": equity,
                        "timeframe": timeframe
                    }
                    
                    try:
                        sz_resp = await client.post(quant_size_url, json=sizing_payload, headers=headers, timeout=10.0)
                        if sz_resp.status_code == 200:
                            sz_data = sz_resp.json().get("data", {})
                            lots = sz_data.get("sizing", {}).get("lot_size_units", 0.01)
                            quant_risk = sz_data.get("risk_map", {}).get("composite_risk_score", 0.5)
                            
                            # Quant Score visualization
                            score_emoji = "🟢" if quant_risk < 0.4 else "🟡" if quant_risk < 0.7 else "🔴"
                            score_text = f"{score_emoji} {quant_risk:.2f}"
                        else:
                            # Fallback if quant layer fails
                            sl_dist = abs(entry - sl)
                            lots = (equity * (risk_pct / 100.0)) / (sl_dist * contract_size) if sl_dist > 0 else 0.01
                            score_text = "N/A"
                    except Exception as e:
                        logger.warning(f"Quant sizing failed, using fallback: {e}")
                        sl_dist = abs(entry - sl)
                        lots = (equity * (risk_pct / 100.0)) / (sl_dist * contract_size) if sl_dist > 0 else 0.01
                        score_text = "N/A"

                    plan_table.append(
                        f"| {setup['type']} | {setup['status']} | {entry} | {sl} | {tp} | {rr} | **{lots:.2f}** | {score_text} |"
                    )

                plan_table.append("\n**Reasoning**: " + sig_data.get("reason", "Based on SMC structural confluence."))
                
                return "\n".join(plan_table)

        except Exception as e:
            logger.error(f"Trading plan generation error: {e}")
            return f"Error generating professional trading plan: {str(e)}"
