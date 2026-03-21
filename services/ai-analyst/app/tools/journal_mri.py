from pydantic import BaseModel, Field
from typing import Any, Optional, List
import aiohttp
import json
import logging
from app.core.config import settings
from app.core.base_tool import BaseTool

logger = logging.getLogger(__name__)

class JournalMRIInput(BaseModel):
    lookback_days: int = Field(default=7, description="Number of days to look back for journal entries.")
    limit: int = Field(default=10, description="Maximum number of entries to analyze.")

class JournalMRITool(BaseTool):
    name: str = "journal_mri_retriever"
    description: str = "Fetches deep psychological journal data (mental states, root causes, mistakes) for RAG-based coaching."

    async def run_tool(self, input_data: Any, auth_token: str = None, request_id: str = None, **kwargs) -> str:
        lookback = 7
        limit = 10
        
        if isinstance(input_data, dict):
            lookback = input_data.get("lookback_days", 7)
            limit = input_data.get("limit", 10)
        
        async with aiohttp.ClientSession() as session:
            try:
                # 1. Fetch from API Gateway /journal/ with lookback
                # Since the gateway /journal endpoint doesn't support 'days' directly in the list, 
                # we'll fetch the first few pages and filter, or just use the per_page limit.
                url = f"{settings.API_GATEWAY_URL}/api/v1/journal/"
                params = {"per_page": limit, "page": 1}
                
                headers = {}
                if auth_token:
                    headers["Authorization"] = f"Bearer {auth_token}" if not auth_token.startswith("Bearer ") else auth_token
                
                async with session.get(url, params=params, headers=headers, timeout=5.0) as resp:
                    if resp.status != 200:
                        return f"Error fetching journal: {resp.status}"
                    
                    data = await resp.json()
                    entries = data.get("data", [])
                    
                    if not entries:
                        return "No recent journal entries found to analyze."
                    
                    # 2. Format detailed context for the MRI Node
                    formatted_context = []
                    for e in entries:
                        entry_id = e.get("id")
                        symbol = e.get("symbol", "N/A")
                        pnl = e.get("pnl_amount", 0)
                        
                        # Extract deep psychological data if present
                        mental = e.get("mental_state", {})
                        root = e.get("root_cause", {})
                        
                        emotion_summary = []
                        if mental:
                            for key in ["greed_level", "fear_level", "tilt_level", "discipline_level", "confidence_level"]:
                                val = mental.get(key)
                                if val is not None:
                                    emotion_summary.append(f"{key.replace('_level', '').capitalize()}: {val}/10")
                        
                        mistake = root.get("flaw", "No specific mistake logged")
                        lesson = root.get("lesson", "")
                        
                        context_blob = (
                            f"--- Entry {entry_id} ---\n"
                            f"Symbol: {symbol} | PnL: ${pnl}\n"
                            f"Psychological State: {', '.join(emotion_summary) if emotion_summary else 'Normal'}\n"
                            f"Primary Mistake: {mistake}\n"
                            f"Lesson Learned: {lesson}\n"
                        )
                        formatted_context.append(context_blob)
                    
                    return "\n".join(formatted_context)
                    
            except Exception as e:
                logger.error(f"MRI Tool Failed: {e}")
                return f"Failed to retrieve psychological context: {e}"
