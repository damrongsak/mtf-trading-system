import logging
import httpx
import json
from typing import Any, Optional, Type
from pydantic import BaseModel, Field
from app.core.config import settings
from app.core.base_tool import BaseTool

logger = logging.getLogger(__name__)

class SpecialistConsultationInput(BaseModel):
    agent_id: str = Field(..., description="The ID of the specialist agent to consult (e.g., 'market_observer', 'strategy_advisor').")
    query: str = Field(..., description="The specific question or task for the specialist.")
    context: Optional[str] = Field(None, description="Additional technical context or data to share with the specialist.")

class ConsultSpecialistTool(BaseTool):
    name: str = "consult_specialist"
    description: str = """
    Consults with a specialized AI agent to gain deeper insights or perform complex cross-domain tasks.
    Use this when your current tools or scope are insufficient for a highly technical request.
    """
    args_schema: Type[BaseModel] = SpecialistConsultationInput
    is_heavy: bool = True # Agent-to-agent consultation is a heavy operation

    async def run_tool(self, input_data: Any, **kwargs) -> str:
        agent_id = ""
        query = ""
        context = None
        
        if hasattr(input_data, "dict"):
            input_data = input_data.dict()
            
        if isinstance(input_data, dict):
            agent_id = input_data.get("agent_id", "")
            query = input_data.get("query", "")
            context = input_data.get("context")
            
        # 1. Robust Context Extraction
        # We try to extract auth_token and user_id from:
        # a) Direct kwargs (passed during manual call)
        # b) LangChain's 'config'/'configurable' metadata (passed during agent execution)
        
        auth_token = kwargs.get("auth_token")
        user_id = kwargs.get("user_id")
        
        # Check LangChain config structure
        if not auth_token or not user_id:
            config = kwargs.get("config", {})
            configurable = config.get("configurable", {})
            if not auth_token:
                auth_token = configurable.get("auth_token")
            if not user_id:
                user_id = configurable.get("user_id", "orchestrator")

        # Fallback for user_id
        if not user_id:
            user_id = "orchestrator"

        # 2. Route through API Gateway
        gateway_url = f"{settings.API_GATEWAY_URL}/api/v1/ai/agent/universal/run"
        
        headers = {
            "Content-Type": "application/json"
        }
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}" if not auth_token.startswith("Bearer ") else auth_token

        # Universal Agent Configuration for the specialist
        payload = {
            "config": {
                "name": agent_id,
                "role_prompt_id": agent_id,
                "model": settings.GEMINI_MODEL_ID,
                "temperature": 0.2
            },
            "input_text": f"### CONSULTATION REQUEST ###\nQuery: {query}\n\n### ADDITIONAL CONTEXT ###\n{context or 'No additional context provided.'}",
            "user_id": user_id
        }

        from app.core.globals import services
        redis = services.get("redis")
        
        # Log Start of Consultation
        if redis:
            audit_entry = {
                "type": "agent_handoff",
                "source_agent": "orchestrator",
                "target_agent": agent_id,
                "query": query,
                "status": "STARTED",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            try:
                await redis.xadd("orchestration.audit.stream", audit_entry, maxlen=1000, approximate=True)
            except Exception as e:
                logger.error(f"Failed to log handoff start to Redis: {e}")

        async with httpx.AsyncClient() as client:
            try:
                logger.info(f"Consulting specialist '{agent_id}' via Gateway (User: {user_id})...")
                response = await client.post(
                    gateway_url,
                    json=payload,
                    headers=headers,
                    timeout=120.0
                )
                
                status_code = response.status_code
                if status_code == 200:
                    data = response.json()
                    inner_data = data.get("data", {})
                    result = inner_data.get("response") or inner_data.get("report") or str(inner_data)
                    
                    if redis:
                        await redis.xadd("orchestration.audit.stream", {
                            "type": "agent_handoff",
                            "source_agent": "orchestrator",
                            "target_agent": agent_id,
                            "status": "COMPLETED",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }, maxlen=1000, approximate=True)
                        
                    return f"### SPECIALIST RESPONSE ({agent_id}) ###\n\n{result}"
                else:
                    logger.error(f"Specialist consultation failed: {status_code} - {response.text}")
                    if redis:
                        await redis.xadd("orchestration.audit.stream", {
                            "type": "agent_handoff",
                            "source_agent": "orchestrator",
                            "target_agent": agent_id,
                            "status": "FAILED",
                            "error": response.text[:200],
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }, maxlen=1000, approximate=True)
                    return f"Error: Specialist '{agent_id}' is currently unavailable (Gateway returned {status_code})."
                    
            except Exception as e:
                logger.error(f"ConsultSpecialistTool failed: {str(e)}")
                if redis:
                    await redis.xadd("orchestration.audit.stream", {
                        "type": "agent_handoff",
                        "source_agent": "orchestrator",
                        "target_agent": agent_id,
                        "status": "ERROR",
                        "error": str(e),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }, maxlen=1000, approximate=True)
                return f"Error: Failed to connect to specialist agent '{agent_id}': {str(e)}"
