import logging
import aiohttp
import json
from datetime import datetime
from app.core.config import settings
from redis import asyncio as aioredis # type: ignore

logger = logging.getLogger(__name__)

class CalendarService:
    def __init__(self):
        self.url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        self.redis_key = "calendar:USD"
        self.cache_ttl = 6 * 3600  # 6 hours

    async def fetch_and_cache_events(self):
        """Fetches economic calendar events and caches them in Redis."""
        try:
            logger.info(f"Fetching economic calendar from {self.url}...")
            async with aiohttp.ClientSession() as session:
                async with session.get(self.url) as resp:
                    if resp.status != 200:
                        logger.error(f"Failed to fetch calendar: {resp.status}")
                        return
                    
                    data = await resp.json()
                    
                    # Filter for USD only to save space, or store all if needed.
                    # The user prompt specifically cared about USD macros (NFP, FOMC).
                    usd_events = [
                        event for event in data 
                        if event.get("country") == "USD"
                    ]
                    
                    if not usd_events:
                        logger.warning("No USD events found in calendar data.")
                        return

                    # Connect to Redis
                    redis = await aioredis.from_url(settings.REDIS_URL, decode_responses=True)
                    
                    # Store as a JSON string
                    await redis.set(self.redis_key, json.dumps(usd_events), ex=self.cache_ttl)
                    
                    logger.info(f"Successfully cached {len(usd_events)} USD economic events to Redis.")
                    await redis.close()
                    
        except Exception as e:
            logger.error(f"Error in CalendarService: {e}")

calendar_service = CalendarService()
