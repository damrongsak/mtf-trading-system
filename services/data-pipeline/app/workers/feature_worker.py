import asyncio
import logging
import json
import pandas as pd
import numpy as np
from app.streaming.publisher import RedisPublisher
from app.database import SessionLocal
from app.repositories.candle_repository import CandleRepository
from app.repositories.market_repository import MarketRepository
from app.models.market import MarketSymbol
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class FeatureWorker:
    def __init__(self):
        self.publisher = RedisPublisher()
        self.running = False
        self.batch_size = 10
        self.stream_key = "market.data.stream"
        self.group_name = "feature_group"
        self.consumer_name = "worker_1" # In prod, unique ID

    async def start(self):
        self.running = True
        await self.publisher.connect()
        
        # Create Consumer Group
        try:
            # 0 means start from beginning? Or "$" for new? 
            # Use "$" to only process new events if restarting, or "0" to replay.
            # For data integrity, "0" is safer but might process old data.
            # Let's use "$" for now to avoid reprocessing entire history on restart during dev.
            # Actually, catching un-ACKed messages is handled by XAUTOCLAIM usually.
            # Simple XGROUP CREATE for now.
            await self.publisher.redis.xgroup_create(self.stream_key, self.group_name, id="$", mkstream=True)
            logger.info(f"Created consumer group {self.group_name}")
        except Exception as e:
            if "BUSYGROUP" not in str(e):
                logger.error(f"Group create error: {e}")
            else:
                logger.info(f"Consumer group {self.group_name} already exists.")

        asyncio.create_task(self._consume_loop())

    async def stop(self):
        self.running = False
        await self.publisher.close()

    async def _consume_loop(self):
        logger.info("FeatureWorker loop started.")
        while self.running:
            try:
                # Read new messages
                streams = await self.publisher.redis.xreadgroup(
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
                        await self.publisher.redis.xack(self.stream_key, self.group_name, message_id)

            except Exception as e:
                logger.error(f"FeatureWorker loop/consumption error: {e}")
                await asyncio.sleep(5)

    async def process_message(self, message_id, fields):
        try:
            event_type = fields.get("event_type")
            if event_type != "candle_completed":
                return

            symbol = fields.get("symbol")
            timeframe = fields.get("timeframe")
            
            # We need history to calculate features.
            # Fetch last 200 candles from DB.
            features = await self.calculate_features(symbol, timeframe)
            
            if features:
                # Publish to Alpha Stream (Smart Latch)
                # We include the original message payload + features
                payload = {
                    "event_type": "features_calculated",
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "timestamp": fields.get("timestamp"),
                    "features": json.dumps(features, default=str),
                    "features_complete": "true"
                }
                
                # 1. Publish to Stream
                await self.publisher.xadd("market.alpha.stream", payload)
                
                # 2. Publish to standard Pub/Sub for frontend (Feature Matrix)
                pubsub_channel = f"market.features.{symbol}"
                await self.publisher.publish(pubsub_channel, features)
                
                logger.info(f"Published features for {symbol} {timeframe}")

        except Exception as e:
            logger.error(f"Error processing message {message_id}: {e}")

    async def calculate_features(self, symbol: str, timeframe: str):
        """
        Fetch history and calculate technical indicators.
        """
        # Run in thread pool to avoid blocking async loop with heavy pandas/DB ops
        return await asyncio.to_thread(self._calculate_sync, symbol, timeframe)

    def _calculate_sync(self, symbol: str, timeframe: str):
        db = SessionLocal()
        try:
            market_repo = MarketRepository(db)
            ms = market_repo.get_any_by_symbol(symbol)
            if not ms:
                logger.warning(f"FeatureWorker: Symbol {symbol} not found in DB.")
                return None
            
            candle_repo = CandleRepository(db)
            # Fetch last 200 candles
            candles = candle_repo.get_candles_paginated(ms.id, timeframe, page=1, page_size=200)
            # Note: get_candles_paginated typically returns DESC order (latest first).
            # We need them in ASC order for calculation.
            
            if len(candles) < 50:
                return None

            # Convert to DataFrame
            data = [{
                "close": c.close,
                "high": c.high,
                "low": c.low,
                "volume": c.volume,
                "timestamp": c.timestamp
            } for c in candles]
            
            df = pd.DataFrame(data)
            df = df.sort_values("timestamp") # Ensure ASC
            
            # Calculations
            # 1. RSI (14)
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi_14'] = 100 - (100 / (1 + rs))
            
            # 2. SMA (20, 50, 200)
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            
            # 3. ATR (14)
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = np.max(ranges, axis=1)
            df['atr_14'] = true_range.rolling(window=14).mean()
            
            # 4. Volatility (StdDev of returns) - simple proxy
            df['volatility'] = df['close'].pct_change().rolling(window=20).std()

            # Get latest values
            latest = df.iloc[-1]
            
            return {
                "type": "FEATURE",
                "symbol": symbol,
                "timeframe": timeframe,
                "timestamp": latest['timestamp'], # Should match stream
                "rsi_14": float(latest['rsi_14']) if not pd.isna(latest['rsi_14']) else None,
                "sma_20": float(latest['sma_20']) if not pd.isna(latest['sma_20']) else None,
                "sma_50": float(latest['sma_50']) if not pd.isna(latest['sma_50']) else None,
                "atr_14": float(latest['atr_14']) if not pd.isna(latest['atr_14']) else None,
                "volatility": float(latest['volatility']) if not pd.isna(latest['volatility']) else None,
                "close": float(latest['close'])
            }

        except Exception as e:
            logger.error(f"Calculation error for {symbol}: {e}")
            return None
        finally:
            db.close()
