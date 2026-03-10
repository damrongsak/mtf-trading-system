import asyncio
import httpx
import logging
from typing import Any, Optional, Type
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool as LCTool
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

# Global semaphore for heavy IO to prevent event loop starvation
# Allows 5 concurrent heavy operations across the service
HEAVY_IO_SEMAPHORE = asyncio.Semaphore(5)

class BaseTool(LCTool):
    """
    Standard Olympus BaseTool. 
    Inherits from LangChain's BaseTool for native agent compatibility.
    Adds Institutional Resilience:
    1. AsyncQueue (Semaphore) for heavy IO.
    2. Circuit Breaker for consecutive failures.
    3. Standardized retries.
    """
    is_heavy: bool = Field(default=False, description="Whether this tool performs heavy IO/CPU work.")
    timeout: int = Field(default=60, description="Max execution time in seconds before cancellation.")
    
    # Circuit Breaker state (simplified)
    # Note: In Pydantic v2/LangChain BaseTool, private attributes starting with _ are allowed
    _failure_count: int = 0
    _consecutive_failures_threshold: int = 5

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """Synchronous run fallback (should be avoided in Olympus)."""
        raise NotImplementedError("Use _arun for Olympus BaseTools.")

    async def _arun(self, *args: Any, **kwargs: Any) -> Any:
        """
        Main execution path for LangChain/LangGraph agents.
        Applies resilience and throttling.
        """
        if self._failure_count >= self._consecutive_failures_threshold:
            logger.warning(f"🚨 Circuit Breaker OPEN for tool: {self.name}. Skipping execution.")
            return f"❌ Tool '{self.name}' is currently unavailable (Circuit Breaker OPEN)."

        try:
            if self.is_heavy:
                async with HEAVY_IO_SEMAPHORE:
                    logger.info(f"⏳ Tool '{self.name}' (Heavy) entered execution queue...")
                    return await self._execute_resiliently(*args, **kwargs)
            
            return await self._execute_resiliently(*args, **kwargs)
        except Exception as e:
            self._failure_count += 1
            logger.error(f"❌ Tool '{self.name}' ultimate failure: {e}")
            return f"❌ Tool '{self.name}' failed: {str(e)}"

    async def _execute_resiliently(self, *args: Any, **kwargs: Any) -> Any:
        """Internal execution with retries."""
        result = await self._run_with_retry(*args, **kwargs)
        self._failure_count = 0 # Reset on success
        return result

    async def _run_with_retry(self, *args: Any, **kwargs: Any) -> Any:
        """Actual tool logic should be implemented in run_tool by subclasses."""
        # Normalize input: LangChain arun passes a single arg (dict or str)
        # But if it was called via tool.arun(**dict), it comes in kwargs.
        input_data = args[0] if args else kwargs
        
        # Extract metadata from kwargs
        auth_token = kwargs.get("auth_token")
        request_id = kwargs.get("request_id")
        
        try:
            return await asyncio.wait_for(
                self.run_tool(input_data, auth_token=auth_token, request_id=request_id),
                timeout=self.timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"⌛ Tool '{self.name}' timed out after {self.timeout}s.")
            return f"❌ Tool '{self.name}' timed out after {self.timeout}s. Please try again or simplify the query."

    async def run_tool(self, input_data: Any, auth_token: str = None, request_id: str = None) -> str:
        """Subclasses should implement this instead of run or _arun."""
        raise NotImplementedError("Subclasses must implement run_tool.")
