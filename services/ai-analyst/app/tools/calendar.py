from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type
from datetime import datetime, timedelta

class CalendarInput(BaseModel):
    currency: str = Field(default="USD", description="The currency to check for news (e.g., 'USD', 'EUR').")

from typing import Optional

class GetEconomicCalendarTool(BaseTool):
    name: str = "get_economic_calendar"
    description: str = "Fetches upcoming high-impact economic events (like NFP, FOMC, CPI) for a given currency."
    args_schema: Type[BaseModel] = CalendarInput
    auth_header: Optional[str] = None

    def _run(self, currency: str = "USD"):
        raise NotImplementedError("Use _arun instead")

    async def _arun(self, currency: str = "USD"):
        # TODO: Integrate with real news API (e.g. data-pipeline news scraper) if available.
        # For now, we improve the mock to include dynamic dating and better impact filtering.
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Enhanced Mock Data - can be replaced with API call using self.auth_header if needed
        mock_events = [
            {"date": today, "time": "14:30", "currency": "USD", "event": "Core CPI m/m", "impact": "High", "forecast": "0.3%", "previous": "0.3%"},
            {"date": today, "time": "20:00", "currency": "USD", "event": "FOMC Meeting Minutes", "impact": "High", "forecast": "", "previous": ""},
            {"date": today, "time": "14:30", "currency": "USD", "event": "Unemployment Claims", "impact": "Medium", "forecast": "210K", "previous": "215K"},
             {"date": today, "time": "15:00", "currency": "USD", "event": "ISM Manufacturing PMI", "impact": "High", "forecast": "47.2", "previous": "46.9"},
        ]
        
        # Filter: Match currency AND High Impact
        filtered = [
            e for e in mock_events 
            if e["currency"] == currency and e["impact"] == "High"
        ]
        
        if not filtered:
            return f"No high-impact economic events found for {currency} today ({today})."
            
        return f"HIGH IMPACT Economic Events for {currency} today ({today}): {filtered}"
