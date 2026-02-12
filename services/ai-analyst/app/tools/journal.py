from typing import Any, Optional
import aiohttp
from app.core.config import settings
from app.core.base_tool import BaseTool

class GetJournalEntriesTool(BaseTool):
    name: str = "get_journal_entries"
    description: str = "Fetches recent trading journal entries (trades, reflections) for the user."

    async def run(self, input_data: Any, auth_token: str = None) -> str:
        limit = 10
        if isinstance(input_data, int):
            limit = input_data
        elif isinstance(input_data, dict):
            limit = input_data.get("limit", 10)
        elif isinstance(input_data, str) and input_data.isdigit():
            limit = int(input_data)
            
        async with aiohttp.ClientSession() as session:
            try:
                # Call API Gateway /journal/
                url = f"{settings.API_GATEWAY_URL}/api/v1/journal/"
                params = {"page": 1, "per_page": limit}
                
                headers = {}
                if auth_token:
                    if not auth_token.startswith("Bearer "):
                        headers["Authorization"] = f"Bearer {auth_token}"
                    else:
                        headers["Authorization"] = auth_token
                
                async with session.get(url, params=params, headers=headers) as resp:
                     if resp.status == 200:
                         data = await resp.json()
                         entries = data.get("data", [])
                         
                         summary = []
                         for e in entries:
                             summary.append(f"Date: {e.get('date')} | Symbol: {e.get('symbol')} | Result: {e.get('result_pnl')} | Emotion: {e.get('emotion')}")
                         
                         return "\n".join(summary) if summary else "No journal entries found."
                     else:
                         return f"Error fetching journal ({resp.status}): {await resp.text()}"
            except Exception as e:
                return f"Failed to connect to Journal Service: {e}"
