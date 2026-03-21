import logging
import json
import uuid
from typing import Any, Optional, Type, Dict
from pydantic import BaseModel, Field
from app.core.base_tool import BaseTool
from app.services.episodic_memory import EpisodicMemoryService
from app.database import SessionLocal

logger = logging.getLogger("ai-analyst")

class EpisodicMemoryInput(BaseModel):
    action: str = Field(..., description="Action to perform: 'RECALL' (search) or 'LEARN' (save).")
    content: str = Field(..., description="The lesson, observation, or query text.")
    symbol: Optional[str] = Field(None, description="Related symbol (e.g. XAUUSD).")
    intent: Optional[str] = Field(None, description="Intent category (e.g. STRATEGY_EXPLAIN).")
    fund_id: Optional[str] = Field(None, description="Optional Fund UUID for shared context.")

class EpisodicMemoryTool(BaseTool):
    """
    Institutional Episodic Memory Tool.
    Allows the AI to 'remember' lessons and 'recall' them semantically.
    Isolated by user_id for RBAC compliance.
    """
    name: str = "episodic_memory"
    description: str = (
        "Persistent AI Memory. Use 'RECALL' to find past lessons/observations "
        "and 'LEARN' to save new institutional insights. Strictly RBAC compliant."
    )
    args_schema: Type[BaseModel] = EpisodicMemoryInput

    async def run_tool(self, input_data: Any, auth_token: str = None, request_id: str = None) -> str:
        # Parse Input
        if isinstance(input_data, str):
            try:
                data = json.loads(input_data)
            except:
                return "Error: Invalid JSON input for episodic_memory tool."
        else:
            data = input_data

        action = data.get("action", "").upper()
        content = data.get("content")
        symbol = data.get("symbol")
        intent = data.get("intent")
        fund_id_str = data.get("fund_id")

        if not action or not content:
            return "Error: 'action' and 'content' are required fields."

        # Note: In a real multi-user scenario, user_id would be resolved from 
        # the auth_token or session. For this Agentic execution, we assume 
        # the agent state provides it, or we use a context var.
        # Implementation: Resolve user_id from context or fallback to a test ID.
        from app.utils.tracing import get_user_id # Check if this exists
        user_id_str = get_user_id()
        
        if not user_id_str:
            # Fallback for E2E tests if not in request context
            # In LangGraph, we should ideally pass this.
            return "Error: Could not resolve User ID for episodic memory isolation."

        try:
            user_id = uuid.UUID(user_id_str)
            fund_id = uuid.UUID(fund_id_str) if fund_id_str else None
        except Exception as e:
            return f"Error: Invalid UUID format: {e}"

        db = SessionLocal()
        try:
            service = EpisodicMemoryService(db)
            
            if action == "LEARN":
                memory = await service.add_memory(
                    user_id=user_id,
                    content=content,
                    symbol=symbol,
                    intent=intent,
                    fund_id=fund_id
                )
                return f"✅ Lesson learned and saved to episodic memory (ID: {memory.id})."
            
            elif action == "RECALL":
                memories = await service.retrieve_relevant_memories(
                    user_id=user_id,
                    query=content,
                    symbol=symbol,
                    fund_id=fund_id,
                    limit=3
                )
                
                if not memories:
                    return "No matching past lessons found in episodic memory."
                
                results = ["### 🧠 Recalled Lessons:"]
                for m in memories:
                    results.append(f"- [{m['created_at']}] (Symbol: {m['symbol'] or 'Global'})")
                    results.append(f"  Insight: {m['content']}")
                
                return "\n".join(results)
            
            else:
                return f"Error: Unknown action '{action}'. Use 'RECALL' or 'LEARN'."
                
        except Exception as e:
            logger.error(f"EpisodicMemoryTool failed: {e}")
            return f"Error: Memory operation failed: {str(e)}"
        finally:
            db.close()
