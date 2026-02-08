from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Optional
import httpx
import os
import json
from datetime import datetime, timedelta

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

    async def _arun(self, currency: str = None, impact: str = None, days: int = 7):
        base_url = os.getenv("DATA_PIPELINE_URL", "http://data-pipeline:8000")
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
                    return f"Error fetching calendar: {resp.status_code} - {resp.text}"
                
                events = resp.json()
                if not events:
                    return "No economic events found for the given criteria."
                
                # Format for LLM - limit to top 20 to save tokens
                # Sort by impact if possible? API sorts by datetime.
                # Let's ensure we return a concise summary
                summary = []
                for e in events[:30]:
                    dt_str = e.get('datetime', '')
                    title = e.get('title', 'Unknown')
                    imp = e.get('impact', 'N/A')
                    forecast = e.get('forecast', 'N/A')
                    previous = e.get('previous', 'N/A')
                    summary.append(f"[{dt_str}] {imp} {e.get('country')}: {title} (Fcst: {forecast}, Prev: {previous})")
                
                return "\n".join(summary)
                
            except Exception as e:
                return f"Failed to fetch calendar data: {str(e)}"
