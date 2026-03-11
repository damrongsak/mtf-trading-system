from pydantic import BaseModel, Field
from typing import Any, Optional, Type
import aiohttp
import logging
from app.core.config import settings
from app.core.base_tool import BaseTool

logger = logging.getLogger(__name__)

class OpenClawInput(BaseModel):
    task: str = Field(..., description="The research task or objective for the AI browser (e.g. 'Read the latest gold analysis on Bloomberg and summarize the key drivers')")
    url: Optional[str] = Field(None, description="Optional starting URL for the research")

class OpenClawResearcherTool(BaseTool):
    """
    Agentic Browser Research tool using OpenClaw.
    Allows for navigating complex websites, solving CAPTCHAs, and extracting structured data.
    """
    name: str = "open_claw_research"
    description: str = (
        "Performs high-fidelity web research using an autonomous AI browser. "
        "Use this for complex sites (Bloomberg, FT, Reuters), login-protected content, "
        "or when standard scrapers fail. Best for deep intelligence gathering."
    )
    args_schema: Type[BaseModel] = OpenClawInput
    is_heavy: bool = True

    async def run_tool(self, input_data: Any, **kwargs) -> str:
        task = ""
        url = None
        
        if hasattr(input_data, "dict"):
            input_data = input_data.dict()
            
        if isinstance(input_data, dict):
            task = input_data.get("task", "")
            url = input_data.get("url")
        elif isinstance(input_data, str):
            task = input_data

        if not task:
            return "Error: No research task provided."

        # OpenClaw Gateway Integration
        # Based on OpenClaw API standards (Agentic Browser Workflow)
        endpoint = f"{settings.OPENCLAW_URL}/tools/invoke"
        
        headers = {
            "Content-Type": "application/json"
        }
        if settings.OPENCLAW_GATEWAY_TOKEN:
            headers["Authorization"] = f"Bearer {settings.OPENCLAW_GATEWAY_TOKEN}"
        
        # Payload for /tools/invoke
        payload = {
            "tool": "researcher", # Standard OpenClaw researcher tool
            "input": {
                "task": task,
                "url": url
            }
        }

        logger.info(f"OpenClaw: Executing research task: {task}")
        
        try:
            timeout = aiohttp.ClientTimeout(total=180.0) # Research can take time
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(endpoint, json=payload, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # Extract the final answer or summary from the agent response
                        result = data.get("result", data.get("summary", "Task completed but no summary provided."))
                        logger.info(f"OpenClaw: Task completed successfully.")
                        return f"--- OpenClaw Research Result ---\n\n{result}"
                    else:
                        error_text = await resp.text()
                        logger.error(f"OpenClaw API error: {resp.status} - {error_text}")
                        return f"Error from OpenClaw service: {resp.status}. Please fallback to standard search."
        except Exception as e:
            logger.error(f"OpenClaw connection failed: {e}")
            return f"Failed to connect to OpenClaw at {settings.OPENCLAW_URL}. Ensure the service is running locally on port 18789."
