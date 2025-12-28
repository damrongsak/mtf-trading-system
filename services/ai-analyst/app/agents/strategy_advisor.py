from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from app.core.config import settings
from app.services.rag import RAGService
import logging

logger = logging.getLogger(__name__)

class StrategyAdvisorAgent:
    def __init__(self, rag_service: RAGService):
        self.rag = rag_service
        if not settings.GOOGLE_API_KEY:
             raise ValueError("GOOGLE_API_KEY is not set")
             
        self.llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL_ID,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.2
        )

    async def run(self, input_text: str, user_id: str, context_code: str = None) -> str:
        """
        Executes the advisor agent.
        Dynamically binds tools to the current user_id.
        """
        
        @tool
        async def search_knowledge_base(query: str) -> str:
            """
            Search the strategy database for similar code examples and performance stats.
            Use this when the user asks for implementation help, "how to", or performance comparisons.
            """
            try:
                results = await self.rag.search_similar_strategies(query, user_id=user_id)
                if not results:
                    return "No relevant strategies found in knowledge base."
                
                formatted = []
                for res in results:
                    code_snippet = res['code'][:800] + "..." if len(res['code']) > 800 else res['code']
                    formatted.append(f"--- Similar Strategy (Score: {res['score']:.2f}) ---\nStats: {res['stats']}\nCode:\n{code_snippet}")
                return "\n".join(formatted)
            except Exception as e:
                return f"Error searching knowledge base: {str(e)}"

        tools = [search_knowledge_base]
        
        system_prompt = """You are an expert Algorithmic Trading Advisor for the MTF Trading System.
        Your goal is to assist the user in writing, debugging, and optimizing Python strategies using vectorbt.
        
        Capabilities:
        - Analyze user code for logical errors, look-ahead bias, or inefficiency.
        - Retrieve similar profitable strategies from the database to provide examples (use search_knowledge_base).
        - Suggest improvements based on Smart Money Concepts (SMC) and Multi-Timeframe (MTF) logic.
        
        Guidelines:
        - Always "Think Step-by-Step" before answering.
        - If the user provides code, analyze it first.
        - When suggesting code, ensure it is compatible with vectorbt (vbt) and pandas.
        - Be concise and focused on the trading logic.
        """

        graph = create_react_agent(self.llm, tools, state_modifier=system_prompt)
        
        # Prepare input
        full_prompt = f"User Request: {input_text}\n"
        if context_code:
            full_prompt += f"\n--- Current Strategy Code ---\n```python\n{context_code}\n```"

        inputs = {"messages": [("user", full_prompt)]}
        
        try:
            result = await graph.ainvoke(inputs)
            # Extract content logic same as MarketObserver
            content = result["messages"][-1].content
            
            # Simple content extraction (can rely on helper if shared, duplicates logic for now)
            if isinstance(content, list):
                 parts = []
                 for c in content:
                     if isinstance(c, dict) and "text" in c: parts.append(c["text"])
                     elif hasattr(c, "text"): parts.append(c.text)
                     else: parts.append(str(c))
                 return "\n".join(parts)
            return str(content)
            
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            return f"I encountered an error while processing your request: {str(e)}"
