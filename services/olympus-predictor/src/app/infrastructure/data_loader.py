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

logger = logging.getLogger("olympus-predictor.infrastructure.data")

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
        query = """
            SELECT timestamp, open, high, low, close, volume 
            FROM candles 
            WHERE symbol = 'XAUUSD' AND timeframe = 'M15'
            ORDER BY timestamp DESC 
            LIMIT $1
        """
        
        try:
            records = await self.db.fetch(query, limit)
            
            if not records:
                logger.warning("No Gold data found in DB")
                return pd.DataFrame()
                
            data = [dict(r) for r in records]
            df = pd.DataFrame(data)
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
            
            cols = ['open', 'high', 'low', 'close', 'volume']
            df[cols] = df[cols].astype(float)
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch Gold data: {e}")
            raise e

    async def get_macro_data(self, lookback_days: int = 59) -> pd.DataFrame:
        """
        Fetch Macro indicators from yfinance with Redis caching.
        Assets: CL=F, EURUSD=X, ^TNX
        Note: yfinance 15m data is limited to last 60 days.
        """
        lookback_days = min(lookback_days, 59)
        tickers = ['CL=F', 'EURUSD=X', '^TNX']
        cache_key = f"macro_data_m15_{datetime.now().strftime('%Y-%m-%d_%H')}" 
        
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

    async def get_sentiment_data(self, symbol: str = 'XAUUSD', lookback_days: int = 30) -> pd.DataFrame:
        """
        Fetch Sentiment scores from DB with Redis caching.
        Phase 4: Multi-tier retrieval (Redis -> DB -> Fallback).
        """
        cache_key = f"sentiment_data_{symbol}_{datetime.now().strftime('%Y-%m-%d_%H')}"
        
        # 1. Redis Cache
        cached = await self.redis.get(cache_key)
        if cached:
            try:
                data = json.loads(cached)
                return pd.DataFrame(data).set_index('timestamp')
            except Exception:
                pass

        # 2. Database
        query = """
            SELECT created_at as timestamp, score
            FROM sentiment_scores
            WHERE symbol = $1 AND created_at >= NOW() - $2 * INTERVAL '1 day'
            ORDER BY created_at ASC
        """
        try:
            records = await self.db.fetch(query, symbol, lookback_days)
            if records:
                data = [dict(r) for r in records]
                df = pd.DataFrame(data)
                df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
                df.set_index('timestamp', inplace=True)
                
                # Cache results
                await self.redis.set(cache_key, df.reset_index().to_json(orient='records'), ex=3600)
                return df
        except Exception as e:
            logger.error(f"Database sentiment fetch failed: {e}")

        # 3. Fallback (Neutral)
        logger.warning(f"Sentiment data unavailable for {symbol}, falling back to neutral (0.0)")
        return pd.DataFrame()

    def _fetch_yfinance(self, tickers: list, lookback_days: int) -> pd.DataFrame:
        """Blocking yfinance call"""
        start_date = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
        data = yf.download(tickers, start=start_date, interval='15m', progress=False)
        
        if isinstance(data.columns, pd.MultiIndex):
            df = data['Close']
        else:
            df = data
            
        df = df.ffill().bfill()
        
        if df.index.tz is None:
            df.index = df.index.tz_localize('UTC')
        else:
            df.index = df.index.tz_convert('UTC')
            
        return df
