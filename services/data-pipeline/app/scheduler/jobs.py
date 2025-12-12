from app.adapters.oanda import OandaClient
from app.database import SessionLocal
from app.models.candle import Candle
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime
import pandas as pd
import logging

logger = logging.getLogger(__name__)

async def run_ingestion_job(symbols: list[str] = None):
    """
    Scheduled job to fetch and store candles for core timeframes.
    Args:
        symbols: Optional list of symbols to ingest. Defaults to ["XAU_USD"].
    """
    logger.info("Starting ingestion job...")
    client = OandaClient()
    db = SessionLocal()
    
    if symbols is None:
        symbols = ["XAU_USD"]
    
    timeframes = ["M15", "H1", "H4", "D"] 
    
    try:
        for symbol in symbols:
            for tf in timeframes:
                logger.info(f"Fetching {symbol} {tf}...")
                candles = client.fetch_candles(symbol, tf, count=50) # Fetch recent 50 to catch up
                
                # Transform and Loading
                for c in candles:
                    # Oanda returns RFC3339, we parse to datetime
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
                    
                    # Upsert (Update on Conflict)
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
