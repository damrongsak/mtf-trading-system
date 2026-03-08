import aiohttp
import logging
import json
from typing import Optional, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

class OpenRouterClient:
    """
    Simplified client for OpenRouter API to provide secondary LLM verification.
    """
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.site_url = "https://mtf-olympus.trade" # For OpenRouter rankings
        self.site_name = "MTF Olympus"

    async def generate_completion(
        self, 
        model: str, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        temperature: float = 0.3
    ) -> Optional[str]:
        if not self.api_key:
            logger.error("OpenRouter API key is missing.")
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": self.site_url,
            "X-Title": self.site_name,
            "Content-Type": "application/json"
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, headers=headers, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data['choices'][0]['message']['content']
                    else:
                        error_text = await resp.text()
                        logger.error(f"OpenRouter API failed ({resp.status}): {error_text}")
                        return None
        except Exception as e:
            logger.error(f"OpenRouter request failed: {e}")
            return None
