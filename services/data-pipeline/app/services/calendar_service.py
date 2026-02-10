import logging
import json
from typing import List, Dict, Optional
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.services.base import BaseService
from app.core.config import calendar_settings

logger = logging.getLogger(__name__)

class CalendarService(BaseService):
    """
    Professional grade Calendar Service with:
    - Distributed Locking (Redis)
    - Exponential Backoff Retries (Tenacity)
    - Pydantic Configuration
    """
    def __init__(self):
        super().__init__()
        self.settings = calendar_settings

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    async def _fetch_from_source(self) -> List[Dict]:
        """Fetch from URL with retry logic."""
        session = await self.get_session()
        async with session.get(self.settings.source_url, timeout=self.settings.fetch_timeout) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def fetch_and_cache_events(self) -> None:
        """Atomic fetch and cache operation using Redis Distributed Lock."""
        redis_conn = await self.get_redis()
        
        # lock_name = "lock:calendar_refresh"
        # Acquire lock to prevent cache stampede
        try:
            # check if lock is acquirable (non-blocking or short timeout)
            # Using redis-py's lock context manager
            async with redis_conn.lock("lock:calendar_refresh", timeout=30.0, blocking_timeout=5.0):
                logger.info("Acquired lock for Calendar sync.")
                
                data = await self._fetch_from_source()
                
                for currency in self.settings.currencies:
                    # Filter events
                    filtered_events = [
                        event for event in data 
                        if event.get("country") == currency
                    ]
                    
                    if not filtered_events:
                        logger.warning(f"No events found for {currency}.")
                        continue
                        
                    # Store in Redis
                    key = self.settings.redis_key.format(currency=currency)
                    await self._cache_set(key, filtered_events, self.settings.cache_ttl)
                    
                    logger.info(f"Cached {len(filtered_events)} events for {currency} to {key}.")
                    
        except Exception as e:
            # If lock acquisition fails (blocking_timeout), it means another instance is doing it.
            # We can log and skip. 
            # Or if _fetch_from_source fails after retries.
            logger.error(f"Calendar sync failed: {e}")

    async def sync_calendar_to_db(self, db) -> int:
        """Fetches and stores unique events in the database."""
        # Logic remains mostly same, but uses _fetch_from_source for reliability
        try:
            logger.info(f"Syncing economic calendar from {self.settings.source_url}...")
            
            data = await self._fetch_from_source()
                
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

    async def get_cached_events(self, currency:str = "USD") -> Optional[List[Dict]]:
        """Retrieve events from cache."""
        key = self.settings.redis_key.format(currency=currency)
        return await self._cache_get(key)

calendar_service = CalendarService()
