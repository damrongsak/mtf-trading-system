from typing import Any, Optional, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from app.core.globals import services
import logging

logger = logging.getLogger(__name__)

class SkillInput(BaseModel):
    name: str = Field(description="The name of the skill (snake_case)")
    content: str = Field(description="The full content of the SKILL.md file or Python code")

class SkillManagerTool(BaseTool):
    name: str = "save_persistent_skill"
    description: str = (
        "Save a successfully executed Python script or logic as a permanent skill. "
        "Use this when you've discovered a useful way to analyze data or interact with the system "
        "that you want to recall in future sessions."
    )
    args_schema: Type[BaseModel] = SkillInput

    def _run(self, name: str, content: str) -> str:
        import asyncio
        return asyncio.run(self._arun(name, content))

    async def _arun(self, name: str, content: str) -> str:
        skill_service = services.get("skill")
        memory_service = services.get("memory")
        
        results = []
        
        # 1. Save to Disk (Skill Discovery Path)
        if skill_service and ("---" in content or "name:" in content.lower()):
            try:
                path = await skill_service.save_skill(name, content)
                results.append(f"Disk: {path}")
            except Exception as e:
                logger.error(f"SkillManagerTool (Disk) error: {e}")
                results.append(f"Disk Error: {e}")

        # 2. Save to Memory (Semantic Search Path)
        if memory_service:
            try:
                await memory_service.save_persistent_skill("agent_skill", name, content)
                results.append("Memory: OK")
            except Exception as e:
                logger.error(f"SkillManagerTool (Memory) error: {e}")
                results.append(f"Memory Error: {e}")
        
        if not results:
            return "Error: No persistence services available."
            
        return " | ".join(results)
