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
        symbols: Optional list of symbol names to filter.
        from_date: Optional start datetime for backfill.
        to_date: Optional end datetime for backfill.
    """
    logger.info(f"Starting ingestion job... Filter: {symbols}, Range: {from_date} - {to_date}")
    client = OandaClient()
    db = SessionLocal()
    
    # Imports inside function to avoid circular deps if any
    from app.models.market import MarketSymbol
    from app.models.data_source import DataSource
    
    timeframes = ["M15", "H1", "H4", "D"] 
    
    try:
        # 1. Fetch Market Symbols configured for OANDA
        query = db.query(MarketSymbol).join(DataSource).filter(DataSource.name == "OANDA")
        if symbols:
            query = query.filter(MarketSymbol.symbol.in_(symbols))
            
        market_symbols = query.all()
        
        if not market_symbols:
            logger.warning("No OANDA symbols found in database to ingest.")
            return

        for ms in market_symbols:
            symbol_name = ms.symbol
            # OANDA specific formatting if needed (e.g. XAU_USD is fine usually)
            
            for tf in timeframes:
                logger.info(f"Processing {symbol_name} {tf} (ID: {ms.id})...")
                
                if from_date and to_date:
                    # BACKFILL MODE
                    current_start = from_date
                    total_saved = 0
                    
                    while True:
                        kwargs = {
                            "instrument": symbol_name,
                            "granularity": tf,
                            "price": "M",
                            "fromTime": current_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            "count": 2500,
                            "includeFirst": current_start == from_date
                        }
                        
                        try:
                            # Using client.ctx check similar to before
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
                                        "market_symbol_id": ms.id,
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
                                index_elements=['market_symbol_id', 'timeframe', 'timestamp'],
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
                            
                    logger.info(f"Backfill complete for {symbol_name} {tf}: {total_saved} candles.")

                else:
                    # REAL-TIME CATCHUP (Default)
                    candles = client.fetch_candles(symbol_name, tf, count=50)
                    
                    if not candles:
                        continue

                    batch_data = []
                    for c in candles:
                        timestamp = pd.to_datetime(c['time']).to_pydatetime()
                        batch_data.append({
                            "market_symbol_id": ms.id,
                            "timeframe": tf,
                            "timestamp": timestamp,
                            "open": float(c['mid']['o']),
                            "high": float(c['mid']['h']),
                            "low": float(c['mid']['l']),
                            "close": float(c['mid']['c']),
                            "volume": int(c['volume']),
                            "is_complete": c['complete']
                        })
                    
                    if batch_data:
                        stmt = insert(Candle).values(batch_data)
                        do_update_stmt = stmt.on_conflict_do_update(
                            index_elements=['market_symbol_id', 'timeframe', 'timestamp'],
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
                        logger.info(f"Saved {len(batch_data)} candles for {symbol_name} {tf}")
                
    except Exception as e:
        logger.error(f"Ingestion job failed: {e}")
        db.rollback()
    finally:
        db.close()
