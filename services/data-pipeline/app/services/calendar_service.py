import logging
from typing import List, Dict, Optional
from datetime import datetime
from app.services.base import BaseService

logger = logging.getLogger(__name__)

class CalendarService(BaseService):
    def __init__(self):
        super().__init__()
        self.url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        self.redis_key = "calendar:USD"
        self.cache_ttl = 6 * 3600  # 6 hours

    async def fetch_and_cache_events(self) -> None:
        """Fetches economic calendar events and caches them in Redis."""
        try:
            logger.info(f"Fetching economic calendar from {self.url}...")
            session = await self.get_session()
            
            async with session.get(self.url) as resp:
                if resp.status != 200:
                    logger.error(f"Failed to fetch calendar: {resp.status}")
                    return
                
                data = await resp.json()
                
                # Filter for USD only to save space
                usd_events = [
                    event for event in data 
                    if event.get("country") == "USD"
                ]
                
                if not usd_events:
                    logger.warning("No USD events found in calendar data.")
                    return

                # Store in Redis using BaseService helper
                await self._cache_set(self.redis_key, usd_events, self.cache_ttl)
                
                logger.info(f"Successfully cached {len(usd_events)} USD economic events to Redis.")
                
        except Exception as e:
            logger.error(f"Error in CalendarService: {e}")
            # Ensure resources are closed if this was a one-off run, 
            # though usually the service persists.
            # In a long running app, we might keep connections open.

    async def get_cached_events(self) -> Optional[List[Dict]]:
        """Retrieve events from cache."""
        return await self._cache_get(self.redis_key)

calendar_service = CalendarService()
