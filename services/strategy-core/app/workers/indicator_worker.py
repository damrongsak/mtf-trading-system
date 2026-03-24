import asyncio
import logging
import json
import os
import socket
from typing import Optional, Dict, Any
import pandas as pd
import numpy as np
import redis.asyncio as redis
from sqlalchemy import text
from app.database import SessionLocal, engine
from app.models.market import MarketSymbol
from app.models.data_source import DataSource
from app.processing.feature_extractor import FeatureExtractor
from app.utils.redis_client import get_redis_client

logger = logging.getLogger(__name__)

class IndicatorWorker:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        self.redis = None
        self.running = False
        self.batch_size = 10
        self.stream_key = "market.data.stream"
        self.group_name = "indicator_group"
        self.consumer_name = os.getenv("HOSTNAME", socket.gethostname())
        self.symbol_cache: Dict[str, Any] = {} # symbol -> market_symbol_id
        self.cache_refresh_interval = 300 # 5 minutes
        self.extractor = FeatureExtractor()

    async def start(self):
        self.running = True
        self.redis = get_redis_client()
        logger.info(f"IndicatorWorker connected to Global Redis Pool")
        
        # Create Consumer Group
        await self._ensure_group_exists()
        
        # Initial Cache Load
        await self._refresh_cache()
        asyncio.create_task(self._cache_maintenance_loop())
        
        asyncio.create_task(self._consume_loop())

    async def _ensure_group_exists(self):
        try:
            # Use "$" to only process new events if restarting, 
            # or "0" to replay all history. "$" is safer for avoiding storms on restart.
            await self.redis.xgroup_create(self.stream_key, self.group_name, id="$", mkstream=True)
            logger.info(f"Created consumer group {self.group_name}")
        except Exception as e:
            if "BUSYGROUP" in str(e):
                logger.info(f"Consumer group {self.group_name} already exists.")
            else:
                logger.error(f"Group create error: {e}")

    async def _refresh_cache(self):
        """Loads all active MarketSymbols into memory."""
        logger.info("Refreshing symbol cache...")
        try:
            db = SessionLocal()
            try:
                # Query only ACTIVE symbols
                # We need the symbol string and the ID
                symbols = db.query(MarketSymbol).filter(MarketSymbol.is_active == True).all()
                
                new_cache = {}
                for s in symbols:
                    new_cache[s.symbol] = s.id
                
                self.symbol_cache = new_cache
                logger.info(f"Loaded {len(self.symbol_cache)} active symbols into cache.")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to refresh symbol cache: {e}")

    async def _cache_maintenance_loop(self):
        """Periodically refreshes the cache."""
        while self.running:
            await asyncio.sleep(self.cache_refresh_interval)
            await self._refresh_cache()

    async def stop(self):
        self.running = False
        # Redis is now global/pooled, do not close it here.
        pass

    async def _consume_loop(self):
        logger.info("IndicatorWorker loop started.")
        while self.running:
            try:
                # Read new messages
                streams = await self.redis.xreadgroup(
                    groupname=self.group_name,
                    consumername=self.consumer_name,
                    streams={self.stream_key: ">"},
                    count=self.batch_size,
                    block=1000
                )

                if not streams:
                    continue

                for stream, messages in streams:
                    for message_id, fields in messages:
                        await self.process_message(message_id, fields)
                        # Ack processing
                        await self.redis.xack(self.stream_key, self.group_name, message_id)

            except Exception as e:
                if "NOGROUP" in str(e):
                    logger.warning(f"Consumer group missing (NOGROUP). Attempting to recreate...")
                    await self._ensure_group_exists()
                else:
                    logger.error(f"IndicatorWorker loop/consumption error: {e}")
                
                await asyncio.sleep(5)

    async def process_message(self, message_id: str, fields: Dict[str, Any]):
        try:
            event_type = fields.get("event_type")
            if event_type != "candle_completed":
                return

            symbol = fields.get("symbol")
            timeframe = fields.get("timeframe")
            
            # 1. Check Cache
            if symbol not in self.symbol_cache:
                # debug log only to avoid spamming if lots of disabled symbols exist
                # logger.debug(f"Skipping {symbol} (not in active cache)")
                return

            market_symbol_id = self.symbol_cache[symbol]
            
            # Fetch history and calculate
            # Run in thread pool to avoid blocking async loop
            features = await asyncio.to_thread(self._calculate_sync, market_symbol_id, symbol, timeframe)
            
            if features:
                # Publish to Alpha Stream
                payload = {
                    "event_type": "features_calculated",
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "timestamp": fields.get("timestamp"),
                    "features": json.dumps(features, default=str),
                    "features_complete": "true"
                }
                
                # 1. Stream
                # Use approximate trimming to 10000 elements
                await self.redis.xadd("market.alpha.stream", payload, maxlen=10000, approximate=True)
                
                # 2. Pub/Sub
                pubsub_channel = f"market.features.{symbol}"
                # Ensure JSON serialization for PubSub
                await self.redis.publish(pubsub_channel, json.dumps(features, default=str))
                
                logger.info(f"Published features for {symbol} {timeframe}")

        except Exception as e:
            logger.error(f"Error processing message {message_id}: {e}")

    def _calculate_sync(self, market_symbol_id: Any, symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
        db = SessionLocal()
        try:
            # Symbol ID is passed directly, no need to lookup
            
            # Fetch Candles (Last 200)
            # Using raw SQL for speed/simplicity as in backtest.py
            query = text("""
                SELECT timestamp, close, high, low, volume 
                FROM candles 
                WHERE market_symbol_id = :market_symbol_id
                AND timeframe = :timeframe 
                ORDER BY timestamp DESC
                LIMIT 200
            """)
            
            df = pd.read_sql(query, db.bind, params={
                "market_symbol_id": market_symbol_id,
                "timeframe": timeframe
            })
            
            if len(df) < 50:
                return None
                
            # Sort ASC for calculation
            df = df.sort_values("timestamp").reset_index(drop=True)
            
            # Extract Features
            return self.extractor.extract_from_dataframe(df, symbol, timeframe)

        except Exception as e:
            logger.error(f"Calculation error for {symbol}: {e}")
            return None
        finally:
            db.close()
