import aiohttp
import json
import redis.asyncio as redis
from app.core.config import settings
from langchain_google_genai import ChatGoogleGenerativeAI
from datetime import datetime, timedelta

class SentimentService:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL_ID,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.1
        )
        self.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        self.cache_ttl = 3600 # 1 hour
        self._session: Optional[aiohttp.ClientSession] = None

    async def get_session(self) -> aiohttp.ClientSession:
        """Lazy initialization of persistent aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """Close the persistent session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def get_sentiment(self, symbol: str = "XAU/USD") -> dict:
        # ... (rest of the method remains same, but uses self.get_session())
        if not settings.GOOGLE_API_KEY:
            return {"score": 0.0, "reason": "GOOGLE_API_KEY not configured."}

        # 1. Check Cache
        cache_key = f"sentiment:{symbol}"
        try:
            cached = await self.redis.get(cache_key)
            if cached:
                 return json.loads(cached)
        except Exception as e:
            print(f"Redis cache read failed: {e}")

        # 2. Fetch News (if cache miss)
        headlines = await self._fetch_news(symbol)
        if not headlines:
            return {"score": 0.0, "reason": "No recent news found."}

        # 3. Analyze with Gemini
        result = await self._analyze_headlines(symbol, headlines)
        
        # 4. Persist to DB
        await self._save_sentiment_to_db(symbol, result)

        # 5. Save to Cache
        try:
            await self.redis.setex(cache_key, self.cache_ttl, json.dumps(result))
        except Exception as e:
            print(f"Redis cache write failed: {e}")
            
        return result

    async def _save_sentiment_to_db(self, symbol: str, result: dict):
        """Persist sentiment score to Data Pipeline."""
        url = f"{settings.DATA_PIPELINE_URL}/api/v1/news/sentiment"
        payload = {
            "symbol": symbol,
            "score": result.get("score"),
            "reason": result.get("reason"),
            "source_breakdown": {} # Placeholder
        }
        
        try:
            session = await self.get_session()
            async with session.post(url, json=payload) as resp:
                 if resp.status not in [200, 201]:
                     print(f"Failed to save sentiment to DB: {resp.status}")
        except Exception as e:
            print(f"Error saving sentiment to DB: {e}")

    async def _fetch_news(self, symbol: str) -> list[str]:
        """
        Fetches news headlines from Data Pipeline service.
        """
        url = f"{settings.DATA_PIPELINE_URL}/api/v1/news/headlines"
        params = {"symbol": symbol}

        try:
            session = await self.get_session()
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    headlines = await resp.json()
                    # Headlines are list of dicts: {title, source, url, publishedAt}
                    return [f"- {h['title']} ({h['source']})" for h in headlines]
                else:
                    print(f"Data Pipeline News Error: {resp.status} {await resp.text()}")
                    return []
        except Exception as e:
            print(f"Failed to fetch news from pipeline: {e}")
            return []

    async def _analyze_headlines(self, symbol: str, headlines: list[str]) -> dict:
        headlines_text = "\n".join(headlines)
        prompt = (
            f"Analyze the following news headlines for {symbol} sentiment.\n"
            f"Headlines:\n{headlines_text}\n\n"
            "Task:\n"
            "1. Determine the overall market sentiment for this asset.\n"
            "2. Assign a score from -1.0 (Very Bearish) to 1.0 (Very Bullish).\n"
            "3. Provide a concise 1-sentence reason.\n\n"
            "Output Format (JSON only):\n"
            '{"score": 0.0, "reason": "..."}'
        )
        
        try:
            response = await self.llm.ainvoke(prompt)
            content = response.content.strip()
            
            # Simple parsing (robustness improvement: use structured output or PydanticOutputParser later)
            import json
            # Handle potential markdown fence
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].strip()
            
            data = json.loads(content)
            return {
                "score": float(data.get("score", 0.0)),
                "reason": data.get("reason", "Analysis failed")
            }
        except Exception as e:
            print(f"LLM Analysis Error: {e}")
            return {"score": 0.0, "reason": "Error parsing sentiment analysis."}
