from pydantic import BaseModel
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx
import uuid
import logging

logger = logging.getLogger(__name__)

class BaseTool(BaseModel):
    name: str
    description: str
    
    # Circuit Breaker state (simplified)
    # In a real distributed system, this would be in Redis
    _failure_count: int = 0
    _consecutive_failures_threshold: int = 5
    
    async def run(self, input_data: Any, auth_token: str = None, request_id: str = None) -> Any:
        raise NotImplementedError

    async def run_resilient(self, input_data: Any, auth_token: str = None, request_id: str = None) -> Any:
        """
        Executes the tool with built-in retries and circuit breaker checks.
        """
        if self._failure_count >= self._consecutive_failures_threshold:
            logger.warning(f"🚨 Circuit Breaker OPEN for tool: {self.name}. Skipping execution.")
            return f"❌ Tool '{self.name}' is currently unavailable (Circuit Breaker OPEN)."

        try:
            result = await self._run_with_retry(input_data, auth_token=auth_token, request_id=request_id)
            self._failure_count = 0 # Reset on success
            return result
        except Exception as e:
            self._failure_count += 1
            logger.error(f"❌ Tool '{self.name}' failed after retries: {e}")
            return f"❌ Tool '{self.name}' failed: {str(e)}"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError)),
        reraise=True
    )
    async def _run_with_retry(self, input_data: Any, auth_token: str = None, request_id: str = None) -> Any:
        return await self.run(input_data, auth_token=auth_token, request_id=request_id)
