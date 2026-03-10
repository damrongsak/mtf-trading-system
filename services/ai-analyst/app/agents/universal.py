from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import StructuredTool, BaseTool as LCTool
from app.schemas.agent import AgentConfig
from app.core.config import settings
from app.core.workflow import registry
import logging
import uuid

logger = logging.getLogger(__name__)

class UniversalAgent:
    """
    A dynamic agent that builds itself based on a configuration.
    Acts as a Lego wrapper for LangGraph.
    """
    def __init__(self, config: AgentConfig):
        self.config = config
        
        # 1. Resolve Tools
        from app.core.workflow import resolve_tools
        self.tools = resolve_tools(config.tools)

        # 2. Resolve Role
        self.role = config.role
        if config.role_prompt_id:
            fetched = self._fetch_role_sync(config.role_prompt_id)
            if fetched:
                self.role = fetched
            else:
                logger.warning(f"Using fallback role for {config.name}")

        # 3. Initialize LLM
        if not settings.GOOGLE_API_KEY:
             raise ValueError("GOOGLE_API_KEY is not set")
             
        self.llm = ChatGoogleGenerativeAI(
            model=config.model,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=config.temperature
        )
        
        # 4. Build Graph
        # Enhanced System Role for Planning (Protocol Approval v2.6)
        planning_prefix = (
            "You are an adaptive system agent. Before executing complex tasks using shell or python: "
            "1. FORMULATE a step-by-step plan. "
            "2. EXECUTE tools one by one. "
            "3. ADAPT your plan if tool outputs differ from expectations. "
            "\n\nBase Role:\n"
        )
        full_role = planning_prefix + self.role
        
        self.graph = create_react_agent(self.llm, self.tools, prompt=full_role)

    def _fetch_role_sync(self, prompt_id: str) -> str:
        import httpx
        try:
             url = f"{settings.API_GATEWAY_URL}/api/v1/prompts/{prompt_id}"
             with httpx.Client() as client:
                 resp = client.get(url, timeout=3.0)
                 if resp.status_code == 200:
                     return resp.json().get("template", "")
        except Exception as e:
            logger.error(f"Failed to fetch prompt sync: {e}")
        return ""

    async def run(self, input_text: str, user_id: str = "agent_default") -> str:
        """
        Run the agent with text input and adaptive context injection (v2.6).
        """
        # 1. Inject Memory Context (Lessons + Facts)
        from app.core.globals import services
        memory_service = services.get("memory")
        context = ""
        if memory_service:
            context = await memory_service.get_adaptive_context(user_id, input_text)
            
        # 2. Inject Available Skills (v2.8)
        skills_context = ""
        skill_service = services.get("skill")
        if skill_service:
            available_skills = skill_service.list_skills()
            if available_skills:
                skills_list = "\n".join([f"- {s['name']}: {s['description']}" for s in available_skills])
                skills_context = f"\n### AVAILABLE SPECIALIZED SKILLS ###\n{skills_list}\n"
                skills_context += "Use the 'execute_skill' tool if one of these matches the user's intent.\n"

        full_input = f"### CONTEXT ###\n{context}\n{skills_context}\n### REQUEST ###\n{input_text}" if context or skills_context else input_text
        inputs = {"messages": [("user", full_input)]}
        
        try:
            result = await self.graph.ainvoke(inputs)
            
            # Extract content (Standard LangGraph extraction)
            content = result["messages"][-1].content
            return self._parse_content(content)
        except Exception as e:
            logger.error(f"Universal Agent run failed: {e}")
            return f"Error: {str(e)}"

    def _parse_content(self, content) -> str:
        """Helper to extract string from diverse LLM output formats"""
        if isinstance(content, str):
            return content
            
        if isinstance(content, list):
             text_parts = []
             for c in content:
                if isinstance(c, dict) and "text" in c:
                    text_parts.append(c["text"])
                elif hasattr(c, "text"):
                    text_parts.append(c.text)
             return "\n".join(text_parts)
             
        return str(content)
