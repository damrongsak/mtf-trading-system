from typing import Any, Optional, Type, List, Dict
import httpx
import logging
import json
import asyncio
from datetime import datetime, timedelta, timezone
from app.core.config import settings
from app.core.base_tool import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class EconomicImpactCorrelationInput(BaseModel):
    symbol: str = Field(default="XAUUSD", description="Symbol to analyze (e.g., XAUUSD)")
    currency: str = Field(default="USD", description="Currency for economic events (e.g., USD, EUR)")
    impact: str = Field(default="High", description="Min impact level to analyze ('High', 'Medium')")
    lookback_days: int = Field(default=30, description="How many days of history to analyze")
    window_minutes: int = Field(default=60, description="Time window around the event to measure volatility (minutes)")

class EconomicImpactCorrelationTool(BaseTool):
    name: str = "EconomicImpactCorrelation"
    description: str = "Queries historical economic calendar events and correlates them with price volatility to suggest no-trade zones."
    args_schema: Type[BaseModel] = EconomicImpactCorrelationInput
    is_heavy: bool = True # This tool performs multiple network calls

    async def run_tool(self, input_data: Any, auth_token: str = None, **kwargs) -> str:
        # 1. Normalize Input
        if hasattr(input_data, "dict"):
            params = input_data.dict()
        elif isinstance(input_data, dict):
            params = input_data
        else:
            params = {}

        symbol = params.get("symbol", "XAUUSD")
        currency = params.get("currency", "USD")
        impact = params.get("impact", "High")
        lookback_days = params.get("lookback_days", 30)
        window_minutes = params.get("window_minutes", 60)

        logger.info(f"Executing EconomicImpactCorrelation for {symbol}, currency {currency}, last {lookback_days} days")

        try:
            async with httpx.AsyncClient() as client:
                # 2. Fetch Historical Calendar Events
                now = datetime.now(timezone.utc)
                date_from = (now - timedelta(days=lookback_days)).isoformat()
                date_to = now.isoformat()

                calendar_url = f"{settings.DATA_PIPELINE_URL}/api/v1/news/calendar"
                calendar_resp = await client.get(
                    calendar_url, 
                    params={"country": currency, "impact": impact, "date_from": date_from, "date_to": date_to},
                    timeout=10.0
                )
                
                if calendar_resp.status_code != 200:
                    return f"Error: Failed to fetch calendar (Status {calendar_resp.status_code})"
                
                events = calendar_resp.json()
                if not events:
                    return f"No {impact} impact events found for {currency} in the last {lookback_days} days."

                # 3. Correlate with Volatility
                event_groups = {} # Group identical events (e.g. multiple NFPs)

                for event in events:
                    title = event.get("title", "Unknown Event")
                    dt_str = event.get("datetime")
                    if not dt_str: continue

                    try:
                        event_time = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                    except: continue

                    # Define window
                    w_start = event_time - timedelta(minutes=window_minutes // 2)
                    w_end = event_time + timedelta(minutes=window_minutes // 2)

                    # Fetch candles for this window from data-pipeline
                    candles_url = f"{settings.DATA_PIPELINE_URL}/api/v1/candles"
                    candles_resp = await client.get(
                        candles_url,
                        params={
                            "symbol": symbol,
                            "timeframe": "5m", 
                            "page_size": 100
                        },
                        timeout=5.0
                    )

                    if candles_resp.status_code == 200:
                        data = candles_resp.json()
                        candles = data.get("items", [])
                        
                        # Filter candles within window
                        window_candles = []
                        for c in candles:
                            ts = c["timestamp"]
                            c_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                            if w_start <= c_time <= w_end:
                                window_candles.append(c)

                        if window_candles:
                            highs = [float(c["high"]) for c in window_candles]
                            lows = [float(c["low"]) for c in window_candles]
                            volatility = max(highs) - min(lows)
                            
                            if title not in event_groups:
                                event_groups[title] = []
                            event_groups[title].append(volatility)

                if not event_groups:
                    return f"Found events, but could not fetch price data for the windows."

                # 4. Generate Summary
                summary_lines = [f"### Volatility Correlation Analysis ({symbol}) ###"]
                summary_lines.append(f"Analyzing {impact} impact {currency} events (Window: ±{window_minutes//2}m)\n")
                
                # Sort by impact
                sorted_events = sorted(
                    [(t, sum(v)/len(v), len(v)) for t, v in event_groups.items()],
                    key=lambda x: x[1],
                    reverse=True
                )

                for title, avg_vol, count in sorted_events:
                    suggest_ignore = "⚠️ RECOMMENDED NO-TRADE" if avg_vol > 10.0 else "✅ SAFE"
                    summary_lines.append(f"- **{title}**: Avg Volatility ${avg_vol:.2f} (n={count}) - {suggest_ignore}")

                summary_lines.append(f"\n*Generated at {now.strftime('%Y-%m-%d %H:%M')}. Threshold set at $10.00 move.*")
                return "\n".join(summary_lines)

        except Exception as e:
            logger.error(f"EconomicImpactCorrelation error: {e}")
            return f"Error: {str(e)}"
