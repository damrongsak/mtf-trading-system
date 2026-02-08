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

    async def sync_calendar_to_db(self, db) -> int:
        """Fetches and stores unique events in the database."""
        try:
            logger.info(f"Syncing economic calendar from {self.url}...")
            session = await self.get_session()
            
            async with session.get(self.url) as resp:
                if resp.status != 200:
                    logger.error(f"Failed to fetch calendar: {resp.status}")
                    return 0
                
                data = await resp.json()
                
            from app.models.economic_event import EconomicEvent
            import hashlib
            
            new_count = 0
            for item in data:
                # Deduplication hash: date-country-title
                raw_id = f"{item.get('date')}-{item.get('country')}-{item.get('title')}"
                ext_id = hashlib.md5(raw_id.encode()).hexdigest()
                
                exists = db.query(EconomicEvent).filter(EconomicEvent.external_id == ext_id).first()
                if exists:
                    # Update actual value if it changed
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
                new_count += 1
                
            if new_count > 0 or db.deleted or db.dirty:
                db.commit()
                logger.info(f"Successfully synced {new_count} new economic events to database.")
            
            return new_count
                
        except Exception as e:
            logger.error(f"Error in sync_calendar_to_db: {e}")
            db.rollback()
            return 0

    async def get_cached_events(self) -> Optional[List[Dict]]:
        """Retrieve events from cache."""
        return await self._cache_get(self.redis_key)

calendar_service = CalendarService()
