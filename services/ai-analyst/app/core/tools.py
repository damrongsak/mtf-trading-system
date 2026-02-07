import logging
import json
import aiohttp
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.rag import RAGService

logger = logging.getLogger(__name__)

class BaseTool(BaseModel):
    name: str
    description: str
    
    async def run(self, input_data: Any, auth_token: str = None) -> Any:
        raise NotImplementedError

class KnowledgeBaseTool(BaseTool):
    name: str = "knowledge_base"
    description: str = "Search system documentation, coding strategies, and past journal entries."
    rag_service: Any = Field(exclude=True) # Runtime dependency

    async def run(self, query: str, auth_token: str = None) -> str:
        # We assume RAG service is initialized already
        try:
            docs = await self.rag_service.search_documentation(query)
            # Maybe search strategies too if code-related
            
            context = []
            for d in docs:
                context.append(f"[Source: {d['filename']}]\n{d['content']}")
                
            return "\n\n".join(context) if context else "No relevant documentation found."
        except Exception as e:
            logger.error(f"KB Tool failed: {e}")
            return f"Error retrieving knowledge: {e}"

class AccountStatusTool(BaseTool):
    name: str = "account_status"
    description: str = "Get current account balance, equity, margin, and open positions."

    async def run(self, input_data: Any, auth_token: str = None) -> str:
        if not auth_token:
            return "Error: Authentication required for account access."

        url = f"{settings.API_GATEWAY_URL or 'http://api-gateway:8000'}/api/v1/execution/account/summary"
        headers = {"Authorization": f"Bearer {auth_token}"}

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers, timeout=5.0) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # Allow the agent to parse the raw JSON to be flexible
                        return json.dumps(data.get("data", {}), indent=2)
                    else:
                        text = await resp.text()
                        return f"Error ({resp.status}): {text}"
            except Exception as e:
                return f"Connection failed: {e}"

class TradeHistoryTool(BaseTool):
    name: str = "trade_history"
    description: str = "Fetch recent trade history and performance metrics."

    async def run(self, limit: int = 10, auth_token: str = None) -> str:
        if not auth_token:
            return "Error: Authentication required."
            
        # Using journal endpoint as proxy for trade history
        url = f"{settings.API_GATEWAY_URL or 'http://api-gateway:8000'}/api/v1/journal?per_page={limit}"
        headers = {"Authorization": f"Bearer {auth_token}"}

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers, timeout=5.0) as resp:
                    if resp.status == 200:
                         data = await resp.json()
                         return json.dumps(data, indent=2)
                    return f"Error ({resp.status}): {await resp.text()}"
            except Exception as e:
                return f"Connection failed: {e}"

class ToolRegistry:
    def __init__(self, rag_service: RAGService):
        self.rag = rag_service
        self.tools = {
            "knowledge_base": KnowledgeBaseTool(rag_service=rag_service),
            "account_status": AccountStatusTool(),
            "trade_history": TradeHistoryTool()
        }

    def get_tools(self) -> List[BaseTool]:
        return list(self.tools.values())
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self.tools.get(name)
    
    def get_tool_descriptions(self) -> str:
        return "\n".join([f"- {t.name}: {t.description}" for t in self.tools.values()])
