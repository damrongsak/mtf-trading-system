from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Optional, List, Dict
import httpx
import os
import json
import logging
from datetime import datetime, timedelta
import redis.asyncio as redis
from app.core.config import settings

logger = logging.getLogger(__name__)

class CalendarInput(BaseModel):
    currency: Optional[str] = Field(default=None, description="Currency/Country code (e.g. USD, EUR)")
    impact: Optional[str] = Field(default=None, description="Impact filter (High, Medium, Low)")
    days: int = Field(default=7, description="Days to look ahead")

class GetEconomicCalendarTool(BaseTool):
    name: str = "get_economic_calendar"
    description: str = "Fetches economic calendar events from the internal data service."
    args_schema: Type[BaseModel] = CalendarInput

    def _run(self, currency: str = None, impact: str = None, days: int = 7):
        raise NotImplementedError("Use _arun instead")

    async def _fetch_from_redis(self, currency: str = "USD") -> Optional[List[Dict]]:
        """Attempt to fetch events from Redis cache."""
        try:
            # We assume the key is 'calendar:USD' based on data-pipeline implementation
            # If currency is NOT USD, we might not have it in cache yet.
            if currency and currency.upper() != "USD":
                return None
                
            r = redis.from_url(settings.REDIS_URL, decode_responses=True)
            async with r:
                data = await r.get("calendar:USD")
                if data:
                    return json.loads(data)
        except Exception as e:
            logger.warning(f"Redis fetch failed: {e}")
        return None

    async def _fetch_from_api(self, currency: str, impact: str, days: int) -> Optional[List[Dict]]:
        """Fallback to HTTP API."""
        # Using environment variable or settings if available, tool uses existing logic
        base_url = os.getenv("DATA_PIPELINE_URL", settings.DATA_PIPELINE_URL)
        url = f"{base_url}/api/v1/news/calendar"
        
        now = datetime.utcnow()
        end = now + timedelta(days=days)
        
        params = {
            "date_from": now.isoformat(),
            "date_to": end.isoformat()
        }
        if currency:
            params["country"] = currency
        if impact:
            params["impact"] = impact
            
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, params=params, timeout=10.0)
                if resp.status_code != 200:
                    logger.error(f"API fetch failed: {resp.status_code} - {resp.text}")
                    return None
                return resp.json()
            except Exception as e:
                logger.error(f"API connection failed: {e}")
                return None

    def _format_events(self, events: List[Dict], impact_filter: str = None, days: int = 7) -> str:
        """Filter and format events for LLM."""
        if not events:
            return "No economic events found."
            
        summary = []
        now = datetime.utcnow()
        cutoff = now + timedelta(days=days)
        
        for e in events:
            # 1. Date Filter (if source didn't filter, e.g. Redis dump)
            try:
                # Cache (Raw) uses 'date', API/DB might use 'datetime'
                dt_str = e.get('datetime') or e.get('date') or ''
                if dt_str:
                    # simplistic check, ISO format
                    # Source format example: 2026-02-09T13:30:00-05:00
                    dt = datetime.fromisoformat(dt_str)
                    if dt > cutoff:
                        continue
            except:
                pass # ignore parsing errors

            # 2. Impact Filter
            imp = e.get('impact', 'N/A')
            if impact_filter and imp.lower() != impact_filter.lower():
                continue

            title = e.get('title', 'Unknown')
            forecast = e.get('forecast', 'N/A')
            previous = e.get('previous', 'N/A')
            summary.append(f"[{dt_str}] {imp} {e.get('country')}: {title} (Fcst: {forecast}, Prev: {previous})")
            
            if len(summary) >= 30: # Hard limit
                break
                
        return "\n".join(summary) if summary else "No events match the criteria."

    async def _arun(self, currency: str = None, impact: str = None, days: int = 7):
        events = None
        source = "API"
        
        # 1. Try Redis (Fast Path)
        # Default to USD if checking cache, but only if currency is None or USD
        check_currency = currency if currency else "USD"
        if check_currency.upper() == "USD":
            events = await self._fetch_from_redis("USD")
            if events:
                source = "Redis"
        
        # 2. Fallback to API
        if not events:
            events = await self._fetch_from_api(currency, impact, days)
            source = "API"
            
        if not events:
            return "Failed to retrieve calendar data from both Cache and API."
            
        # 3. Format and Return
        result = self._format_events(events, impact, days)
        # logger.info(f"Served calendar from {source}") # Optional debug
        return result
