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
from app.indicators import (
    calculate_rsi, calculate_atr, calculate_macd, calculate_bbands, 
    calculate_ema, calculate_adx, detect_structure,
    detect_order_blocks, detect_fvg, detect_liquidity_sweeps
)

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

    async def start(self):
        self.running = True
        self.redis = redis.from_url(self.redis_url, decode_responses=True)
        logger.info(f"IndicatorWorker connected to Redis at {self.redis_url}")
        
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
        if self.redis:
            await self.redis.close()

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
            
            # Calculations
            # Using centralized logic from app.indicators
            
            # 1. RSI (14)
            try:
                df['rsi_14'] = calculate_rsi(df['close'], window=14)
            except Exception as e:
                logger.debug(f"RSI calc failed: {e}")
                df['rsi_14'] = None
            
            # 2. SMA/EMA
            # Using EMAs as per standard
            df['ema_9'] = calculate_ema(df['close'], span=9)
            df['ema_20'] = calculate_ema(df['close'], span=20)
            df['ema_50'] = calculate_ema(df['close'], span=50)
            df['ema_200'] = calculate_ema(df['close'], span=200)

            # 3. ATR (14)
            try:
                df['atr_14'] = calculate_atr(df['high'], df['low'], df['close'], window=14)
            except Exception as e:
                logger.debug(f"ATR calc failed: {e}")
                df['atr_14'] = None
            
            # 4. Volatility (20) - SMA based std dev
            df['volatility'] = df['close'].pct_change().rolling(window=20).std()

            # 5. MACD (12, 26, 9)
            try:
                macd_res = calculate_macd(df['close'], fast=12, slow=26, signal=9)
                df['macd'] = macd_res['macd']
                df['macd_signal'] = macd_res['signal']
                df['macd_hist'] = macd_res['hist']
            except Exception as e:
                logger.debug(f"MACD calc failed: {e}") 
                
            # 6. Bollinger Bands (20, 2.0)
            try:
                bb_res = calculate_bbands(df['close'], window=20, alpha=2.0)
                df['bb_upper'] = bb_res.upper
                df['bb_middle'] = bb_res.middle
                df['bb_lower'] = bb_res.lower
            except Exception as e:
                logger.debug(f"BB calc failed: {e}")

            # 7. ADX (14)
            try:
                adx_res = calculate_adx(df['high'], df['low'], df['close'], length=14)
                if adx_res is not None:
                     df['adx'] = adx_res['adx']
                     df['dmp'] = adx_res['dmp'] # DI+
                     df['dmn'] = adx_res['dmn'] # DI-
            except Exception as e:
                logger.debug(f"ADX calc failed: {e}")

            # 8. High/Low Logic
            # Rolling 20 High/Low (Donchian-like)
            df['high_20'] = df['high'].rolling(window=20).max()
            df['low_20'] = df['low'].rolling(window=20).min()

            # 9. SMC Structure (Swing High/Low)
            swing_high = None
            swing_low = None
            smc_data = {}
            
            try:
                # Calculate full structure
                structure = detect_structure(df, window=5) 
                
                # Get last confirmed labels for simple Swing metrics
                if structure['labels']:
                    highs = [x for x in structure['labels'] if x['text'] in ['H', 'HH', 'LH']]
                    lows = [x for x in structure['labels'] if x['text'] in ['L', 'LL', 'HL']]
                    
                    if highs:
                        swing_high = highs[-1]['price']
                    if lows:
                        swing_low = lows[-1]['price']
                        
                # Package full objects
                smc_data = {
                    "structure": structure,
                    "order_blocks": detect_order_blocks(df),
                    "fvgs": detect_fvg(df),
                    "liquidity_sweeps": detect_liquidity_sweeps(df)
                }

            except Exception as e:
                logger.debug(f"SMC Structure calc failed: {e}")
                smc_data = {"error": str(e)}

            latest = df.iloc[-1]
            
            def safe_float(val):
                if pd.isna(val) or np.isinf(val):
                    return None
                return float(val)

            return {
                "type": "FEATURE",
                "symbol": symbol,
                "timeframe": timeframe,
                "timestamp": latest['timestamp'],
                "close": float(latest['close']),
                "high": float(latest['high']),
                "low": float(latest['low']),
                
                # Indicators
                "rsi_14": safe_float(latest.get('rsi_14')),
                "atr_14": safe_float(latest.get('atr_14')),
                "ema_9": safe_float(latest.get('ema_9')),
                "ema_20": safe_float(latest.get('ema_20')),
                "ema_50": safe_float(latest.get('ema_50')),
                "ema_200": safe_float(latest.get('ema_200')),
                "volatility": safe_float(latest.get('volatility')),
                
                # MACD
                "macd": safe_float(latest.get('macd')),
                "macd_signal": safe_float(latest.get('macd_signal')),
                "macd_hist": safe_float(latest.get('macd_hist')),
                
                # BBands
                "bb_upper": safe_float(latest.get('bb_upper')),
                "bb_middle": safe_float(latest.get('bb_middle')),
                "bb_lower": safe_float(latest.get('bb_lower')),
                
                # ADX
                "adx": safe_float(latest.get('adx')),
                "di_plus": safe_float(latest.get('dmp')),
                "di_minus": safe_float(latest.get('dmn')),
                
                # High/Low
                "high_20": safe_float(latest.get('high_20')),
                "low_20": safe_float(latest.get('low_20')),
                "swing_high": swing_high,
                "swing_low": swing_low,
                
                # Full SMC Objects
                "smc": smc_data
            }

        except Exception as e:
            logger.error(f"Calculation error for {symbol}: {e}")
            return None
        finally:
            db.close()
