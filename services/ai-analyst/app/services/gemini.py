from google import genai
from app.core.config import settings

class GeminiClient:
    def __init__(self, client_factory=None):
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is not set")
        
        # Dependency Injection for testing
        self.client_factory = client_factory or genai.Client
        
        # Initialize the client with the API key
        self.client = self.client_factory(api_key=settings.GOOGLE_API_KEY)
        # Using configured model
        self.model_id = settings.GEMINI_MODEL_ID

    async def generate_market_outlook(self, context: dict, api_key: str = None, model_id: str = None) -> str:
        """
        Generates a market outlook based on technical indicators and SMC context.
        Supports multimodal input (images).
        Values in `context` can optionally override `api_key` and `model_id`.
        """
        
        # Determine strict client config
        active_key = api_key or settings.GOOGLE_API_KEY
        active_model = model_id or self.model_id
        
        # Instantiate transient client if key differs, else use default
        client = self.client
        if api_key and api_key != settings.GOOGLE_API_KEY:
            client = genai.Client(api_key=active_key)

        prompt = f"""
        You are an elite institutional trader analyzing the financial markets. 
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
        
        contents = [prompt]
        if "image_b64" in context and context["image_b64"]:
            print("INFO: Processing multimodal request with image")
            try:
                import base64
                from io import BytesIO
                from PIL import Image
                
                # Convert base64 to Image object usually required by some SDKs or just pass as blob
                # Google GenAI SDK supports dictionary for parts: {'mime_type': 'image/jpeg', 'data': bytes}
                
                img_data = base64.b64decode(context["image_b64"])
                image_part = {"mime_type": "image/jpeg", "data": img_data}
                contents.append(image_part)
            except Exception as e:
                return f"Error processing image: {str(e)}"

        try:
            # Use transient client for BYOK if key provided
            client = self.client
            if api_key:
                client = self.client_factory(api_key=api_key)
            
            response = await client.aio.models.generate_content(
                model=model_id or self.model_id,
                contents=contents
            )
            return response.text
        except Exception as e:
            print(f"Gemini Error: {e}")
            return f"Error generating outlook: {str(e)}"

    async def analyze_journal_entry(self, entry_content: str, similar_entries: list = None, user_id: str = None) -> str:
        """
        Analyzes a journal entry and compares it with similar past entries to identify patterns.
        If similar_entries is None, it attempts to fetch them via RAG (requires user_id).
        """
        if similar_entries is None:
            if not user_id:
                raise ValueError("user_id is required for RAG search")
                
            from app.services.rag import RAGService
            rag = RAGService(self)
            try:
                similar_entries = await rag.search_similar_entries(entry_content, user_id=user_id)
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

    async def generate_smc_analysis(self, smc_data: dict, api_key: str = None, model_id: str = None) -> str:
        """
        Specialized analysis for Smart Money Concepts
        """
        prompt = f"""
        Analyze this SMC Data and find the best trade setup.
        Data: {smc_data}
        
        Focus on:
        1. Liquidity Sweeps
        2. Order Blocks
        3. Fair Value Gaps
        """
        
        try:
            client = self.client
            if api_key:
                client = self.client_factory(api_key=api_key)

            response = await client.aio.models.generate_content(
                model=model_id or self.model_id,
                contents=prompt
            )
            return response.text
        except Exception as e:
            return f"Error generating narrative: {str(e)}"

    async def generate_smc_narrative(self, smc_data: dict, price_context: dict, api_key: str = None, model_id: str = None) -> str:
        """
        Generates a narrative based on SMC data (Order Blocks, FVGs, Structure).
        """
        active_key = api_key or settings.GOOGLE_API_KEY
        active_model = model_id or self.model_id
        
        client = self.client
        if api_key and api_key != settings.GOOGLE_API_KEY:
            client = genai.Client(api_key=active_key)

        prompt = f"""
        You are an expert Smart Money Concepts (SMC) trader.
        Analyze the current market structure and generate a professional trade narrative.
        
        Market Context:
        - Price: {price_context.get('price')}
        - Trend: {price_context.get('trend')}
        
        SMC Structure:
        - Structure: {smc_data.get('structure', {})}
        - Order Blocks: {smc_data.get('order_blocks', [])}
        - FVGs: {smc_data.get('fvgs', [])}
        - Liquidity Sweeps: {smc_data.get('liquidity_sweeps', [])}
        
        Explain the "Story of Price". specificially:
        1. liquidity objectives (where is the draw on liquidity?)
        2. structural bias (internal vs external structure)
        3. valid POIs (unmigitated OBs or FVGs)
        
        Keep it concise (under 200 words). Use bolding for key terms like **BOS**, **CHoCH**, **Order Block**.
        """
        
        try:
             response = await client.aio.models.generate_content(
                model=active_model,
                contents=prompt
            )
             return response.text
        except Exception as e:
            return f"Error generating narrative: {str(e)}"