from pydantic import BaseModel, Field
from typing import Any, Optional
import aiohttp
import json
from app.core.config import settings
from app.core.base_tool import BaseTool

class JournalInput(BaseModel):
    limit: int = Field(default=5, description="Number of recent entries to fetch. Keep this low (5) to save tokens unless deep history is needed.")
    page: int = Field(default=1, description="Page number for pagination. Use > 1 to load older entries if the recent ones are insufficient.")

class GetJournalEntriesTool(BaseTool):
    name: str = "get_journal_entries"
    description: str = "Fetches recent trading journal entries (trades, reflections) for the user. Supports pagination."

    async def run(self, input_data: Any, auth_token: str = None) -> str:
        limit = 5
        page = 1
        
        if isinstance(input_data, dict):
            limit = input_data.get("limit", 5)
            page = input_data.get("page", 1)
        elif isinstance(input_data, str):
            try:
                data = json.loads(input_data)
                limit = data.get("limit", 5)
                page = data.get("page", 1)
            except:
                if input_data.isdigit():
                    limit = int(input_data)
            
        async with aiohttp.ClientSession() as session:
            try:
                # Call API Gateway /journal/
                url = f"{settings.API_GATEWAY_URL}/api/v1/journal/"
                params = {"page": page, "per_page": limit}
                
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
