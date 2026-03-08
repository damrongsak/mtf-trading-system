from typing import Any, Optional, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from app.core.globals import services
import logging

logger = logging.getLogger(__name__)

class SkillInput(BaseModel):
    name: str = Field(description="The name of the skill (snake_case)")
    code: str = Field(description="The Python code to save as a skill")

class SkillManagerTool(BaseTool):
    name: str = "save_persistent_skill"
    description: str = (
        "Save a successfully executed Python script or logic as a permanent skill. "
        "Use this when you've discovered a useful way to analyze data or interact with the system "
        "that you want to recall in future sessions."
    )
    args_schema: Type[BaseModel] = SkillInput

    def _run(self, name: str, code: str) -> str:
        import asyncio
        return asyncio.run(self._arun(name, code))

    async def _arun(self, name: str, code: str) -> str:
        memory_service = services.get("memory")
        if not memory_service:
            return "Error: Memory service not available."
            
        user_id = "agent_skill"
        
        try:
            await memory_service.save_persistent_skill(user_id, name, code)
            return f"Skill '{name}' saved successfully and indexed for future reasoning."
        except Exception as e:
            logger.error(f"SkillManagerTool error: {e}")
            return f"Error saving skill: {str(e)}"
