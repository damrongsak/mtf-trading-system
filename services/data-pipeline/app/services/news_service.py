import aiohttp
import redis.asyncio as redis
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from app.core.config import settings

class NewsService:
    @staticmethod
    async def _get_redis():
        return redis.from_url(settings.REDIS_URL, decode_responses=True)

    @staticmethod
    async def check_quota(redis_client) -> bool:
        """Check if daily quota (100) is exceeded."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        key = f"news_api:daily_count:{today}"
        count = await redis_client.get(key)
        return int(count) < 100 if count else True

    @staticmethod
    async def increment_quota(redis_client):
        """Increment daily quota usage."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        key = f"news_api:daily_count:{today}"
        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, 86400) # 24h retention
        await pipe.execute()

    @staticmethod
    async def fetch_headlines(symbol: str) -> List[Dict]:
        """
        Fetches news headlines with Quota Management, Caching, and Source Filtering.
        """
        if not settings.NEWS_API_KEY:
            return [{"title": "NewsAPI Key Missing", "source": "System", "url": "", "publishedAt": datetime.utcnow().isoformat()}]

        redis_client = await NewsService._get_redis()
        cache_key = f"news:headlines:{symbol}"
        
        # 1. Check Cache (Read-Through to save quota)
        cached = await redis_client.get(cache_key)
        if cached:
            import json
            return json.loads(cached)

        # 2. Check Quota
        under_quota = await NewsService.check_quota(redis_client)
        
        if not under_quota:
            return [{"title": "Daily Quota Exceeded", "source": "System", "url": "", "publishedAt": datetime.utcnow().isoformat()}]

        # 3. Construct Query
        # Map symbol to query
        query_map = {
            "XAU/USD": "Gold price OR XAUUSD OR Fed rate OR US Inflation OR Geopolitics",
            "EUR/USD": "EURUSD OR ECB OR Eurozone economy OR Fed rate",
            "BTC/USD": "Bitcoin OR BTC price OR Crypto regulation",
            "USD/JPY": "USDJPY OR Bank of Japan OR Yen",
            "GBP/USD": "GBPUSD OR Bank of England OR UK economy",
        }
        q = query_map.get(symbol, symbol)
        
        # VIP Domains for Quality Filter
        vip_domains = "bloomberg.com,reuters.com,wsj.com,cnbc.com,ft.com,marketwatch.com,benzinga.com,investing.com,finance.yahoo.com"

        url = "https://newsapi.org/v2/everything"
        params = {
            "q": q,
            "apiKey": settings.NEWS_API_KEY,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 15,
            "domains": vip_domains
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        articles = data.get("articles", [])
                        
                        # Simplify
                        results = [
                            {
                                "title": a.get("title"),
                                "source": a.get("source", {}).get("name"),
                                "url": a.get("url"),
                                "publishedAt": a.get("publishedAt")
                            }
                            for a in articles
                        ]
                        
                        # 4. Success -> Increment Quota & Cache
                        await NewsService.increment_quota(redis_client)
                        await redis_client.setex(cache_key, 14400, json.dumps(results)) # 4 hour cache
                        
                        return results
                    elif resp.status == 429:
                         # Rate limit hit (external)
                         cached = await redis_client.get(cache_key)
                         if cached:
                             return json.loads(cached)
                         return [{"title": "Rate Limit Exceeded (External)", "source": "NewsAPI", "url": "", "publishedAt": datetime.utcnow().isoformat()}]
                    else:
                        return [{"title": f"Error: {resp.status}", "source": "NewsAPI", "url": "", "publishedAt": datetime.utcnow().isoformat()}]
            except Exception as e:
                return [{"title": f"Fetch Failed: {str(e)}", "source": "NewsAPI", "url": "", "publishedAt": datetime.utcnow().isoformat()}]
            finally:
                await redis_client.close()

    @staticmethod
    def save_sentiment(db, sentiment_data):
        """
        Save calculated sentiment score to the database.
        """
        from app.models.sentiment import SentimentScore
        
        db_obj = SentimentScore(
            symbol=sentiment_data.symbol,
            score=sentiment_data.score,
            reason=sentiment_data.reason,
            source_breakdown=sentiment_data.source_breakdown
        )
        db.add(db_obj)
        db.commit()
        return db_obj

    @staticmethod
    def get_sentiment_history(db, symbol: Optional[str] = None, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None):
        """
        Retrieve historical sentiment scores.
        """
        from app.models.sentiment import SentimentScore
        
        query = db.query(SentimentScore)
        
        if symbol:
            query = query.filter(SentimentScore.symbol == symbol)
        
        if start_date:
            query = query.filter(SentimentScore.created_at >= start_date)
            
        if end_date:
            query = query.filter(SentimentScore.created_at <= end_date)
            
        return query.order_by(SentimentScore.created_at.desc()).limit(1000).all()

    @staticmethod
    async def fetch_and_store_calendar(db) -> List[Dict]:
        """
        Fetches economic calendar from ForexFactory (nfs) and stores unique events.
        """
        url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()
            except Exception as e:
                print(f"Error fetching calendar: {e}")
                return []

        from app.models.economic_event import EconomicEvent
        import hashlib
        
        new_count = 0
        stored_events = []
        
        for item in data:
            # Generate deterministic ID
            # Use date (time), country, and title to uniquely identify
            raw_id = f"{item.get('date')}-{item.get('country')}-{item.get('title')}"
            ext_id = hashlib.md5(raw_id.encode()).hexdigest()
            
            # Check if exists
            exists = db.query(EconomicEvent).filter(EconomicEvent.external_id == ext_id).first()
            if exists:
                # Update actual values if released
                if item.get('actual') != exists.actual:
                     exists.actual = item.get('actual')
                     db.add(exists)
                continue
                
            # Parse datetime
            dt_str = item.get('date')
            try:
                dt = datetime.fromisoformat(dt_str)
            except Exception:
                continue

            event = EconomicEvent(
                external_id=ext_id,
                title=item.get('title'),
                country=item.get('country'),
                currency=item.get('country'), # FF often uses 'USD' as country for currency
                impact=item.get('impact'),
                datetime=dt,
                actual=item.get('actual', ''),
                forecast=item.get('forecast', ''),
                previous=item.get('previous', '')
            )
            db.add(event)
            stored_events.append(event)
            new_count += 1
            
        if new_count > 0:
            db.commit()
            
        return stored_events
