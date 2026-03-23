
import asyncio
import logging
import sys
import os
import time
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

# Ensure app is in path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal
from app.models.market import MarketSymbol
from app.models.data_source import DataSource
from app.models.candle import Candle
from app.adapters.oanda import OandaClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("OandaBackfill")

async def backfill_oanda(days: int = 30):
    db = SessionLocal()
    try:
        # 1. Find OANDA Data Source
        ds = db.query(DataSource).filter(DataSource.name == "OANDA", DataSource.is_active == True).first()
        if not ds:
            logger.error("OANDA Data Source not found or inactive.")
            return

        # 2. Get Active OANDA Symbols
        active_symbols = db.query(MarketSymbol).filter(
            MarketSymbol.data_source_id == ds.id,
            MarketSymbol.is_active == True
        ).all()

        if not active_symbols:
            logger.warning("No active OANDA symbols found.")
            return

        client = OandaClient()
        
        # OANDA Timeframes
        timeframes = ["M1", "M5", "M15", "H1", "H4", "D1", "W1", "MN1"]
        
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        for ms in active_symbols:
            logger.info(f"Processing OANDA symbol: {ms.symbol}")
            
            # Robust details check
            details = ms.details or {}
            broker_symbol = details.get('broker_symbol') or ms.symbol

            for tf in timeframes:
                logger.info(f"  Timeframe: {tf}")
                
                current_to = end_date
                total_saved = 0
                
                # Safety break after 100 chunks to prevent infinite loops
                chunk_count = 0
                while current_to > start_date and chunk_count < 100:
                    chunk_count += 1
                    try:
                        logger.info(f"    Fetching 5000 candles before {current_to}...")
                        to_str = current_to.isoformat()
                        
                        raw_candles = client.fetch_candles(
                            symbol=ms.symbol,
                            timeframe=tf,
                            count=5000,
                            to=to_str,
                            broker_symbol=broker_symbol
                        )
                        
                        if not raw_candles:
                            logger.info("    No more candles found.")
                            break
                        
                        candles_to_save = []
                        earliest_ts = current_to
                        
                        for c in raw_candles:
                            if not c or not isinstance(c, dict):
                                continue
                                
                            ts_str = c.get('time')
                            if not ts_str: continue
                            
                            ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                            if ts < earliest_ts:
                                earliest_ts = ts
                            
                            if ts < start_date:
                                continue
                                
                            mid = c.get('mid')
                            if not mid: continue
                            
                            candles_to_save.append({
                                "market_symbol_id": ms.id,
                                "symbol": ms.symbol,
                                "timeframe": tf,
                                "timestamp": ts,
                                "open": float(mid.get('o', 0)),
                                "high": float(mid.get('h', 0)),
                                "low": float(mid.get('l', 0)),
                                "close": float(mid.get('c', 0)),
                                "volume": float(c.get('volume', 0)),
                                "is_complete": c.get('complete', True)
                            })

                        # Save Chunk
                        if candles_to_save:
                            count = 0
                            for c_data in candles_to_save:
                                existing = db.query(Candle).filter(
                                    Candle.market_symbol_id == c_data['market_symbol_id'],
                                    Candle.timeframe == c_data['timeframe'],
                                    Candle.timestamp == c_data['timestamp']
                                ).first()
                                
                                if existing:
                                    existing.open = c_data['open']
                                    existing.high = c_data['high']
                                    existing.low = c_data['low']
                                    existing.close = c_data['close']
                                    existing.volume = c_data['volume']
                                else:
                                    db.add(Candle(**c_data))
                                count += 1
                            
                            db.commit()
                            total_saved += count
                            logger.info(f"    Saved {count} candles. Total: {total_saved}. Earliest: {earliest_ts}")
                        
                        if earliest_ts >= current_to:
                            break
                        current_to = earliest_ts
                        
                        if len(raw_candles) < 100:
                            break
                            
                    except Exception as e:
                        logger.error(f"    Error fetching Oanda candles: {e}")
                        break
                
                logger.info(f"  Finished {ms.symbol} {tf}. Total saved: {total_saved}")

    except Exception as e:
        logger.error(f"Global Oanda Backfill Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args()
    
    asyncio.run(backfill_oanda(days=args.days))
