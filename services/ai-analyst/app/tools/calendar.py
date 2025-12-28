from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type
from datetime import datetime, timedelta

class CalendarInput(BaseModel):
    currency: str = Field(default="USD", description="The currency to check for news (e.g., 'USD', 'EUR').")

class GetEconomicCalendarTool(BaseTool):
    name: str = "get_economic_calendar"
    description: str = "Fetches upcoming high-impact economic events (like NFP, FOMC, CPI) for a given currency."
    args_schema: Type[BaseModel] = CalendarInput

    def _run(self, currency: str = "USD"):
        raise NotImplementedError("Use _arun instead")

    async def _arun(self, currency: str = "USD"):
        # Mock Data Simulation
        # In a real app, this would call an API like ForexFactory or Finnhub or AlphaVantage
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Static mock events for demo purposes
        mock_events = [
            {"date": today, "time": "14:30", "currency": "USD", "event": "Core CPI m/m", "impact": "High", "forecast": "0.3%", "previous": "0.3%"},
            {"date": today, "time": "20:00", "currency": "USD", "event": "FOMC Meeting Minutes", "impact": "High", "forecast": "", "previous": ""},
            {"date": today, "time": "14:30", "currency": "USD", "event": "Unemployment Claims", "impact": "Medium", "forecast": "210K", "previous": "215K"},
        ]
        
        # Filter by currency (simple partial match)
        filtered = [e for e in mock_events if e["currency"] == currency]
        
        if not filtered:
            return f"No high-impact events found for {currency} today."
            
        return f"Upcoming Economic Events for {currency}: {filtered}"
