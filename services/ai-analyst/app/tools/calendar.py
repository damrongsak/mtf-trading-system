from typing import List, Dict, Optional, Any
import httpx
import os
import json
import logging
from datetime import datetime, timedelta
import redis.asyncio as redis
from app.core.config import settings
from app.core.base_tool import BaseTool
from app.core.utils import parse_tool_input

logger = logging.getLogger(__name__)

class GetEconomicCalendarTool(BaseTool):
    name: str = "get_economic_calendar"
    description: str = "Fetches economic calendar events from the internal data service."

    async def _fetch_from_redis(self, currency: str = "USD") -> Optional[List[Dict]]:
        """Attempt to fetch events from Redis cache."""
        try:
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
            try:
                dt_str = e.get('datetime') or e.get('date') or ''
                if dt_str:
                    dt = datetime.fromisoformat(dt_str)
                    if dt > cutoff:
                        continue
            except:
                pass

            imp = e.get('impact', 'N/A')
            if impact_filter and imp.lower() != impact_filter.lower():
                continue

            title = e.get('title', 'Unknown')
            forecast = e.get('forecast', 'N/A')
            previous = e.get('previous', 'N/A')
            summary.append(f"[{dt_str}] {imp} {e.get('country')}: {title} (Fcst: {forecast}, Prev: {previous})")
            
            if len(summary) >= 30:
                break
                
        return "\n".join(summary) if summary else "No events match the criteria."

    async def run(self, input_data: Any, auth_token: str = None, request_id: str = None):
        input_dict = parse_tool_input(input_data)
        currency = input_dict.get("currency")
        impact = input_dict.get("impact")
        days = input_dict.get("days", 7)
        
        if not currency and isinstance(input_data, str) and len(input_data) <= 5:
             # Handle raw "USD" string case if parse_tool_input didn't quite capture it as currency
             currency = input_data.upper()
        
        events = None
        source = "API"
        
        check_currency = currency if currency else "USD"
        if check_currency.upper() == "USD":
            events = await self._fetch_from_redis("USD")
            if events:
                source = "Redis"
        
        if not events:
            events = await self._fetch_from_api(currency, impact, days)
            source = "API"
            
        if not events:
            return "Failed to retrieve calendar data from both Cache and API."
            
        result = self._format_events(events, impact, days)
        return result
