import httpx
from typing import Optional, Dict
from app.core.config import settings
import logging
import time

logger = logging.getLogger(__name__)

class PromptRegistry:
    def __init__(self):
        self._cache: Dict[str, dict] = {} # {id: {text: str, expires: float}}
        self._ttl = 300 # 5 minutes

    async def get_prompt_text(self, prompt_id: str) -> Optional[str]:
        """
        Fetch prompt template from API Gateway.
        Uses in-memory caching.
        """
        # Check Cache
        if prompt_id in self._cache:
            entry = self._cache[prompt_id]
            if time.time() < entry["expires"]:
                return entry["text"]

        # Fetch from Gateway
        try:
            async with httpx.AsyncClient() as client:
                url = f"{settings.API_GATEWAY_URL}/api/v1/prompts/{prompt_id}"
                # TODO: Add Service Token/Auth if needed. Assuming internal network trust for MVP.
                response = await client.get(url, timeout=5.0)
                
                if response.status_code == 200:
                    data = response.json()
                    template = data.get("template", "")
                    
                    # Cache it
                    self._cache[prompt_id] = {
                        "text": template,
                        "expires": time.time() + self._ttl
                    }
                    return template
                elif response.status_code == 404:
                    logger.warning(f"Prompt {prompt_id} not found in Gateway.")
                    return None
                else:
                    logger.error(f"Failed to fetch prompt {prompt_id}: {response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"Error fetching prompt {prompt_id}: {e}")
            return None

# Global Instance
prompt_registry = PromptRegistry()
