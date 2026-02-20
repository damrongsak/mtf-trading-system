import pandas as pd
import numpy as np
import yfinance as yf
import asyncpg
import redis.asyncio as redis
import os
import json
import logging
from datetime import datetime, timedelta
import asyncio
from io import BytesIO

logger = logging.getLogger("olympus-predictor.data")

class DataLoader:
    def __init__(self, db_pool: asyncpg.Pool, redis_client: redis.Redis):
        self.db = db_pool
        self.redis = redis_client
        self.macro_cache_ttl = 3600  # 1 hour capture for macro data
    
    async def get_gold_data(self, limit: int = 5000) -> pd.DataFrame:
        """
        Fetch Gold (XAUUSD) data directly from DB with high performance.
        Using asyncpg and converting to pandas.
        """
        # We assume XAUUSD is the symbol name in stored DB
        query = """
            SELECT timestamp, open, high, low, close, volume 
            FROM candles 
            WHERE symbol = 'XAUUSD' AND timeframe = 'M15'
            ORDER BY timestamp DESC 
            LIMIT $1
        """
        
        try:
            # asyncpg returns Record objects
            records = await self.db.fetch(query, limit)
            
            if not records:
                logger.warning("No Gold data found in DB")
                return pd.DataFrame()
                
            # Convert to DataFrame - optimized approach
            # Using simple list of dicts or records is usually fast enough for 5k rows
            # For strictly high perf with millions of rows, we'd use copy_to_bytes
            data = [dict(r) for r in records]
            df = pd.DataFrame(data)
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
            
            # Ensure native float types for ML models (asyncpg returns Decimal)
            cols = ['open', 'high', 'low', 'close', 'volume']
            df[cols] = df[cols].astype(float)
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch Gold data: {e}")
            raise e

    async def get_macro_data(self, lookback_days: int = 50) -> pd.DataFrame:
        """
        Fetch Macro indicators from yfinance with Redis caching.
        Assets:
        - CL=F (Crude Oil)
        - EURUSD=X (EUR/USD)
        - ^TNX (10Y Treasury Yield)
        """
        tickers = ['CL=F', 'EURUSD=X', '^TNX']
        cache_key = f"macro_data_m15_{datetime.now().strftime('%Y-%m-%d_%H')}" # Cache key valid for the hour
        
        cached = await self.redis.get(cache_key)
        if cached:
            logger.info("Serving Macro data from Redis cache")
            return pd.read_json(BytesIO(cached.encode()))

        logger.info("Fetching Macro data from yfinance...")
        
        try:
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(None, self._fetch_yfinance, tickers, lookback_days)
            
            if not df.empty:
                await self.redis.set(cache_key, df.to_json(), ex=self.macro_cache_ttl)
                
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch Macro data: {e}")
            return pd.DataFrame()

    def _fetch_yfinance(self, tickers: list, lookback_days: int) -> pd.DataFrame:
        """Blocking yfinance call"""
        start_date = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
        # Use 15m interval to match M15 candles
        # Note: 15m data is only available for last 60 days
        data = yf.download(tickers, start=start_date, interval='15m', progress=False)
        
        # yfinance returns MultiIndex columns (Price, Ticker) -> Flatten or extract Close
        # We start by taking 'Close' or 'Adj Close'
        # Check structure
        if isinstance(data.columns, pd.MultiIndex):
             # Extract Close prices
            df = data['Close']
        else:
            df = data
            
        # Handle missing values (forward fill then backward fill)
        df = df.ffill().bfill()
        
        # Ensure UTC timezone alignment might be tricky as yfinance returns localized or naive
        # We will standardize on UTC
        if df.index.tz is None:
            df.index = df.index.tz_localize('UTC')
        else:
            df.index = df.index.tz_convert('UTC')
            
        return df

