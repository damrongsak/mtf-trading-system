from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional, Type
import aiohttp
from app.core.config import settings

class AccountStatusInput(BaseModel):
    pass

class GetAccountStatusTool(BaseTool):
    name: str = "get_account_status"
    description: str = "Fetches current account balance, equity, margin, and open positions."
    args_schema: Type[BaseModel] = AccountStatusInput

    def _run(self):
        raise NotImplementedError("Use _arun instead")

    async def _arun(self):
        async with aiohttp.ClientSession() as session:
            try:
                # Calling Execution service /account/summary
                async with session.get(f"{settings.EXECUTION_SERVICE_URL}/account/summary") as resp:
                     if resp.status == 200:
                         data = await resp.json()
                         return str(data)
                     else:
                         return f"Error fetching account data: {resp.status}"
            except Exception as e:
                return f"Failed to connect to Execution Service: {e}"
