import httpx
import os
from typing import Dict, Any

EXECUTION_SERVICE_URL = os.getenv("EXECUTION_SERVICE_URL", "http://execution:8000")

class ExecutionClient:
    def __init__(self):
        self.base_url = EXECUTION_SERVICE_URL
        # In async context, we might want to instantiate client per request or use a singleton with lifecycle.
        # For simplicity in this step, we'll use a context manager per request, 
        # or we could make the methods async and use httpx.AsyncClient().
        
    async def place_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Place an order via the Execution Service.
        """
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(f"{self.base_url}/orders", json=order_data, timeout=10.0)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPError as e:
                # Log error or re-raise custom exception
                print(f"Execution Service Error: {e}")
                raise

execution_client = ExecutionClient()
