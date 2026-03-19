import logging
from typing import Any, Type, Optional
from pydantic import BaseModel, Field
from app.core.config import settings
from app.core.base_tool import BaseTool
from app.utils.tracing import request_id_ctx, get_request_id, get_account_id
import httpx

logger = logging.getLogger(__name__)

class RiskReviewInput(BaseModel):
    fund_id: Optional[str] = Field(None, description="UUID of the fund to review. If not provided, will attempt to resolve from active account.")

class RiskReviewTool(BaseTool):
    name: str = "risk_review_tool"
    description: str = (
        "Fetches the institutional risk configuration (drawdown thresholds, risk percentage) "
        "and recent account history for a fund. Use this to prepare for a risk rebalancing analysis."
    )
    args_schema: Type[BaseModel] = RiskReviewInput

    async def run_tool(self, input_data: Any, auth_token: str = None, **kwargs) -> str:
        execution_service_url = settings.EXECUTION_SERVICE_URL
        api_key = settings.INTERNAL_API_KEY
        
        fund_id = None
        if isinstance(input_data, dict):
            fund_id = input_data.get("fund_id")
            
        # If fund_id is not provided, try to resolve it from the active account
        if not fund_id:
            account_id = get_account_id()
            if account_id:
                # Need to fetch account details to get fund_id
                # (Assuming get_account_status tool or similar internal call)
                # For now, let's assume the agent might provide it or we fetch it from execution/accounts
                pass

        if not fund_id:
            return "Error: No Fund ID provided or resolved. Please provide a fund_id."

        headers = {
            "X-Internal-API-Key": api_key,
            "X-Request-ID": get_request_id()
        }
        
        results = []
        
        # 1. Fetch Fund Risk Config
        config_url = f"{execution_service_url}/funds/{fund_id}/risk-config"
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(config_url, headers=headers, timeout=10.0)
                if resp.status_code == 200:
                    config = resp.json().get("data", {})
                    results.append(f"**Fund Risk Config ({fund_id})**:")
                    results.append(f"- Risk per Trade: {config.get('risk_percentage', 0)*100:.2f}%")
                    results.append(f"- Max Drawdown Threshold: {config.get('max_drawdown_threshold', 0):.2f}")
                    results.append(f"- Max USD Risk per Trade: ${config.get('max_risk_per_trade', 0):.2f}")
                else:
                    results.append(f"Error fetching fund config: {resp.status_code}")
            except Exception as e:
                results.append(f"Fund Config Error: {str(e)}")

        # 2. Add context about account health if available
        # (The agent can also use get_account_status tool separately)
        
        return "\n".join(results)
