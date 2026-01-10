from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from app.core.config import settings
from app.tools.journal import GetJournalEntriesTool
from app.tools.signal import GetTechnicalSignalsTool
from app.tools.market import GetMarketContextTool
from app.tools.account import GetAccountStatusTool
from app.tools.calendar import GetEconomicCalendarTool

class DailyBriefingAgent:
    def __init__(self):
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is not set")

        self.llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL_ID,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.2 
        )
        
        # Base tools for initialization (used by graph builder, though we rebuild in run)
        self.tools = [
            GetJournalEntriesTool(),
            GetTechnicalSignalsTool(),
            GetMarketContextTool(),
            GetAccountStatusTool(),
            GetEconomicCalendarTool()
        ]
        
        self.graph = create_react_agent(self.llm, self.tools)

    async def run(self, input_text: str = "Generate a daily trading briefing.", auth_header: str = None) -> str:
        """
        Executes the agent with the given input.
        """
        # Initialize tools with auth header if provided
        tools = [
            GetJournalEntriesTool(auth_header=auth_header),
            GetTechnicalSignalsTool(auth_header=auth_header),
            GetMarketContextTool(),
            GetAccountStatusTool(auth_header=auth_header),
            GetEconomicCalendarTool(auth_header=auth_header)
        ]
        
        # Create fresh Agent Graph with context-aware tools
        graph = create_react_agent(self.llm, tools)

        # Enhanced Prompt for Professional Briefing
        prompt = (
            f"{input_text}\n"
            "You are a sophisticated Quant Fund Manager Assistant ('The Weaver').\n"
            "Your goal is to prepare the Head Trader for the day by synthesizing specific data points into a 'Pre-Flight Checklist'.\n\n"
            
            "**Execution Protocol:**\n"
            "1. **Macro Check**: Use `get_economic_calendar` to check for HIGH IMPACT news today for USD.\n"
            "2. **Risk Reality**: Use `get_account_status` to assess current exposure and drawdown.\n"
            "3. **Market Bias**: Use `get_technical_signals` for 'XAU/USD'.\n"
            "4. **Psychology**: Use `get_journal_entries` to review recent 5 trades for emotional patterns (Tilt, Fear, Confidence).\n\n"
            
            "**Output Format (Markdown)**:\n"
            "## 🌤️ Morning Call\n"
            "- **Macro Risk**: [List High Impact events or 'Clear skies']. Warning if NFP/FOMC/CPI today.\n"
            "- **Portfolio Health**: [Equity] | [Margin Used] | [Active Positions Count].\n\n"
            
            "## 🎯 Market Focus (XAU/USD)\n"
            "- **Bias**: [Signal Direction]\n"
            "- **Reason**: [Technicals]\n\n"
            
            "## 🧠 Psychological Weather\n"
            "- **Trend**: Analyze the last few trades. Are they executing well or tilting? (e.g. 'Chasing losses' or 'Good patience').\n"
            "- **Performance**: Net PnL of last 5 trades.\n\n"
            
            "## 🛡️ Strategic Orders\n"
            "- Concise, bulleted advice based on the above mix. (e.g. 'Volatile news at 14:00 - No entries 15m before', 'You are near max daily drawdown, reduce risk by 50%').\n\n"
            
            "**Tone**: Professional, concise, data-driven, and slightly protective of capital."
        )

        inputs = {"messages": [("user", prompt)]}
        result = await graph.ainvoke(inputs)
        
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
