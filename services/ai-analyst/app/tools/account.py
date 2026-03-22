import logging
from typing import Any, Type
from pydantic import BaseModel
from app.core.config import settings
from app.core.base_tool import BaseTool
from app.utils.tracing import request_id_ctx, get_request_id, get_account_id
import httpx

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
        # Use direct internal call to execution service per guardrails
        execution_service_url = settings.EXECUTION_SERVICE_URL
        api_key = settings.INTERNAL_API_KEY
        
        # Get account_id from context (set by middleware from X-Broker-Account-ID header)
        account_id = get_account_id()
        
        if not account_id:
            # Fallback for old implementations or missing header: try to find an active account in DB?
            # For now, return a helpful error so the agent knows it needs context.
            return "Error: No Active Account ID found in context. Please ensure X-Broker-Account-ID is passed via Gateway."

        headers = {
            "X-Internal-API-Key": api_key,
            "X-Request-ID": get_request_id()
        }
        if auth_token:
            headers["Authorization"] = auth_token if auth_token.startswith("Bearer ") else f"Bearer {auth_token}"
        
        url = f"{execution_service_url}/account/summary"
        payload = {"broker_account_id": account_id}
        
        logger.error(f"GetAccountStatusTool: Calling {url} with account_id={account_id}")
        logger.error(f"GetAccountStatusTool: Internal API Key is {'set' if api_key else 'MISSING'}")

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(url, json=payload, headers=headers, timeout=10.0)
                logger.error(f"GetAccountStatusTool: Received status={resp.status_code}")
                if resp.status_code != 200:
                    logger.error(f"GetAccountStatusTool: Error response: {resp.text}")
                
                if resp.status_code == 200:
                    json_resp = resp.json()
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
                        
                    leverage = data.get("leverage", 30)
                    currency = data.get("currency", "USD")
                    data_source_id = data.get("data_source_id", "N/A")
                    
                    report = (
                        f"**Account Health**:\n"
                        f"- Balance: ${balance:,.2f} {currency}\n"
                        f"- Equity: ${equity:,.2f} {currency}\n"
                        f"- Leverage: 1:{leverage}\n"
                        f"- Data Source: {data_source_id}\n"
                        f"- Margin Used: ${margin_used:,.2f}\n"
                        f"- Active Positions: {len(open_positions)}\n"
                        f"- Total Risk Exposure: ${total_exposure_risk:,.2f}\n"
                        f"- Open Trades: {', '.join(positions_summary) if positions_summary else 'None'}"
                    )
                    return report
                else:
                    return f"Account Summary: Error {resp.status_code} - {resp.text}"
            except Exception as e:
                logger.error(f"GetAccountStatusTool error: {e}")
                return f"Account Summary Error: {str(e)}"
