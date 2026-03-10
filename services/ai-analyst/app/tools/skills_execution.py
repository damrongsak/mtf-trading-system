import logging
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, Field
from app.core.globals import services
from langgraph.prebuilt import create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings
from app.core.base_tool import BaseTool

logger = logging.getLogger(__name__)

class SkillExecutionInput(BaseModel):
    skill_name: str = Field(description="The name of the skill to execute")
    task: str = Field(description="The specific task or prompt for the skill to handle")

class ExecuteSkillTool(BaseTool):
    name: str = "execute_skill"
    description: str = (
        "Execute a specialized skill. Use this when the user's request matches "
        "one of your available skills. You must provide the skill name and the "
        "specific task for that skill."
    )
    args_schema: Type[BaseModel] = SkillExecutionInput
    is_heavy: bool = True

    async def run_tool(self, input_data: Any, **kwargs) -> str:
        skill_name = ""
        task = ""
        
        if hasattr(input_data, "dict"):
            input_data = input_data.dict()
            
        if isinstance(input_data, dict):
            skill_name = input_data.get("skill_name", "")
            task = input_data.get("task", "")
            
        skill_service = services.get("skill")
        logger.info(f"Executing skill '{skill_name}' for task: {task[:50]}...")
        if not skill_service:
            return "Error: Skill service not available."

        skill = skill_service.get_skill(skill_name)
        if not skill:
            return f"Error: Skill '{skill_name}' not found."

        logger.info(f"Executing skill '{skill_name}' for task: {task}")

        # 1. Prepare Sub-Agent
        try:
            from app.core.workflow import registry, resolve_tools
            # Resolve all tools in the registry for the sub-agent
            all_tool_names = list(registry._tools.keys())
            all_tools = resolve_tools(all_tool_names)
            
            # Extract auth_token if present in kwargs to pass down to sub-agent tools
            auth_token = kwargs.get("auth_token") or kwargs.get("config", {}).get("configurable", {}).get("auth_token")

            llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash", # Use flash for sub-tasks for speed
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=0
            )

            # The full instructions from SKILL.md
            instructions = skill["instructions"]
            references = skill.get("references", "")
            
            # 2. Reference Injection (v2.9)
            full_prompt = instructions
            if references:
                full_prompt += f"\n\n### Additional Context (References):\n{references}"
                logger.info(f"Injected {len(references)} chars of reference context into skill '{skill_name}'")
            
            # Create a transient agent
            sub_agent = create_react_agent(llm, all_tools, prompt=full_prompt)
            
            # 3. Execute
            # Inject auth_token into configurable context for sub-agent
            config = {"configurable": {"auth_token": auth_token}} if auth_token else {}
            inputs = {"messages": [("user", task)]}
            result = await sub_agent.ainvoke(inputs, config=config)
            
            # 4. Format result
            content = result["messages"][-1].content
            return f"--- Skill '{skill_name}' Output ---\n{content}\n--- End Skill Output ---"
            
        except Exception as e:
            logger.error(f"Error executing skill '{skill_name}': {e}")
            return f"Error executing skill: {str(e)}"
