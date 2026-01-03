from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langchain_core.prompts import ChatPromptTemplate
from app.core.config import settings
from app.tools.journal import GetJournalEntriesTool
from app.tools.signal import GetTechnicalSignalsTool
from app.tools.market import GetMarketContextTool

class DailyBriefingAgent:
    def __init__(self):
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is not set")

        self.llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL_ID,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.2 # Slightly higher than 0.1 for more narrative
        )
        
        self.tools = [
            GetJournalEntriesTool(),
            GetTechnicalSignalsTool(),
            GetMarketContextTool()
        ]
        
        # LangGraph React Agent
        self.graph = create_react_agent(self.llm, self.tools)

    async def run(self, input_text: str = "Generate a daily trading briefing.") -> str:
        """
        Executes the agent with the given input.
        """
        # Prompt Engineering for Briefing
        prompt = (
            f"{input_text}\n"
            "You are a professional Quant Fund Manager Assistant.\n"
            "Your task is to generate a 'Daily Briefing' for the Head Trader.\n"
            "Steps:\n"
            "1. Fetch the last 10 journal entries using 'get_journal_entries'.\n"
            "2. Fetch active signals for 'XAU/USD' using 'get_technical_signals'.\n"
            "3. Synthesize a report in Markdown with these sections:\n"
            "   - ** Performance Snapshot**: Summary of recent wins/losses and Net PnL.\n"
            "   - ** Key Trades**: Briefly mention 1-2 significant trades and the 'Emotion' recorded.\n"
            "   - ** Market Outlook**: Based on active signals, what is the bias for XAU/USD?\n"
            "   - ** Strategic Note**: A short advice based on the performance (e.g., 'Good discipline today' or 'Watch out for overtrading').\n"
            "Keep it professional, concise, and motivating."
        )

        inputs = {"messages": [("user", prompt)]}
        result = await self.graph.ainvoke(inputs)
        
        # Extract last message content (Reuse logic from MarketObserverAgent)
        content = result["messages"][-1].content
        if isinstance(content, list):
            text_parts = []
            for c in content:
                if isinstance(c, dict) and "text" in c:
                    text_parts.append(c["text"])
                elif hasattr(c, "text"):
                    text_parts.append(c.text)
                else:
                    text_parts.append(str(c))
            return "\n".join(text_parts)

        if isinstance(content, dict):
            if "text" in content:
                 return content["text"]
        
        return str(content)
