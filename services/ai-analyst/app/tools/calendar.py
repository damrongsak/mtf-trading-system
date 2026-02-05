from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type
from datetime import datetime, timedelta

class CalendarInput(BaseModel):
    currency: str = Field(default="USD", description="The currency to check for news (e.g., 'USD', 'EUR').")

from typing import Optional

import json
from redis import asyncio as aioredis # type: ignore
from app.core.config import settings

class GetEconomicCalendarTool(BaseTool):
    name: str = "get_economic_calendar"
    description: str = "Fetches upcoming high-impact economic events (like NFP, FOMC, CPI) for a given currency."
    args_schema: Type[BaseModel] = CalendarInput
    auth_header: Optional[str] = None

    def _run(self, currency: str = "USD"):
        raise NotImplementedError("Use _arun instead")

    async def _arun(self, currency: str = "USD"):
        redis_url = settings.REDIS_URL
        redis_key = f"calendar:{currency}"
        
        try:
             redis = await aioredis.from_url(redis_url, decode_responses=True)
             data = await redis.get(redis_key)
             await redis.close()
             
             if not data:
                 return f"No economic events found for {currency} in cache."
                 
             events = json.loads(data)
             
             # The source stores all events. We can filter here if needed, or return all.
             # The prompt asks for High Impact. The source JSON has "impact": "High", "Medium", "Low"
             
             high_impact = [e for e in events if e.get("impact") == "High"]
             
             if not high_impact:
                 return f"No HIGH IMPACT events found for {currency} this week in cache. (Total events: {len(events)})"
                 
             return f"HIGH IMPACT Economic Events for {currency}: {high_impact}"

        except Exception as e:
            return f"Failed to fetch calendar data: {e}"
