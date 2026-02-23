from app.core.base_tool import BaseTool
from pydantic import BaseModel, Field
from typing import Any, List, Dict, Optional
import aiohttp
from app.core.config import settings


class StrategyRetrieverTool(BaseTool):
    name: str = "list_active_strategies"
    description: str = "Lists the user's currently active strategies. Returns ID, Symbol, Type, and Semantic Description."

    async def run(self, input_data: Any = None, auth_token: str = None, request_id: str = None) -> str:
        base_url = getattr(settings, "API_GATEWAY_URL", "http://api-gateway:8000")
        url = f"{base_url}/api/v1/strategies/"

        headers = {}
        if auth_token:
            if not auth_token.startswith("Bearer "):
                headers["Authorization"] = f"Bearer {auth_token}"
            else:
                headers["Authorization"] = auth_token

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        strategies = data.get("data", [])

                        active = [s for s in strategies if s.get("is_active")]
                        if not active:
                            return "No active strategies found."

                        lines = ["### Active Strategies"]
                        for s in active:
                            meta = s.get("config_json", {}).get("meta_description", "No description")
                            lines.append(
                                f"- **ID**: {s['id']} | **Name**: {s['name']} | **Type**: {s.get('template_id', 'N/A')} | {meta}"
                            )
                        return "\n".join(lines)
                    else:
                        return f"Failed to fetch strategies: {resp.status}"
            except Exception as e:
                return f"Error fetching strategies: {e}"
