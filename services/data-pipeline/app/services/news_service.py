import logging
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from app.core.config import settings
from app.services.base import BaseService
from sqlalchemy.orm import Session as DBSession

logger = logging.getLogger(__name__)

class NewsApiService(BaseService):
    def __init__(self):
        super().__init__()
        self.base_url = "https://newsapi.org/v2/everything"
        self.vip_domains = "bloomberg.com,reuters.com,wsj.com,cnbc.com,ft.com,marketwatch.com,benzinga.com,investing.com,finance.yahoo.com"
        
    async def check_quota(self) -> bool:
        """Check if daily quota (100) is exceeded."""
        redis = await self.get_redis()
        today = datetime.utcnow().strftime("%Y-%m-%d")
        key = f"news_api:daily_count:{today}"
        count = await redis.get(key)
        return int(count) < 100 if count else True

    async def increment_quota(self):
        """Increment daily quota usage."""
        redis = await self.get_redis()
        today = datetime.utcnow().strftime("%Y-%m-%d")
        key = f"news_api:daily_count:{today}"
        async with redis.pipeline() as pipe:
            await pipe.incr(key)
            await pipe.expire(key, 86400) # 24h retention
            await pipe.execute()

    def _get_query_for_symbol(self, symbol: str) -> str:
        """Map symbol to news query."""
        query_map = {
            "XAU/USD": "Gold price OR XAUUSD OR Fed rate OR US Inflation OR Geopolitics",
            "XAUUSD": "Gold price OR XAUUSD OR Fed rate OR US Inflation OR Geopolitics",
            "EUR/USD": "EURUSD OR ECB OR Eurozone economy OR Fed rate",
            "EURUSD": "EURUSD OR ECB OR Eurozone economy OR Fed rate",
            "BTC/USD": "Bitcoin OR BTC price OR Crypto regulation",
            "BTCUSD": "Bitcoin OR BTC price OR Crypto regulation",
            "USD/JPY": "USDJPY OR Bank of Japan OR Yen",
            "USDJPY": "USDJPY OR Bank of Japan OR Yen",
            "GBP/USD": "GBPUSD OR Bank of England OR UK economy",
            "GBPUSD": "GBPUSD OR Bank of England OR UK economy",
        }
        return query_map.get(symbol, symbol)

    async def fetch_headlines(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Fetches news headlines with Quota Management, Caching, and Source Filtering.
        """
        if not settings.NEWS_API_KEY:
            return [self._create_sys_msg("NewsAPI Key Missing")]

        cache_key = f"news:headlines:{symbol}"
        
        # 1. Check Cache
        cached = await self._cache_get(cache_key)
        if cached:
            return cached

        # 2. Check Quota
        if not await self.check_quota():
            return [self._create_sys_msg("Daily Quota Exceeded")]

        # 3. Fetch from API
        try:
            results = await self._fetch_from_api(symbol)
            if results:
                 await self.increment_quota()
                 await self._cache_set(cache_key, results, ttl=14400) # 4 hours
            return results
        except Exception as e:
            logger.error(f"News fetch failed: {e}")
            return [self._create_sys_msg(f"Fetch Failed: {str(e)}")]

    async def _fetch_from_api(self, symbol: str) -> List[Dict[str, Any]]:
        """Internal method to call NewsAPI."""
        q = self._get_query_for_symbol(symbol)
        params = {
            "q": q,
            "apiKey": settings.NEWS_API_KEY,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 15,
            "domains": self.vip_domains
        }

        session = await self.get_session()
        async with session.get(self.base_url, params=params) as resp:
            if resp.status == 200:
                data = await resp.json()
                articles = data.get("articles", [])
                return [
                    {
                        "title": a.get("title"),
                        "source": a.get("source", {}).get("name"),
                        "url": a.get("url"),
                        "publishedAt": a.get("publishedAt")
                    }
                    for a in articles
                ]
            elif resp.status == 429:
                return [self._create_sys_msg("Rate Limit Exceeded (External)", "NewsAPI")]
            else:
                return [self._create_sys_msg(f"Error: {resp.status}", "NewsAPI")]

    async def sync_news_to_db(self, db: DBSession, symbol: str) -> int:
        """Fetch headlines and sync new ones to the database."""
        headlines = await self.fetch_headlines(symbol)
        if not headlines or (len(headlines) == 1 and headlines[0].get("source") == "System"):
            return 0

        from app.models.news import NewsArticle
        import hashlib
        
        new_count = 0
        for item in headlines:
            url = item.get("url")
            if not url:
                continue
                
            # Deduplication hash: URL
            ext_id = hashlib.md5(url.encode()).hexdigest()
            
            exists = db.query(NewsArticle).filter(NewsArticle.external_id == ext_id).first()
            if exists:
                continue
                
            pub_at_str = item.get("publishedAt")
            try:
                # Handle ISO format from NewsAPI
                pub_at = datetime.fromisoformat(pub_at_str.replace('Z', '+00:00'))
            except Exception:
                pub_at = datetime.utcnow()

            article = NewsArticle(
                external_id=ext_id,
                title=item.get("title"),
                source=item.get("source"),
                url=url,
                published_at=pub_at,
                symbol=symbol
            )
            db.add(article)
            new_count += 1
            
        if new_count > 0:
            db.commit()
            logger.info(f"Successfully synced {new_count} new news articles for {symbol} to database.")
            
        return new_count

    def _create_sys_msg(self, title: str, source: str = "System") -> Dict[str, str]:
        return {
            "title": title,
            "source": source,
            "url": "",
            "publishedAt": datetime.utcnow().isoformat()
        }

    @staticmethod
    def save_sentiment(db: DBSession, sentiment_data: Any):
        """Save calculated sentiment score to the database."""
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
    def get_sentiment_history(db: DBSession, symbol: Optional[str] = None, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None):
        """Retrieve historical sentiment scores."""
        from app.models.sentiment import SentimentScore
        
        query = db.query(SentimentScore)
        if symbol:
            query = query.filter(SentimentScore.symbol == symbol)
        if start_date:
            query = query.filter(SentimentScore.created_at >= start_date)
        if end_date:
            query = query.filter(SentimentScore.created_at <= end_date)
            
        return query.order_by(SentimentScore.created_at.desc()).limit(1000).all()

    async def fetch_and_store_calendar(self, db: DBSession) -> List[Any]:
        """
        Fetches economic calendar from ForexFactory (nfs) and stores unique events.
        Legacy method kept on NewsService causing confusion with CalendarService. 
         Ideally should be moved to CalendarService, but kept here for compatibility if needed.
        """
        # Delegating to the new CalendarService would be better, but avoiding circular Deps.
        # Implemented using current BaseService structure.
        url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        
        try:
             session = await self.get_session()
             async with session.get(url) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
        except Exception as e:
            logger.error(f"Error fetching calendar: {e}")
            return []

        from app.models.economic_event import EconomicEvent
        import hashlib
        
        new_count = 0
        stored_events = []
        
        for item in data:
            raw_id = f"{item.get('date')}-{item.get('country')}-{item.get('title')}"
            ext_id = hashlib.md5(raw_id.encode()).hexdigest()
            
            exists = db.query(EconomicEvent).filter(EconomicEvent.external_id == ext_id).first()
            if exists:
                if item.get('actual') != exists.actual:
                     exists.actual = item.get('actual')
                     db.add(exists)
                continue
                
            dt_str = item.get('date')
            try:
                dt = datetime.fromisoformat(dt_str)
            except Exception:
                continue

            event = EconomicEvent(
                external_id=ext_id,
                title=item.get('title'),
                country=item.get('country'),
                currency=item.get('country'),
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
