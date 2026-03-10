import logging
from typing import Any, Optional, Type
import aiohttp
from app.core.config import settings
from app.core.base_tool import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class AccountStatusInput(BaseModel):
    pass # No input required

class GetAccountStatusTool(BaseTool):
    name: str = "get_account_status"
    description: str = (
        "Fetches dimensions of account health including balance, equity, margin, "
        "open positions, and risk metrics. REQUIRED for calculating position size."
    )
    args_schema: Type[BaseModel] = AccountStatusInput

    async def run_tool(self, input_data: Any, auth_token: str = None, **kwargs) -> str:
        async with aiohttp.ClientSession() as session:
            try:
                headers = {}
                if auth_token:
                    headers["Authorization"] = auth_token if auth_token.startswith("Bearer ") else f"Bearer {auth_token}"
                
                url = f"{settings.API_GATEWAY_URL}/api/v1/execution/account/summary"
                
                async with session.get(url, headers=headers, timeout=5.0) as resp:
                     if resp.status == 200:
                         json_resp = await resp.json()
                         data = json_resp.get("data", {})
                         
                         def parse_float(v):
                             if isinstance(v, (float, int)): return float(v)
                             if isinstance(v, str):
                                 clean = v.split(' ')[0].replace(',', '')
                                 try: return float(clean)
                                 except: return 0.0
                             return 0.0

                         balance = parse_float(data.get("balance"))
                         equity = parse_float(data.get("NAV") or data.get("equity"))
                         margin_available = parse_float(data.get("marginAvailable"))
                         margin_used = equity - margin_available
                         open_positions = data.get("open_positions", [])
                         
                         positions_summary = []
                         total_exposure_risk = 0.0
                         for p in open_positions:
                             symbol = p.get("symbol")
                             pnl = p.get("pnl", 0.0)
                             risk = p.get("risk_usd", 0.0)
                             total_exposure_risk += risk
                             positions_summary.append(f"{symbol}: PnL ${pnl:.2f}, Risk ${risk:.2f}")
                             
                         report = (
                             f"**Account Health**:\n"
                             f"- Balance: ${balance:,.2f}\n"
                             f"- Equity: ${equity:,.2f}\n"
                             f"- Margin Used: ${margin_used:,.2f}\n"
                             f"- Active Positions: {len(open_positions)}\n"
                             f"- Total Risk Exposure: ${total_exposure_risk:,.2f}\n"
                             f"- Open Trades: {', '.join(positions_summary) if positions_summary else 'None'}"
                         )
                         return report
                     else:
                         return f"Account Summary: Error {resp.status}"
            except Exception as e:
                logger.error(f"GetAccountStatusTool error: {e}")
                return f"Account Summary Error: {str(e)}"
