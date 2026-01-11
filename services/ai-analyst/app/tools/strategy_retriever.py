from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, List, Dict
import aiohttp
from app.core.config import settings

class StrategyRetrieverInput(BaseModel):
    user_id: str = Field(description="The ID of the user.")

class StrategyRetrieverTool(BaseTool):
    name: str = "list_active_strategies"
    description: str = "Lists the user's currently active strategies. Returns ID, Symbol, Type, and Semantic Description."
    args_schema: Type[BaseModel] = StrategyRetrieverInput

    def _run(self, **kwargs):
        raise NotImplementedError("Use _arun instead")

    async def _arun(self, user_id: str) -> List[Dict]:
        base_url = getattr(settings, "API_GATEWAY_URL", "http://api-gateway:8000")
        url = f"{base_url}/api/v1/strategies/"
        
        async with aiohttp.ClientSession() as session:
            try:
                # Filter by active? The API currently lists all. We filter client side.
                # headers = {"x-user-id": user_id} 
                headers = {} # Auth usually handled by Gateway middleware 
                
                async with session.get(url, headers=headers, timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        strategies = data.get("data", [])
                        
                        # Map to simplified semantic format
                        result = []
                        for s in strategies:
                            if s.get("is_active"):
                                meta = s.get("config_json", {}).get("meta_description", "No description")
                                result.append({
                                    "id": s["id"],
                                    "name": s["name"],
                                    "type": s["template_id"],
                                    "description": meta
                                })
                        return result
                    else:
                        return [{"error": f"Failed to fetch strategies: {resp.status}"}]
            except Exception as e:
                return [{"error": f"Error fetching strategies: {e}"}]
