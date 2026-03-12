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
    persona: Optional[str] = Field("agent", description="Specialist persona: 'quant_engineer', 'software_engineer', 'market_critic', 'graph_specialist'")
    context_data: Optional[dict] = Field(None, description="Optional internal Olympus state/code to be critiqued by the persona")
    autonomous: bool = Field(False, description="If True, uses the browser tool for zero-cost scraping instead of paid Search APIs")

class OpenClawChatInput(BaseModel):
    message: str = Field(..., description="The message or instruction to send to the OpenClaw agent (e.g. 'Go to Google and find X')")
    session_key: Optional[str] = Field(None, description="Optional session key to maintain conversation context")
    target_agent: Optional[str] = Field("agent:main", description="The target OpenClaw agent (default: 'agent:main')")

class OpenClawResearcherTool(BaseTool):
    """
    Agentic Browser Research tool using OpenClaw.
    Supports specialist personas and recursive critique of internal Olympus data.
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
        persona = "agent"
        autonomous = False
        
        if hasattr(input_data, "dict"):
            input_data = input_data.dict()
            
        if isinstance(input_data, dict):
            task = input_data.get("task", "")
            url = input_data.get("url")
            persona = input_data.get("persona", "agent")
            autonomous = input_data.get("autonomous", False)
        elif isinstance(input_data, str):
            task = input_data

        if not task:
            return "Error: No research task provided."

        # ZERO-COST MODE: Use the Browser tool for scraping via the Chat API
        if autonomous:
            logger.info(f"OpenClaw: Running in AUTONOMOUS mode for zero-cost research: {task[:50]}...")
            chat_tool = OpenClawChatTool()
            
            # Special prompt to force the agent to use the browser and scrape
            autonomous_prompt = (
                f"You are a high-fidelity research assistant. Your task is to perform an autonomous search and scrape. "
                f"1. Search DuckDuckGo for: '{task}'\n"
                f"2. Use your browser tool to visit the top 3 relevant results.\n"
                f"3. Extract and summarize the key information related to the task.\n"
                f"4. Provide citations for the sources used.\n"
                f"Begin your research now."
            )
            
            return await chat_tool.run_tool({
                "message": autonomous_prompt,
                "session_key": f"autonomous-research-{hash(task) % 10000}"
            })

        # STANDARD MODE: Use paid High-Fidelity API (web_search)
        endpoint = f"{settings.OPENCLAW_URL}/tools/invoke"
        
        headers = {
            "Content-Type": "application/json"
        }
        if settings.OPENCLAW_GATEWAY_TOKEN:
            headers["Authorization"] = f"Bearer {settings.OPENCLAW_GATEWAY_TOKEN}"
        
        query = task
        if url:
            query = f"On site {url}: {task}"

        payload = {
            "tool": "web_search",
            "action": "json",
            "args": {
                "query": query
            },
            "sessionKey": "main",
            "dryRun": False
        }

        logger.info(f"OpenClaw: Executing 'web_search' (paid) for task: {task[:50]}...")
        
        try:
            timeout = aiohttp.ClientTimeout(total=180.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(endpoint, json=payload, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if not data.get("ok"):
                            error_msg = data.get("error", {}).get("message", "Unknown OpenClaw error")
                            logger.error(f"OpenClaw execution failed: {error_msg}")
                            return await self._run_fallback(task)

                        result_obj = data.get("result", {})
                        content_list = result_obj.get("content", [])
                        
                        if not content_list:
                            return await self._run_fallback(task)

                        raw_text = content_list[0].get("text", "")
                        
                        import json
                        try:
                            nested_data = json.loads(raw_text)
                            if "error" in nested_data:
                                logger.error(f"OpenClaw internal tool error: {nested_data.get('message')}")
                                return await self._run_fallback(task)

                            summary = nested_data.get("content", "No summary provided.")
                            citations = nested_data.get("citations", [])
                            citation_text = "\n\n**Sources:**\n" + "\n".join([f"- [{c.get('title', 'Link')}]({c.get('url')})" for c in citations]) if citations else ""
                            
                            summary = summary.replace("<<<EXTERNAL_UNTRUSTED_CONTENT", "--- RESEARCH START ---")
                            summary = summary.replace("END_EXTERNAL_UNTRUSTED_CONTENT", "--- RESEARCH END ---")
                            
                            logger.info(f"OpenClaw: Task completed successfully with {len(citations)} citations.")
                            return f"--- OpenClaw High-Fidelity Research Result ---\n\n{summary}{citation_text}"
                        except Exception:
                            return f"--- OpenClaw Research Result ---\n\n{raw_text}"
                    else:
                        error_text = await resp.text()
                        logger.error(f"OpenClaw API error: {resp.status} - {error_text}")
                        return await self._run_fallback(task)
        except Exception as e:
            logger.error(f"OpenClaw connection failed: {e}")
            return await self._run_fallback(task)

    async def _run_fallback(self, task: str) -> str:
        """Runs the standard search tool as a fallback."""
        logger.warning(f"OpenClaw failed. Falling back to standard search for: {task}")
        try:
            from app.tools.search import GoogleSearchTool
            search_tool = GoogleSearchTool()
            res = await search_tool.run_tool({"query": task})
            return f"--- FALLBACK Search Result (OpenClaw Service Issue) ---\n\n{res}"
        except Exception as e:
            logger.error(f"Fallback search failed: {e}")
            return "Error: High-fidelity research and fallback search failed."

class OpenClawChatTool(BaseTool):
    """
    Direct Agent Interaction tool using OpenClaw.
    Enables conversational task delegation and stateful agent communication.
    """
    name: str = "open_claw_chat"
    description: str = (
        "Enables direct natural language conversation with an OpenClaw AI Agent. "
        "Use this for complex browser automation tasks, step-by-step interactions, "
        "or when you need to maintain a stateful session with the AI Browser."
    )
    args_schema: Type[BaseModel] = OpenClawChatInput
    is_heavy: bool = True

    async def run_tool(self, input_data: Any, **kwargs) -> str:
        message = ""
        session_key = "olympus-default-session"
        target_agent = "agent:main"
        
        if hasattr(input_data, "dict"):
            input_data = input_data.dict()
            
        if isinstance(input_data, dict):
            message = input_data.get("message", "")
            session_key = input_data.get("session_key") or session_key
            target_agent = input_data.get("target_agent", "agent:main")
        elif isinstance(input_data, str):
            message = input_data

        if not message:
            return "Error: No message provided for the agent."

        # OpenClaw Responses API (OpenResponses compatible)
        endpoint = f"{settings.OPENCLAW_URL}/v1/responses"
        
        headers = {
            "Content-Type": "application/json"
        }
        if settings.OPENCLAW_GATEWAY_TOKEN:
            headers["Authorization"] = f"Bearer {settings.OPENCLAW_GATEWAY_TOKEN}"
        
        # OpenResponses Payload format
        payload = {
            "items": [
                {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "text", "text": message}]
                }
            ],
            "model": target_agent,
            "sessionKey": session_key,
            "stream": False
        }

        logger.info(f"OpenClaw: Sending direct message to {target_agent} (Session: {session_key})...")
        
        try:
            timeout = aiohttp.ClientTimeout(total=420.0) # Research tasks can be very long
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(endpoint, json=payload, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # Extract content from OpenResponses output items
                        output_items = data.get("output", [])
                        final_text = []
                        
                        for item in output_items:
                            if item.get("type") == "message" and item.get("role") == "assistant":
                                content = item.get("content", [])
                                for part in content:
                                    if part.get("type") == "text":
                                        final_text.append(part.get("text", ""))
                        
                        result = "\n".join(final_text) if final_text else "Message sent, but no text response received (might be browser actions only)."
                        logger.info(f"OpenClaw Chat: Response received from {target_agent}.")
                        return f"--- OpenClaw Agent Response ({target_agent}) ---\n\n{result}"
                    elif resp.status == 404:
                        logger.warning(f"OpenClaw /v1/responses not found. Falling back to alternative endpoint structure.")
                        # Possible fallback if the version expects 'input' instead of 'items'
                        fallback_payload = {
                            "input": message,
                            "model": target_agent,
                            "sessionKey": session_key,
                            "stream": False
                        }
                        async with session.post(endpoint, json=fallback_payload, headers=headers) as fresp:
                            if fresp.status == 200:
                                fdata = await fresp.json()
                                return f"--- OpenClaw Agent Response ({target_agent}) ---\n\n{fdata.get('output', 'Success')}"
                        
                        return "Error: Direct Agent Communication (/v1/responses) is not available or returned 404."
                    else:
                        error_text = await resp.text()
                        logger.error(f"OpenClaw Chat API error: {resp.status} - {error_text}")
                        return f"Error: OpenClaw Chat failed with status {resp.status}."
        except Exception as e:
            logger.error(f"OpenClaw Chat connection failed: {e}")
            return f"Error: Could not connect to OpenClaw Chat gateway: {e}"
