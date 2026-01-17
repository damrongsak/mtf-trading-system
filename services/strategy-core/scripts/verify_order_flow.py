
import asyncio
import os
import sys
import json
import logging
from datetime import datetime, timedelta

# Add app directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import redis.asyncio as redis
# from app.streaming.publisher import RedisPublisher # Not available in strategy-core
from app.database import SessionLocal
from app.models.signal_log import SignalLog
from app.engine.core import strategy_engine
from app.market_data import market_data_manager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_order_flow")

async def main():
    logger.info("Starting End-to-End Verification for Order Flow V1")
    
    # 1. Setup Wrapper Dependencies
    # We need to simulate the Engine running or rely on the actual running engine?
    # RLY: We can instantiate a local engine for this test script if we don't want to rely on the background service.
    # PROB: Redis channels might conflict if the real service is running. 
    # SOL: Use a unique symbol for testing.
    TEST_SYMBOL = "TEST_FLOW_USD"
    
    # 2. Register Strategy for Test Symbol
    # We manually create a strategy instance in the engine
    config = {
        "id": "test-order-flow-strat-1",
        "template_id": "order_flow_v1", # MATCHES folder name
        "symbol": TEST_SYMBOL,
        "timeframe": "M15",
        "execution_mode": "MANUAL",
        "parameters": {
            "ema_period": 5 # Short EMA for easy trend filter pass
        }
    }
    
    # Initialize Engine Components
    await strategy_engine.subscriber.connect()
    
    await strategy_engine.start_strategy(config["id"], config)
    logger.info(f"Strategy {config['id']} started for {TEST_SYMBOL}")
    
    # 3. Simulate Data Stream
    # publisher = RedisPublisher()
    # await publisher.connect()
    # Direct Redis Connection
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    logger.info(f"Connecting to Redis at {redis_url}")
    redis_client = redis.from_url(redis_url, decode_responses=True)
    logger.info("Connected to Redis")
    
    start_price = 100.0
    start_time = datetime.utcnow()
    
    # Sequence:
    # A. Establish Trend (Above EMA) -> 10 candles rising
    # B. Trigger Imbalance -> Big Buy Delta candle
    
    logger.info("Simulating Trend Establishment...")
    # Because our strategy logic uses `close > EMA`, we just need price to be consistent.
    # We'll inject M15 candles directly via market_data_manager first to prime the EMA?
    # OR we just simulate ticks. 
    # Simulating 200 ticks is tedious. 
    # Let's direct inject history into market_data_manager for the trend, then tick for signal.
    
    import pandas as pd
    history_frames = []
    for i in range(10):
        history_frames.append({
            'timestamp': start_time - timedelta(minutes=15 * (10 - i)),
            'open': 90 + i, 'high': 91 + i, 'low': 90 + i, 'close': 91 + i,
            'volume': 100, 'delta': 0, 'footprint': []
        })
    df_history = pd.DataFrame(history_frames)
    market_data_manager.set_data(TEST_SYMBOL, df_history)
    
    logger.info("Simulating Aggressive Buying (Imbalance Tick)...")
    # Current Last Price is 100 (90+9+1 approx)
    # We send ticks: 101, 101, 101 ... to create Ask Vol
    
    # To trigger the engine, we MUST publish to Redis "market_data:tick:{symbol}"
    # The Engine listens to "market_data:*"
    
    channel = f"market_data:tick:{TEST_SYMBOL}" # Core listener expects market_data:{symbol} ?
    # Let's check core.py -> LiveRunner subscribes to market_data:*
    # on_tick checks data['instrument']
    # Publisher usually publishes to market_data:{symbol}
    
    pub_channel = f"market_data:{TEST_SYMBOL}"
    
    # Send a series of BUY ticks
    # Price 102.0
    for i in range(20):
        payload = {
            "type": "PRICE",
            "instrument": TEST_SYMBOL,
            "time": (datetime.utcnow()).isoformat(),
            "bid": 101.9,
            "ask": 102.0, # Price is Ask (Buying)
            "status": "tradeable"
        }
        await redis_client.publish(pub_channel, json.dumps(payload))
        # Manually trigger engine processing if we are running standalone
        # Currently `strategy_engine` creates its own subscriber. 
        # Since we are in the same process, we can just call on_tick directly!
        # Waiting for Redis roundtrip in same process might be flaky depending on loop.
        # Direct call is safer for script.
        await strategy_engine.on_tick(payload)
        
    logger.info("Ticks injected.")
    
    # 4. Verify Signal Log
    logger.info("Checking Database for Signals...")
    db = SessionLocal()
    try:
        signals = db.query(SignalLog).filter(
            SignalLog.symbol == TEST_SYMBOL,
            SignalLog.strategy_name == f"Strategy-{config['id']}"
        ).all()
        
        if signals:
            logger.info("✅ SUCCESS: Signal Generated!")
            for s in signals:
                logger.info(f"Signal: {s.direction} @ {s.price} | Reason: {s.reason}")
                logger.info(f"Metadata: {s.meta_data}")
        else:
            logger.error("❌ FAILURE: No signals generated.")
            
            # Debug: Check Market Data state
            df = market_data_manager.get_data(TEST_SYMBOL)
            logger.info("Market Data Dump (Last Row):")
            if not df.empty:
                logger.info(df.iloc[-1].to_dict())
                
    finally:
        db.close()
        await redis_client.aclose()
        # Clean up strategy?
        
if __name__ == "__main__":
    asyncio.run(main())
