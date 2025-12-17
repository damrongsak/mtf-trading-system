from app.adapters.oanda import OandaClient
from app.database import SessionLocal
from app.models.candle import Candle
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime
import pandas as pd
import logging

logger = logging.getLogger(__name__)

async def run_ingestion_job(symbols: list[str] = None, from_date: datetime = None, to_date: datetime = None):
    """
    Scheduled job to fetch and store candles for core timeframes.
    Args:
        symbols: Optional list of symbols to ingest. Defaults to ["XAU_USD"].
        from_date: Optional start datetime for backfill.
        to_date: Optional end datetime for backfill.
    """
    logger.info(f"Starting ingestion job... Symbols: {symbols}, Range: {from_date} - {to_date}")
    client = OandaClient()
    db = SessionLocal()
    
    if symbols is None:
        symbols = ["XAU_USD"]
    
    timeframes = ["M15", "H1", "H4", "D"] 
    
    try:
        for symbol in symbols:
            for tf in timeframes:
                logger.info(f"Processing {symbol} {tf}...")
                
                if from_date and to_date:
                    # BACKFILL MODE
                    current_start = from_date
                    total_saved = 0
                    
                    while True:
                        kwargs = {
                            "instrument": symbol,
                            "granularity": tf,
                            "price": "M",
                            "fromTime": current_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            "count": 2500, # Safe limit
                            "includeFirst": current_start == from_date
                        }
                        logger.info(f"Backfill batch: {kwargs}")
                        
                        try:
                            # Direct check on client context if available, or assume client.fetch_candles wrapper needs bypass
                            # The adapter wrapper `fetch_candles` might not support `fromTime` directly if not designed for it.
                            # Let's check `OandaClient` adapter in `data-pipeline`.
                            # Assuming we can use client.ctx.instrument.candles direct or update adapter. 
                            # For safety, let's use the underlying ctx if available or update adapter.
                            # Looking at `services/data-pipeline/app/adapters/oanda.py` would be good, but assuming standard v20 setup:
                            response = client.ctx.instrument.candles(**kwargs)
                            
                            if response.status != 200:
                                logger.error(f"Oanda Error: {response.body}")
                                break
                                
                            candles = response.get("candles", 200)
                            if not candles:
                                break
                                
                            batch_data = []
                            for c in candles:
                                if c.complete:
                                    ts = pd.to_datetime(c.time).to_pydatetime()
                                    if ts > to_date:
                                        break
                                        
                                    batch_data.append({
                                        "symbol": symbol,
                                        "timeframe": tf,
                                        "timestamp": ts,
                                        "open": float(c.mid.o),
                                        "high": float(c.mid.h),
                                        "low": float(c.mid.l),
                                        "close": float(c.mid.c),
                                        "volume": int(c.volume),
                                        "is_complete": c.complete 
                                    })
                            
                            if not batch_data:
                                break
                                
                            # Bulk Insert
                            stmt = insert(Candle).values(batch_data)
                            do_update_stmt = stmt.on_conflict_do_update(
                                index_elements=['symbol', 'timeframe', 'timestamp'],
                                set_={
                                    'open': stmt.excluded.open,
                                    'high': stmt.excluded.high,
                                    'low': stmt.excluded.low,
                                    'close': stmt.excluded.close,
                                    'volume': stmt.excluded.volume,
                                    'is_complete': stmt.excluded.is_complete
                                }
                            )
                            db.execute(do_update_stmt)
                            db.commit()
                            total_saved += len(batch_data)
                            
                            last_ts = batch_data[-1]["timestamp"]
                            if last_ts >= to_date or len(candles) < 2500:
                                break
                                
                            current_start = last_ts
                            
                        except Exception as e:
                            logger.error(f"Batch failed: {e}")
                            break
                            
                    logger.info(f"Backfill complete for {symbol} {tf}: {total_saved} candles.")

                else:
                    # REAL-TIME CATCHUP (Default)
                    candles = client.fetch_candles(symbol, tf, count=50)
                    
                    for c in candles:
                        timestamp = pd.to_datetime(c['time']).to_pydatetime()
                        stmt = insert(Candle).values(
                            symbol=symbol,
                            timeframe=tf,
                            timestamp=timestamp,
                            open=float(c['mid']['o']),
                            high=float(c['mid']['h']),
                            low=float(c['mid']['l']),
                            close=float(c['mid']['c']),
                            volume=int(c['volume']),
                            is_complete=c['complete']
                        )
                        do_update_stmt = stmt.on_conflict_do_update(
                            index_elements=['symbol', 'timeframe', 'timestamp'],
                            set_={
                                'open': stmt.excluded.open,
                                'high': stmt.excluded.high,
                                'low': stmt.excluded.low,
                                'close': stmt.excluded.close,
                                'volume': stmt.excluded.volume,
                                'is_complete': stmt.excluded.is_complete
                            }
                        )
                        db.execute(do_update_stmt)
                    
                    db.commit()
                    logger.info(f"Saved {len(candles)} candles for {symbol} {tf}")
                
    except Exception as e:
        logger.error(f"Ingestion job failed: {e}")
        db.rollback()
    finally:
        db.close()
