import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Type, Any
import httpx
import redis.asyncio as redis
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from app.core.config import settings

logger = logging.getLogger(__name__)

class CalendarInput(BaseModel):
    currency: Optional[str] = Field(default="USD", description="Currency filter (e.g. USD, EUR)")
    impact: Optional[str] = Field(None, description="Impact filter: 'High', 'Medium', 'Low'")
    days: int = Field(default=7, description="Number of days ahead to check")

class GetEconomicCalendarTool(BaseTool):
    name: str = "get_economic_calendar"
    description: str = "Fetches economic calendar events from the internal data service."
    args_schema: Type[BaseModel] = CalendarInput

    def _run(self, currency: Optional[str] = "USD", impact: Optional[str] = None, days: int = 7) -> str:
        import asyncio
        return asyncio.run(self._arun(currency, impact, days))

    async def _arun(self, currency: Optional[str] = "USD", impact: Optional[str] = None, days: int = 7, **kwargs) -> str:
        events = None
        if currency and currency.upper() == "USD":
            try:
                r = redis.from_url(settings.REDIS_URL, decode_responses=True)
                data = await r.get("calendar:USD")
                if data: events = json.loads(data)
                await r.close()
            except: pass

        if not events:
            url = f"{settings.DATA_PIPELINE_URL}/api/v1/news/calendar"
            now = datetime.utcnow()
            params = {"date_from": now.isoformat(), "date_to": (now + timedelta(days=days)).isoformat()}
            if currency: params["country"] = currency
            if impact: params["impact"] = impact
            
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(url, params=params, timeout=5.0)
                    if resp.status_code == 200: events = resp.json()
            except: pass
            
        if not events:
            return "No economic events found or service unavailable."
            
        summary = []
        now = datetime.utcnow()
        cutoff = now + timedelta(days=days)
        
        for e in events:
            dt_str = e.get('datetime') or e.get('date') or ''
            try:
                dt = datetime.fromisoformat(dt_str)
                if dt > cutoff: continue
            except: pass

            imp = e.get('impact', 'N/A')
            if impact and imp.lower() != impact.lower(): continue

            summary.append(f"[{dt_str}] {imp} {e.get('country')}: {e.get('title')} (Fcst: {e.get('forecast', 'N/A')})")
            if len(summary) >= 20: break
                
        return "\n".join(summary) if summary else "No events match filter."
