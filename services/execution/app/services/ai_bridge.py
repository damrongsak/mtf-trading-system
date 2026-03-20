import httpx
import logging
from typing import Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class AIBridge:
    """
    Bridge service for interacting with the AI Analyst.
    Called by background workers to trigger trade analysis.
    """
    
    @staticmethod
    async def run_entry_analysis(trade_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Trigger 'Reason Learning' analysis for a new trade fill.
        """
        url = f"{settings.AI_ANALYST_URL}/api/v1/ai/agent/entry-reason/analyze"
        # Ensure JSON serializable (Enums to strings)
        serializable_data = {
            k: (v.value if hasattr(v, "value") else v) 
            for k, v in trade_data.items()
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    json=serializable_data,
                    headers={"X-Internal-API-Key": settings.INTERNAL_API_KEY}
                )
                if response.status_code == 200:
                    result = response.json().get("data", {})
                    logger.info(f"AIBridge: Entry analysis completed for trade {serializable_data.get('trade_id')}")
                    return result
                else:
                    logger.error(f"AIBridge: Entry analysis failed (HTTP {response.status_code}): {response.text}")
        except Exception as e:
            logger.error(f"AIBridge: Error calling AI Analyst for entry analysis: {e}")
        return None

    @staticmethod
    async def run_post_mortem(trade_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Trigger 'Grading' analysis for a closed trade.
        """
        url = f"{settings.AI_ANALYST_URL}/api/v1/ai/agent/post-mortem/analyze"
        # Ensure JSON serializable (Enums to strings)
        serializable_data = {
            k: (v.value if hasattr(v, "value") else v) 
            for k, v in trade_data.items()
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    json=serializable_data,
                    headers={"X-Internal-API-Key": settings.INTERNAL_API_KEY}
                )
                if response.status_code == 200:
                    result = response.json().get("data", {})
                    logger.info(f"AIBridge: Post-mortem analysis completed for trade {serializable_data.get('trade_id')}")
                    return result
                else:
                    logger.error(f"AIBridge: Post-mortem analysis failed (HTTP {response.status_code}): {response.text}")
        except Exception as e:
            logger.error(f"AIBridge: Error calling AI Analyst for post-mortem: {e}")
        return None
