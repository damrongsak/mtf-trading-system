import httpx
from typing import Optional, Any
from pydantic import BaseModel, Field
from app.core.base_tool import BaseTool
from app.core.config import settings
from app.core.utils import parse_tool_input
import logging

logger = logging.getLogger(__name__)

class DeployTelegramAlertInput(BaseModel):
    symbol: str = Field(..., description="The symbol to monitor (e.g. 'XAUUSD', 'EURUSD')")
    condition: str = Field(..., description="The condition for the alert (PRICE_ABOVE or PRICE_BELOW)")
    threshold: float = Field(..., description="The price threshold that triggers the alert")
    is_active: bool = Field(True, description="Whether the alert should be active immediately")

class DeployTelegramAlertTool(BaseTool):
    name: str = "deploy_telegram_alert"
    description: str = (
        "Deploys a persistent price alert that notifies the user via Telegram when a specific market threshold is met. "
        "Use this for 'set-and-forget' monitoring of key support/resistance levels or breakout points. "
        "The alert will trigger once and then deactivate."
    )
    args_schema: Any = DeployTelegramAlertInput

    async def run_tool(self, input_data: Any, auth_token: str = None, request_id: str = None) -> str:
        input_dict = parse_tool_input(input_data)
        
        headers = {}
        if auth_token:
            headers["Authorization"] = auth_token if auth_token.startswith("Bearer ") else f"Bearer {auth_token}"

        base_url = settings.API_GATEWAY_URL
        url = f"{base_url}/api/v1/alerts/"
        
        # Validate condition
        condition = str(input_dict.get("condition", "")).upper()
        if condition not in ["PRICE_ABOVE", "PRICE_BELOW"]:
            return f"❌ Invalid condition '{condition}'. Use 'PRICE_ABOVE' or 'PRICE_BELOW'."

        payload = {
            "symbol": input_dict.get("symbol"),
            "condition": condition,
            "threshold": input_dict.get("threshold"),
            "is_active": input_dict.get("is_active", True)
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers, timeout=10.0)
                
                if response.status_code == 201:
                    res_json = response.json()
                    # Standardized response has data nested in 'data' field
                    data = res_json.get("data", {})
                    alert_id = data.get("id")
                    return (
                        f"✅ **Telegram Alert Deployed Successfully**\n"
                        f"- **ID**: `{alert_id}`\n"
                        f"- **Asset**: `{payload['symbol']}`\n"
                        f"- **Trigger**: `{payload['condition']} {payload['threshold']}`\n"
                        f"- **Notification**: Telegram (Persistent Agent Monitoring)\n\n"
                        f"> [!NOTE]\n"
                        f"> The system will now monitor `{payload['symbol']}` every minute. "
                        f"You will receive a Telegram message the moment the price crosses this threshold."
                    )
                else:
                    return f"❌ Error deploying alert: {response.status_code} - {response.text}"

        except Exception as e:
            logger.error(f"Deploy Telegram Alert Tool error: {e}")
            return f"❌ Error connecting to API Gateway for alert deployment: {str(e)}"
