
import httpx
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://api-gateway:8000")
INTERNAL_KEY = os.getenv("INTERNAL_API_KEY", "dev-internal-key")

class APIGatewayClient:
    """
    Client for internal communication with API Gateway.
    """
    def __init__(self):
        self.base_url = API_GATEWAY_URL
        self.headers = {"x-internal-key": INTERNAL_KEY}
        
    async def execute_signal(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Send a signal to API Gateway for execution and journaling.
        """
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/api/v1/internal/signals",
                    json=payload,
                    headers=self.headers,
                    timeout=5.0
                )
                if resp.status_code == 200:
                    logger.info(f"Signal executed successfully: {resp.json()}")
                    return resp.json()
                else:
                    logger.error(f"Failed to execute signal: {resp.status_code} {resp.text}")
                    return None
            except Exception as e:
                logger.error(f"Error calling API Gateway: {e}")
                return None

gateway_client = APIGatewayClient()
