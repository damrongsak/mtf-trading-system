from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from app.schemas.agent import AgentConfig
from app.core.config import settings
from app.core.workflow import registry
import logging

logger = logging.getLogger(__name__)

class UniversalAgent:
    """
    A dynamic agent that builds itself based on a configuration.
    Acts as a Lego wrapper for LangGraph.
    """
    def __init__(self, config: AgentConfig):
        self.config = config
        
        # 1. Resolve Tools
        self.tools = []
        for tool_name in config.tools:
            tool = registry.get(tool_name)
            if tool:
                self.tools.append(tool)
            else:
                logger.warning(f"Tool '{tool_name}' not found in registry. Skipping.")
        
        # 2. Initialize LLM
        # Handle BYOK if needed (TODO: Pass runtime config for keys, here using system defaults for simplicity/prototype)
        if not settings.GOOGLE_API_KEY:
             raise ValueError("GOOGLE_API_KEY is not set")
             
        self.llm = ChatGoogleGenerativeAI(
            model=config.model,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=config.temperature
        )
        
        # 3. Build Graph
        # We use create_react_agent which gives us a compiled graph
        self.graph = create_react_agent(self.llm, self.tools, messages_modifier=config.role)

    async def run(self, input_text: str) -> str:
        """
        Run the agent with text input.
        """
        inputs = {"messages": [("user", input_text)]}
        
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
