import httpx
import logging
import asyncio
from typing import Optional, Any, Dict

logger = logging.getLogger(__name__)

class InternalHTTPClient:
    """
    Resilient HTTP Client for internal service-to-service communication.
    Features:
    - Retries (3x) for connection errors.
    - Standard timeouts.
    - Centralized logging.
    """
    
    def __init__(self, timeout: float = 600.0, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        # Transport with retries
        self.transport = httpx.AsyncHTTPTransport(
            retries=max_retries,
            trust_env=False # Avoid proxy issues in internal docker network
        )

    async def get_client(self) -> httpx.AsyncClient:
        """Returns a configured AsyncClient."""
        return httpx.AsyncClient(
            transport=self.transport, 
            timeout=self.timeout
        )

# Global Instance
internal_http_client = InternalHTTPClient()

async def get_internal_client() -> httpx.AsyncClient:
    """Helper for FastAPI dependency or direct use."""
    return await internal_http_client.get_client()
