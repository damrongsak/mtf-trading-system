from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional, Type, List
import aiohttp
from app.core.config import settings

class JournalInput(BaseModel):
    limit: int = Field(default=10, description="Number of recent entries to fetch")

class GetJournalEntriesTool(BaseTool):
    name: str = "get_journal_entries"
    description: str = "Fetches recent trading journal entries (trades, reflections) for the user."
    args_schema: Type[BaseModel] = JournalInput

    def _run(self, limit: int = 10):
        raise NotImplementedError("Use _arun instead")

    async def _arun(self, limit: int = 10):
        async with aiohttp.ClientSession() as session:
            try:
                # Call API Gateway /journal/
                url = f"{settings.API_GATEWAY_URL}/api/v1/journal/"
                params = {"page": 1, "per_page": limit}
                
                # Note: Internal calls might need a service token or handle auth differently.
                # Assuming internal network trust or mock for now.
                # In prod, we'd pass headers={"Authorization": ...} if needed.
                
                async with session.get(url, params=params) as resp:
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
