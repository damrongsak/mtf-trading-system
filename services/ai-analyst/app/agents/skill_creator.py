import logging
import uuid

from typing import List, Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import StructuredTool, BaseTool as LCTool
from langgraph.prebuilt import create_react_agent
from app.core.config import settings
from app.core.workflow import registry
from app.core.globals import services

logger = logging.getLogger(__name__)

class SkillCreatorAgent:
    """
    A specialized agent that follows the 'skill-creator' workflow 
    to generate, test, and refine new SKILL.md files.
    """
    def __init__(self, gemini_client=None):
        self.gemini = gemini_client or services.get("gemini")
        
        # Tools specifically useful for creating skills
        # 1. Resolve Tools
        from app.core.workflow import resolve_tools
        self.tools = resolve_tools([
            "google_search", 
            "web_reader", 
            "shell_command", 
            "python_interpreter", 
            "save_persistent_skill"
        ])

        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash", 
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.2
        )

        template_path = "services/ai-analyst/skills/templates/default_skill.md"
        
        self.role = f"""
You are the **Skill Creator Agent** for MTF Olympus. Your mission is to build world-class 'skills' 
that empower the AI with specialized logic and domain expertise.

### 🎯 Core standards (agentskills.io):
1. **Name & Description**: YAML frontmatter is MANDATORY. The description must be 'pushy' (clearly stating when to trigger).
2. **Imperative Instructions**: Use direct commands (e.g., "Analyze the trend", "Extract the key figures"). 
   - 🚫 AVOID: "You should...", "The user might want...", "It is recommended to...".
3. **Examples**: Include exactly 2-3 realistic Examples in the SKILL.md body.
4. **Separation of Concerns**: Long data or static reference material should be suggested for the `references/` directory (inform the user or system).
5. **Phase 2 Skeleton**: The `save_persistent_skill` tool now automatically creates `scripts/`, `references/`, and `assets/` folders. 

### 🔄 Mandatory Workflow:
1. **Research**: Use 'google_search' to find the best practices for the requested skill.
2. **Draft & Lint**: Draft the SKILL.md. BEFORE saving, perform a 'Self-Review' against the 5 standards above.
3. **Save**: Use 'save_persistent_skill' ONLY after the draft passes your own linting process.

**Template Reference:**
{template_path}
"""
        self.graph = create_react_agent(self.llm, self.tools, prompt=self.role)

    async def run(self, user_intent: str, user_id: str = "skill_creator") -> str:
        """
        Execute the skill creation workflow based on user intent.
        """
        logger.info(f"Skill Creator started with intent: {user_intent}")
        
        # Inject existing skills context to avoid duplicates
        existing_skills = ""
        skill_service = services.get("skill")
        if skill_service:
            meta = skill_service.list_skills()
            existing_skills = "\nExisting Skills:\n" + "\n".join([f"- {s['name']}: {s['description']}" for s in meta])

        full_input = f"User Intent: {user_intent}\n{existing_skills}"
        inputs = {"messages": [("user", full_input)]}
        
        try:
            result = await self.graph.ainvoke(inputs)
            return result["messages"][-1].content
        except Exception as e:
            logger.error(f"Skill Creator failed: {e}")
            return f"Error creating skill: {str(e)}"
