from typing import Dict, Any, List, Type
import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

# Note: We need internal API tokens or impersonation because trades are secured by JWT 
# in the API Gateway. The implementation plan specified we should access the DB directly
# or use a service auth token. For modularity, we use a service token and the API if available, 
# or fallback to direct DB if implemented in JournalService.

from app.core.base_tool import BaseTool
from pydantic import BaseModel, Field

class FetchUnanalyzedTradesInput(BaseModel):
    limit: int = Field(default=5, description="Number of trades to fetch")

class FetchUnanalyzedTradesTool(BaseTool):
    name: str = "fetch_unanalyzed_trades"
    description: str = (
        "Fetches recent closed trades that do not have an associated AI-generated JournalEntry. "
        "These are the trades that the AI Analyst needs to review and learn from to build its Episodic Memory."
    )
    args_schema: Type[BaseModel] = FetchUnanalyzedTradesInput

    async def run_tool(self, input_data: Any, **kwargs) -> Dict[str, Any]:
        limit = 5
        if isinstance(input_data, dict):
            limit = input_data.get("limit", limit)
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"{settings.API_GATEWAY_URL}/api/v1/journal/internal/memory/pending-trades?limit={limit}"
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                return {"status": "success", "trades": data.get("data", [])}
        except Exception as e:
            logger.error(f"Error fetching unanalyzed trades: {e}")
            return {"status": "error", "message": str(e), "trades": []}

class SaveEpisodicMemoryInput(BaseModel):
    trade_id: str = Field(..., description="The UUID of the trade being analyzed.")
    insight: str = Field(..., description="The actionable lesson or insight learned from this trade outcome.")
    game_level: str = Field(default="B_GAME", description="The psychological performance rating (A_GAME, B_GAME, C_GAME).")

class SaveEpisodicMemoryTool(BaseTool):
    name: str = "save_episodic_memory"
    description: str = (
        "Saves an AI-generated insight for a specific trade, forming an Episodic Memory. "
        "This creates a JournalEntry marked as is_ai_generated=True."
    )
    args_schema: Type[BaseModel] = SaveEpisodicMemoryInput

    async def run_tool(self, input_data: Any, **kwargs) -> Dict[str, Any]:
        trade_id = ""
        insight = ""
        game_level = "B_GAME"
        
        if isinstance(input_data, dict):
            trade_id = input_data.get("trade_id", "")
            insight = input_data.get("insight", "")
            game_level = input_data.get("game_level", "B_GAME")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"{settings.API_GATEWAY_URL}/api/v1/journal/internal/memory/save-insight"
                payload = {
                    "trade_id": trade_id,
                    "ai_insight": insight,
                    "game_level": game_level
                }
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return {"status": "success", "message": f"Episodic memory saved for trade {trade_id}"}
        except Exception as e:
            logger.error(f"Error saving episodic memory: {e}")
            return {"status": "error", "message": str(e)}
