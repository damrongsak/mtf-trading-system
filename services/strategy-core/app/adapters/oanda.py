import v20
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional
from app.models.candle import Candle
from app.models.data_source import DataSource
from app.database import SessionLocal
import json
import os

class OandaAdapter:
    def __init__(self, data_source_id: str):
        self.db = SessionLocal()
        self.data_source = self.db.query(DataSource).filter(DataSource.id == data_source_id).first()
        if not self.data_source:
            raise ValueError(f"DataSource {data_source_id} not found")
        
        self.config = self.data_source.config_json
        self.ctx = v20.Context(
            hostname=self.config.get("hostname", "api-fxpractice.oanda.com"),
            port=443,
            token=self.config.get("token"),
            datetime_format="RFC3339"
        )
        self.account_id = self.config.get("account_id")

    def fetch_candles(self, symbol: str, timeframe: str, count: int = 500) -> List[dict]:
        """
        Fetch candles from Oanda.
        
        Args:
            symbol: Instrument name (e.g., "EUR_USD")
            timeframe: Granularity (e.g., "M15", "H1", "H4", "D")
            count: Number of candles to fetch
            
        Returns:
            List of candle dictionaries
        """
        response = self.ctx.instrument.candles(
            instrument=symbol,
            granularity=timeframe,
            count=count,
            price="M" # Midpoint candles
        )

        if response.status != 200:
            raise Exception(f"Oanda API Error: {response.body}")

        candles = []
        for c in response.get("candles", 200):
            if c.complete:
                candles.append({
                    "timestamp": c.time,
                    "open": float(c.mid.o),
                    "high": float(c.mid.h),
                    "low": float(c.mid.l),
                    "close": float(c.mid.c),
                    "volume": float(c.volume)
                })
        
        return candles

    def get_account_summary(self):
        response = self.ctx.account.summary(self.account_id)
        if response.status != 200:
            raise Exception(f"Oanda API Error: {response.body}")
        return response.get("account", 200)
