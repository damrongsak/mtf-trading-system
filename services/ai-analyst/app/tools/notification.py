import logging
from typing import Any, Optional, Type
from pydantic import BaseModel, Field
from app.core.base_tool import BaseTool
from app.core.config import settings
import httpx

logger = logging.getLogger(__name__)

class NotificationInput(BaseModel):
    message: str = Field(
        description="The message text to send. Supports Markdown formatting (bold with **, tables, code blocks)."
    )

class SendNotificationTool(BaseTool):
    name: str = "send_notification"
    description: str = (
        "Sends a message or report to the user's linked Telegram chat. "
        "Use this when the user asks to 'send to Telegram', 'notify me', or 'alert me'. "
        "The user's chat_id is automatically resolved from their account profile — "
        "no need to provide it manually. Supports Markdown formatting."
    )
    args_schema: Type[BaseModel] = NotificationInput

    async def run_tool(self, input_data: Any, auth_token: str = None, **kwargs) -> str:
        message = ""
        if isinstance(input_data, dict):
            message = input_data.get("message", "")
        elif isinstance(input_data, str):
            message = input_data

        if not message:
            return "❌ Notification failed: Empty message provided."

        if not auth_token:
            return "❌ Notification failed: No auth token available."

        headers = {
            "Authorization": auth_token if auth_token.startswith("Bearer ") else f"Bearer {auth_token}"
        }

        base_url = getattr(settings, "API_GATEWAY_URL", "http://api-gateway:8000")
        send_url = f"{base_url}/api/v1/telegram/send"

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    send_url,
                    json={"message": message},
                    headers=headers
                )

            if resp.status_code == 200:
                result = resp.json()
                chat_id = result.get("chat_id", "?")
                return f"✅ Message successfully sent to your Telegram (chat_id: {chat_id})."
            elif resp.status_code == 404:
                return "❌ Notification failed: Your Telegram account is not linked."
            else:
                return f"❌ Notification failed (HTTP {resp.status_code}): {resp.text}"

        except Exception as e:
            logger.error(f"SendNotificationTool error: {e}")
            return f"❌ Notification failed: {str(e)}"
