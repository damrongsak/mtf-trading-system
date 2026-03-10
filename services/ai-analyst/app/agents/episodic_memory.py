import logging
from typing import Dict, Any, List
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from app.core.config import settings
from app.tools.episodic_memory import FetchUnanalyzedTradesTool, SaveEpisodicMemoryTool
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

class EpisodicMemoryAgent:
    """
    Episodic Memory Agent (Trade Learning)
    Runs autonomously or on-demand to scan for unanalyzed trades,
    review the execution outcomes against the original trade narrative,
    extract actionable lessons, and save them as AI insights in JournalEntry.
    """
    def __init__(self):
        # 1. Tools
        self.tools = [FetchUnanalyzedTradesTool(), SaveEpisodicMemoryTool()]
        
        # 2. Role / System Prompt
        self.role = (
            "You are the Olympus AI Episodic Memory Subsystem. "
            "Your objective is to build a knowledge base of actionable trading lessons by analyzing past trades. "
            "When triggered, you must: "
            "1. Fetch recent closed trades that do not have an AI journal entry yet. "
            "2. Analyze EACH trade individually (Entry vs Exit, PnL, Strategy reasons). "
            "3. Extract a single, concrete, actionable rule or lesson learned from the outcome "
            "   (e.g., 'Do not long Gold when the 1H trend is bearish just because of a 5m FVG'). "
            "4. Determine a game_level ('A_GAME' for following strategy, 'C_GAME' for tilt/mistake). "
            "5. Save the episodic memory for that trade_id. "
            "Do not stop until you process all fetched trades up to the limit."
        )

        # 3. Initialize LLM
        if not settings.GOOGLE_API_KEY:
             raise ValueError("GOOGLE_API_KEY is not set")
             
        self.llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL_ID or "gemini-2.5-flash",
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.2 # low temp for objective analysis
        )
        
        # 4. Build Graph
        # Using create_react_agent as the orchestrator loop
        self.graph = create_react_agent(self.llm, self.tools, prompt=self.role)

    async def run(self, input_text: str = "Sync my episodic memory by processing 5 unanalyzed trades.") -> str:
        """
        Run the agent to process unanalyzed trades.
        """
        inputs = {"messages": [("user", input_text)]}
        
        try:
            result = await self.graph.ainvoke(inputs)
            
            # Extract content (Standard LangGraph extraction)
            content = result["messages"][-1].content
            return self._parse_content(content)
        except Exception as e:
            logger.error(f"Episodic Memory Agent run failed: {e}")
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
