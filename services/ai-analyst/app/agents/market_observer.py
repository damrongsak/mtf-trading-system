from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langchain_core.prompts import ChatPromptTemplate
from app.core.config import settings
from app.tools.market import GetMarketContextTool
from app.tools.account import GetAccountStatusTool

class MarketObserverAgent:
    def __init__(self):
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is not set")

        self.llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL_ID,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.1
        )
        
        self.tools = [
            GetMarketContextTool(),
            GetAccountStatusTool()
        ]
        
        # LangGraph React Agent
        self.graph = create_react_agent(self.llm, self.tools)

    async def run(self, input_text: str = "Generate a market situation report for XAU/USD.") -> str:
        """
        Executes the agent with the given input.
        """
        # LangGraph invoke returns a dict with 'messages'
        inputs = {"messages": [("user", input_text)]}
        result = await self.graph.ainvoke(inputs)
        # Extract last message content
        content = result["messages"][-1].content
        if isinstance(content, list):
            return "\n".join([str(c) for c in content])
        return str(content)
