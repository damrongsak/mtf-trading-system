from typing import Any, Optional
import aiohttp
import logging
from app.core.config import settings
from app.core.base_tool import BaseTool

logger = logging.getLogger(__name__)

class GetAccountStatusTool(BaseTool):
    name: str = "get_account_status"
    description: str = "Fetches comprehensive account health including balance, equity, margin, open positions, and risk metrics."

    async def run(self, input_data: Any = None, auth_token: str = None) -> str:
        async with aiohttp.ClientSession() as session:
            try:
                headers = {}
                if auth_token:
                    headers["Authorization"] = auth_token
                
                url = f"{settings.API_GATEWAY_URL}/api/v1/execution/account/summary"
                
                async with session.get(url, headers=headers) as resp:
                     if resp.status == 200:
                         json_resp = await resp.json()
                         data = json_resp.get("data", {})
                         
                         def parse_float(v):
                             if isinstance(v, (float, int)): return float(v)
                             if isinstance(v, str):
                                 clean = v.split(' ')[0].replace(',', '')
                                 try:
                                     return float(clean)
                                 except:
                                     return 0.0
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
                         return f"Error fetching account data ({resp.status}): {await resp.text()}"
            except Exception as e:
                return f"Failed to connect to Execution Service: {e}"
