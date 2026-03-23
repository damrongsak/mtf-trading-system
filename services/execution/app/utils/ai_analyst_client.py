import httpx
import logging
import os
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class AIAnalystClient:
    """
    Async client for communicating with the ai-analyst service.
    """
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.getenv("AI_ANALYST_URL", "http://ai-analyst:8002")
        self.timeout = 30.0

    async def get_correlation_analysis(self, prices: Dict[str, List[float]]) -> Dict[str, Any]:
        """
        Request PCA-based correlation analysis from AI Analyst.
        """
        url = f"{self.base_url}/api/v1/ai/risk/correlation"
        payload = {
            "prices": prices,
            "threshold": 0.6
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch correlation analysis from AI Analyst: {e}")
            return {"status": "error", "reason": str(e)}
