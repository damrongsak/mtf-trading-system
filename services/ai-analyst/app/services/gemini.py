from google import genai
from app.core.config import settings

class GeminiClient:
    def __init__(self):
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is not set")
        
        # Initialize the client with the API key
        self.client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        # Using gemini-1.5-pro
        self.model_id = 'gemini-1.5-pro'

    async def generate_market_outlook(self, context: dict) -> str:
        """
        Generates a market outlook based on technical indicators and SMC context.
        """
        prompt = f"""
        You are an elite institutional trader analyzing XAU/USD. 
        Analyze the following market context and provide a concise, narrative-based outlook.
        
        Context:
        - Trend (4H): {context.get('trend_4h', 'Unknown')}
        - Price: {context.get('current_price', 'Unknown')}
        - Key Levels: {context.get('key_levels', [])}
        - Recent Signals: {context.get('recent_signals', [])}
        
        Format your response in Markdown with these sections:
        ## 📊 Market Context
        ## 🗝️ Key Levels to Watch
        ## 🧠 Strategy Bias (Bullish/Bearish/Neutral)
        """
        
        try:
            response = await self.client.aio.models.generate_content(
                model=self.model_id,
                contents=prompt
            )
            return response.text
        except Exception as e:
            return f"Error generating insight: {str(e)}"

    async def analyze_journal_entry(self, entry_content: str, similar_entries: list = None) -> str:
        """
        Analyzes a journal entry and compares it with similar past entries to identify patterns.
        If similar_entries is None, it attempts to fetch them via RAG.
        """
        if similar_entries is None:
            from app.services.rag import RAGService
            rag = RAGService(self)
            try:
                similar_entries = await rag.search_similar_entries(entry_content)
            except Exception as e:
                # Fallback if RAG fails (e.g., connection issue)
                similar_entries = []
                print(f"RAG fetch failed: {e}")

        context_str = "\n".join([f"- {e}" for e in similar_entries])
        prompt = f"""
        Analyze this trading journal entry for psychological patterns and mistakes.
        Compare it with these similar past entries:
        {context_str}
        
        Current Entry:
        "{entry_content}"
        
        Provide a bulleted list of:
        - Detected Emotion
        - Recurring Mistake (if any)
        - Actionable Advice
        """
        
        try:
            response = await self.client.aio.models.generate_content(
                model=self.model_id,
                contents=prompt
            )
            return response.text
        except Exception as e:
            return f"Error analyzing journal: {str(e)}"