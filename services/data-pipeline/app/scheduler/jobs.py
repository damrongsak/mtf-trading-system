from app.adapters.oanda import OandaClient
from app.database import SessionLocal
from app.models.candle import Candle
## Removed insert import as it's handled by repo
from app.repositories.candle_repository import CandleRepository
from app.repositories.market_repository import MarketRepository
from datetime import datetime
import pandas as pd
import logging
import json
import asyncio
from app.streaming.publisher import RedisPublisher
from app.utils.retry import async_retry

logger = logging.getLogger(__name__)

@async_retry(max_retries=3, initial_delay=2, exceptions=(Exception,))
async def fetch_candles_safe(client_ctx, **kwargs):
    """Safe wrapper for OANDA candle fetch with retry."""
    return await asyncio.to_thread(client_ctx.instrument.candles, **kwargs)

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
    from app.models.system_config import SystemConfig
    
    # 0. Load Supported Timeframes
    default_timeframes = ["M5", "M15", "H1", "H4", "D", "W", "M"]
    try:
        config_record = db.query(SystemConfig).filter(SystemConfig.key == "supported_timeframes").first()
        if config_record and isinstance(config_record.value, list):
            timeframes = config_record.value
        else:
             timeframes = default_timeframes
    except Exception as e:
        logger.warning(f"Failed to load system config, using defaults: {e}")
        timeframes = default_timeframes 
    
    try:
        # Initialize Publisher
        publisher = RedisPublisher()
        await publisher.connect()

        # 1. Fetch Market Symbols configured for OANDA
        repo = MarketRepository(db)
        # Assuming we just get OANDA symbols. 
        # But get_symbols_for_datasource needs ID. 
        # Let's import MarketRepository first.
        # We can query all active OANDA symbols using helper in manager logic or just use repo methods.
        # Repository has get_active_symbols(broker='OANDA')
        market_symbols = repo.get_active_symbols("OANDA")

        if symbols:
            # Filter in python if repository doesn't support list filter yet.
            # Or assume symbols arg is small.
            market_symbols = [ms for ms in market_symbols if ms.symbol in symbols]
            
        # market_symbols = query.all() # Removed query usage
        
        if not market_symbols:
            logger.warning("No OANDA symbols found in database to ingest.")
            await publisher.close()
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
                            response = await fetch_candles_safe(client.ctx, **kwargs)
                            
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
                                
                            # Bulk Upsert via Repository
                            candle_repo = CandleRepository(db)
                            await asyncio.to_thread(candle_repo.bulk_upsert, batch_data)
                            
                            logger.info(f"Saved {len(batch_data)} candles for {symbol_name} {tf}")
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
                    # User requested 100 to ensure faster import
                    candles = await asyncio.to_thread(client.fetch_candles, symbol_name, tf, count=100)
                    
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
                        candle_repo = CandleRepository(db)
                        await asyncio.to_thread(candle_repo.bulk_upsert, batch_data)
                        logger.info(f"Saved {len(batch_data)} candles for {symbol_name} {tf}")

                        # Publish Events for Completed Candles
                        for c_data in batch_data:
                            if c_data['is_complete']:
                                # Convert to JSON-friendly dict (handle UUIDs if needed, but ms.id is UUID object? 
                                # c_data['market_symbol_id'] is UUID. json dump check)
                                event_payload = c_data.copy()
                                event_payload['market_symbol_id'] = str(event_payload['market_symbol_id'])
                                
                                channel = f"market_data:candle:{symbol_name}:{tf}"
                                try:
                                    # Legacy Pub/Sub
                                    await publisher.publish(channel, event_payload)
                                    
                                    # Smart Latch: Publish to Stream
                                    stream_payload = {
                                        "event_type": "candle_completed",
                                        "symbol": symbol_name,
                                        "timeframe": tf,
                                        "timestamp": event_payload['timestamp'].isoformat() if hasattr(event_payload['timestamp'], 'isoformat') else str(event_payload['timestamp']),
                                        "c_open": event_payload['open'],
                                        "c_high": event_payload['high'],
                                        "c_low": event_payload['low'],
                                        "c_close": event_payload['close'],
                                        "c_volume": event_payload['volume'],
                                        "data": json.dumps(event_payload, default=str)
                                    }
                                    await publisher.xadd("market.data.stream", stream_payload)
                                    
                                except Exception as pub_err:
                                    logger.error(f"Failed to publish event {channel}/stream: {pub_err}")
                
    except Exception as e:
        logger.error(f"Ingestion job failed: {e}")
        db.rollback()
    finally:
        if 'publisher' in locals():
            await publisher.close()
        db.close()
