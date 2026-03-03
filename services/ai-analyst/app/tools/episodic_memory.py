from typing import Dict, Any, List
import logging
import httpx
from langchain_core.tools import tool
from app.core.config import settings

logger = logging.getLogger(__name__)

# Note: We need internal API tokens or impersonation because trades are secured by JWT 
# in the API Gateway. The implementation plan specified we should access the DB directly
# or use a service auth token. For modularity, we use a service token and the API if available, 
# or fallback to direct DB if implemented in JournalService.

@tool
async def fetch_unanalyzed_trades(limit: int = 5) -> Dict[str, Any]:
    """
    Fetches recent closed trades that do not have an associated AI-generated JournalEntry.
    These are the trades that the AI Analyst needs to review and learn from to build its Episodic Memory.
    """
    try:
        # In a real microservice environment, the AI analyst should call the API Gateway 
        # using a secure internal service token to get trades.
        # Since we are implementing MVP for AI Episodic Memory, we will mock the API call
        # structure here but point to the gateway's internal port.
        
        # NOTE: Gateway needs to support a service-level endpoint to fetch ALL trades lacking AI journals.
        # We'll use a placeholder URL here which we will need to implement in api-gateway next.
        async with httpx.AsyncClient(timeout=10.0) as client:
            # We assume api-gateway exposes an internal endpoint for the ai service
            url = f"{settings.API_GATEWAY_URL}/internal/memory/pending-trades?limit={limit}"
            
            # Use internal service auth header
            headers = {"Authorization": f"Bearer {settings.SYSTEM_API_KEY}"}
            
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            return {"status": "success", "trades": data.get("data", [])}
            
    except httpx.HTTPError as e:
        logger.error(f"HTTP error fetching unanalyzed trades: {e}")
        return {"status": "error", "message": f"Service unavailable: {str(e)}", "trades": []}
    except Exception as e:
        logger.error(f"Unexpected error fetching unanalyzed trades: {e}")
        return {"status": "error", "message": str(e), "trades": []}

@tool
async def save_episodic_memory(trade_id: str, insight: str, game_level: str = "B_GAME") -> Dict[str, Any]:
    """
    Saves an AI-generated insight for a specific trade, forming an Episodic Memory.
    This creates a JournalEntry marked as is_ai_generated=True.
    
    Args:
        trade_id: The UUID of the trade being analyzed.
        insight: The actionable lesson or insight learned from this trade outcome.
        game_level: The psychological performance rating (A_GAME, B_GAME, C_GAME).
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{settings.API_GATEWAY_URL}/internal/memory/save-insight"
            headers = {"Authorization": f"Bearer {settings.SYSTEM_API_KEY}"}
            
            payload = {
                "trade_id": trade_id,
                "ai_insight": insight,
                "game_level": game_level
            }
            
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            return {"status": "success", "message": f"Episodic memory saved for trade {trade_id}"}
            
    except Exception as e:
        logger.error(f"Error saving episodic memory: {e}")
        return {"status": "error", "message": str(e)}
