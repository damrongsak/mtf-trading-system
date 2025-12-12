from datetime import datetime
from typing import List, Optional
import pandas as pd
from app.adapters.oanda import OandaAdapter
from app.database import SessionLocal
from app.models.data_source import DataSource
from sqlalchemy import func

class OandaHistoryAdapter(OandaAdapter):
    """
    Adapter for fetching historical data from OANDA.
    Extends base OandaAdapter but focuses on history/candles endpoints.
    """
    
    def __init__(self, data_source_name: str = "oanda"):
        # Initialize parent manually since we look up by name here, not ID
        self.db = SessionLocal()
        try:
            ds = self.db.query(DataSource).filter(func.lower(DataSource.name) == data_source_name.lower()).first()
            if not ds:
                raise ValueError(f"DataSource '{data_source_name}' not found")
            
            # Pass ID to parent init which does the setup
            super().__init__(data_source_id=str(ds.id))
        finally:
            self.db.close()

    def fetch_candles_range(self, symbol: str, timeframe: str, 
                          from_time: Optional[datetime] = None, 
                          to_time: Optional[datetime] = None,
                          count: int = 500) -> pd.DataFrame:
        """
        Fetch candles from Oanda for a specific range or count.
        Returns a DataFrame compatible with strategy/indicator logic.
        """
        kwargs = {
            "instrument": symbol,
            "granularity": timeframe,
            "price": "M"  # Midpoint candles
        }
        
        if from_time:
            kwargs["fromTime"] = from_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        if to_time:
            kwargs["toTime"] = to_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        if not from_time and not to_time:
            kwargs["count"] = count

        response = self.ctx.instrument.candles(**kwargs)

        if response.status != 200:
            raise Exception(f"Oanda API Error: {response.body}")

        candles_data = []
        for c in response.get("candles", 200):
            if c.complete:
                candles_data.append({
                    "timestamp": pd.to_datetime(c.time),
                    "open": float(c.mid.o),
                    "high": float(c.mid.h),
                    "low": float(c.mid.l),
                    "close": float(c.mid.c),
                    "volume": float(c.volume)
                })
        
        if not candles_data:
            return pd.DataFrame()
            
        df = pd.DataFrame(candles_data)
        df.set_index("timestamp", inplace=True)
        return df
