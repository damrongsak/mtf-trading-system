import logging
import httpx
from typing import Any, Optional, Type
from pydantic import BaseModel, Field
from app.core.base_tool import BaseTool
from app.core.config import settings

logger = logging.getLogger(__name__)

class ModifyTradeInput(BaseModel):
    broker_account_id: str = Field(..., description="ID of the broker account (UUID)")
    broker_trade_id: str = Field(..., description="ID of the position or order at the broker")
    sl_price: Optional[float] = Field(None, description="New Stop Loss price")
    tp_price: Optional[float] = Field(None, description="New Take Profit price")
    trailing_sl: Optional[bool] = Field(None, description="Whether to enable trailing stop loss")
    is_position: bool = Field(True, description="True if amending a filled position, False if amending a pending order")

class ModifyTradeTool(BaseTool):
    name: str = "modify_trade"
    description: str = (
        "Amends an existing open position or pending order at the broker. "
        "Extremely useful for securing profits by moving SL to breakeven or trailing SL "
        "during high-volatility events or trend shifts."
    )
    args_schema: Type[BaseModel] = ModifyTradeInput

    async def run_tool(self, input_data: Any, auth_token: str = None, **kwargs) -> str:
        # Normalize input_data
        if isinstance(input_data, dict):
            pass
        elif hasattr(input_data, "dict"):
            input_data = input_data.model_dump()
        else:
            return f"Invalid input format for {self.name}"

        broker_account_id = input_data.get("broker_account_id")
        broker_trade_id = input_data.get("broker_trade_id")
        is_position = input_data.get("is_position", True)

        endpoint = "positions" if is_position else "orders"
        # API Gateway routes /api/v1/execution/... to execution service
        url = f"{settings.API_GATEWAY_URL}/api/v1/execution/{endpoint}/{broker_trade_id}"

        payload = {
            "broker_account_id": broker_account_id,
            "sl_price": input_data.get("sl_price"),
            "tp_price": input_data.get("tp_price"),
            "trailing_sl": input_data.get("trailing_sl")
        }

        # Filter None values but keep broker_account_id
        payload = {k: v for k, v in payload.items() if v is not None or k == "broker_account_id"}

        async with httpx.AsyncClient() as client:
            try:
                # Use internal API key for service-to-service communication
                headers = {"X-Internal-API-Key": settings.INTERNAL_API_KEY}
                
                resp = await client.put(url, json=payload, headers=headers, timeout=10.0)
                
                if resp.status_code == 200:
                    data = resp.json()
                    return f"✅ Successfully modified {endpoint[:-1]} {broker_trade_id}. Server response: {data.get('data')}"
                else:
                    error_msg = resp.text
                    try:
                        error_msg = resp.json().get("detail", resp.text)
                    except:
                        pass
                    return f"❌ Failed to modify {endpoint[:-1]} {broker_trade_id}: {resp.status_code} - {error_msg}"
            except Exception as e:
                logger.error(f"ModifyTradeTool error: {e}")
                return f"❌ Error connecting to execution service: {str(e)}"
