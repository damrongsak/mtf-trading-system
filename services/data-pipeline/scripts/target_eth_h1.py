
import asyncio
import logging
import sys
import os
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal
from app.models.market import MarketSymbol
from app.models.candle import Candle
from app.adapters.binance import BinanceClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TargetedBackfill")

async def target_backfill():
    db = SessionLocal()
    try:
        ms = db.query(MarketSymbol).filter(MarketSymbol.symbol == "ETHUSDT").first()
        if not ms:
            print("ETHUSDT not found")
            return
            
        client = BinanceClient()
        tf = "H1"
        days = 30
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        start_ts = int(start_date.timestamp() * 1000)
        
        current_to_ts = int(end_date.timestamp() * 1000)
        total_saved = 0
        
        while current_to_ts > start_ts:
            raw_candles = client.fetch_candles(
                symbol="ETHUSDT",
                timeframe=tf,
                count=1000,
                end_time=current_to_ts
            )
            
            if not raw_candles:
                break
                
            earliest_ts = current_to_ts
            
            for c in raw_candles:
                open_time = c[0]
                if open_time < earliest_ts:
                    earliest_ts = open_time
                if open_time < start_ts:
                    continue
                
                ts = datetime.fromtimestamp(open_time / 1000.0, tz=timezone.utc)
                
                # Check if exists
                existing = db.query(Candle).filter(
                    Candle.market_symbol_id == ms.id,
                    Candle.timeframe == tf,
                    Candle.timestamp == ts
                ).first()
                
                if not existing:
                    new_candle = Candle(
                        market_symbol_id=ms.id,
                        symbol=ms.symbol,
                        timeframe=tf,
                        timestamp=ts,
                        open=float(c[1]),
                        high=float(c[2]),
                        low=float(c[3]),
                        close=float(c[4]),
                        volume=float(c[5]),
                        is_complete=True
                    )
                    db.add(new_candle)
            
            db.commit()
            total_saved += 1000 # Approximation per chunk
            print(f"Processed chunk. Earliest: {datetime.fromtimestamp(earliest_ts/1000, tz=timezone.utc)}")
            
            if earliest_ts >= current_to_ts:
                break
            current_to_ts = earliest_ts - 1
            if len(raw_candles) < 500: break

        print(f"Targeted backfill for ETHUSDT H1 completed.")

    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(target_backfill())
