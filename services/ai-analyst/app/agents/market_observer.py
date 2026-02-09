from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langchain_core.prompts import ChatPromptTemplate
from app.core.config import settings
from app.tools.market import GetMarketContextTool
from app.tools.account import GetAccountStatusTool
from app.tools.signal import GetTechnicalSignalsTool
from app.tools.calendar import GetEconomicCalendarTool
from app.tools.search import GoogleSearchTool
from app.tools.market_state import MarketStateTool

class MarketObserverAgent:
    def __init__(self):
        if not settings.gemini.api_key:
            raise ValueError("GOOGLE_API_KEY is not set")

        self.llm = ChatGoogleGenerativeAI(
            model=settings.gemini.model_id,
            google_api_key=settings.gemini.api_key,
            temperature=0.1
        )
        
        self.tools = [
            MarketStateTool(),  # NEW: Institutional-grade market state features
            GetMarketContextTool(),
            GetTechnicalSignalsTool(),
            GetAccountStatusTool(),
            GetEconomicCalendarTool(),
            GoogleSearchTool()
        ]
        
        # LangGraph React Agent
        self.graph = create_react_agent(self.llm, self.tools)

    async def run(self, input_text: str = "Generate a market situation report for XAU/USD.", auth_header: str = None) -> str:
        """
        Executes the agent with the given input.
        """
        # Initialize tools with auth header if provided
        # Note: GetAccountStatusTool might also need auth if api-gateway protects it or if it calls another secure service
        # GetTechnicalSignalsTool definitely needs it.
        
        runtime_tools = [
            MarketStateTool(),  # NEW: Institutional-grade market state features
            GetMarketContextTool(),
            GetTechnicalSignalsTool(auth_header=auth_header),
            GetAccountStatusTool(), # Assuming internal execution service doesn't require user token, OR it needs one. Let's assume user token is better.
            GetEconomicCalendarTool(),
            GoogleSearchTool()
        ]

        # Re-create graph with authenticated tools
        graph = create_react_agent(self.llm, runtime_tools)

        # LangGraph invoke returns a dict with 'messages'
        inputs = {"messages": [("user", input_text)]}
        result = await graph.ainvoke(inputs)
        # Extract last message content
        content = result["messages"][-1].content
        if isinstance(content, list):
            # Handle list of content blocks (e.g. text + tool_use)
            text_parts = []
            for c in content:
                if isinstance(c, dict) and "text" in c:
                    text_parts.append(c["text"])
                elif hasattr(c, "text"): # Object with text attr
                    text_parts.append(c.text)
                else:
                    text_parts.append(str(c))
            return "\n".join(text_parts)

        if isinstance(content, dict):
            # Handle direct dictionary content
            if "text" in content:
                 return content["text"]
        
        # Check if content is a stringified dict (common with some LLM outputs or tool results)
        import ast
        try:
            if isinstance(content, str) and content.strip().startswith("{") and "text" in content:
                 # Attempt safely parse
                 parsed = ast.literal_eval(content)
                 if isinstance(parsed, dict) and "text" in parsed:
                     return parsed["text"]
        except:
            pass
            
        return str(content)
