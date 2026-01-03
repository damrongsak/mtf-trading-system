import aiohttp
import json
import redis.asyncio as redis
from app.core.config import settings
from langchain_google_genai import ChatGoogleGenerativeAI
from datetime import datetime, timedelta

class SentimentService:
    def __init__(self):
        self.news_api_key = settings.NEWS_API_KEY
        self.llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL_ID,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.1
        )
        self.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        self.cache_ttl = 3600 # 1 hour

    async def get_sentiment(self, symbol: str = "XAU/USD") -> dict:
        """
        Fetches news and calculates sentiment score for the given symbol.
        Uses Redis caching (TTL 1h).
        Returns: { "score": float, "reason": str }
        """
        if not self.news_api_key:
            return {"score": 0.0, "reason": "NewsAPI key not configured."}

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
        
        # 4. Save to Cache
        try:
            await self.redis.setex(cache_key, self.cache_ttl, json.dumps(result))
        except Exception as e:
            print(f"Redis cache write failed: {e}")
            
        return result

    async def _fetch_news(self, symbol: str) -> list[str]:
        # Map symbol to query
        query_map = {
            "XAU/USD": "Gold price OR XAUUSD OR Fed rate OR US Inflation OR Geopolitics",
            "EUR/USD": "EURUSD OR ECB OR Eurozone economy OR Fed rate",
            "BTC/USD": "Bitcoin OR BTC price OR Crypto regulation",
        }
        q = query_map.get(symbol, symbol)
        
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": q,
            "apiKey": self.news_api_key,
            "language": "en",
            "sortBy": "relevancy",
            "from": (datetime.utcnow() - timedelta(days=1)).isoformat(), # Last 24h
            "pageSize": 15
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        articles = data.get("articles", [])
                        return [f"- {a['title']} ({a['source']['name']})" for a in articles]
                    else:
                        print(f"NewsAPI Error: {resp.status} {await resp.text()}")
                        return []
            except Exception as e:
                print(f"Failed to fetch news: {e}")
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
