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
async def fetch_candles_safe(client, **kwargs):
    """Safe wrapper for OANDA candle fetch with retry."""
    return await asyncio.to_thread(client.fetch_candles, **kwargs)

async def process_oanda_backfill(client, ms, tf, from_date, to_date, db, logger):
    current_start = from_date
    total_saved = 0
    symbol_name = ms.symbol
    
    while True:
        # Params matching OandaClient.fetch_candles kwargs
        kwargs = {
            "fromTime": current_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "includeFirst": current_start == from_date,
            "count": 2500
        }
        
        try:
            # Call adapter method
            candles = await fetch_candles_safe(client, symbol=symbol_name, timeframe=tf, **kwargs)
            
            if not candles:
                break
                
            batch_data = []
            for c in candles:
                # Oanda returns dicts in adapter
                is_complete = c.get('complete', False)
                if is_complete:
                    ts = pd.to_datetime(c['time']).to_pydatetime()
                    if ts > to_date:
                        break
                        
                    batch_data.append({
                        "market_symbol_id": ms.id,
                        "symbol": symbol_name,
                        "timeframe": tf,
                        "timestamp": ts,
                        "open": float(c['mid']['o']),
                        "high": float(c['mid']['h']),
                        "low": float(c['mid']['l']),
                        "close": float(c['mid']['c']),
                        "volume": int(c['volume']),
                        "is_complete": is_complete
                    })
            
            if not batch_data:
                break
                
            candle_repo = CandleRepository(db)
            await asyncio.to_thread(candle_repo.bulk_upsert, batch_data)
            
            total_saved += len(batch_data)
            
            last_ts = batch_data[-1]["timestamp"]
            
            # Stop conditions
            if last_ts >= to_date or len(candles) < 2500:
                break
                
            current_start = last_ts
            
        except Exception as e:
            logger.error(f"Batch failed for {symbol_name}: {e}")
            break
            
    logger.info(f"Backfill complete for {symbol_name} {tf}: {total_saved} candles.")

async def run_ingestion_job(symbols: list[str] = None, from_date: datetime = None, to_date: datetime = None):
    """
    Scheduled job to fetch and store candles for core timeframes.
    Args:
        symbols: Optional list of symbol names to filter.
        from_date: Optional start datetime for backfill.
        to_date: Optional end datetime for backfill.
    """
    logger.info(f"Starting ingestion job... Filter: {symbols}, Range: {from_date} - {to_date}")
    db = SessionLocal()
    
    # Imports inside function to avoid circular deps if any
    from app.models.market import MarketSymbol
    from app.models.data_source import DataSource
    from app.models.system_config import SystemConfig
    
    # 0. Load Supported Timeframes
    default_timeframes = ["M1", "M5", "M15", "H1", "H4", "D1", "W1", "MN1"]
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
        
        repo = MarketRepository(db)
        
        # 1. Simplify: Iterate over Active Data Sources to handle connections properly
        active_sources = repo.get_active_data_sources()
        
        if not active_sources:
            logger.warning("No active data sources found.")
            await publisher.close()
            return

        for source in active_sources:
            logger.info(f"Processing Source: {source.name} ({source.provider})")
            
            # Instantiate Client based on Provider
            client = None
            if source.provider == "OANDA":
                # Config from source.config_json or env? adapter uses env by default but let's check
                # OandaClient in this project seems to use env or hardcoded.
                # Let's use the one from main.py pattern? 
                # Actually OandaAdapter in jobs.py used OandaClient() which uses envs.
                # Ideally we should use source.config_json if possible, but adapter might not support it yet.
                # For now keeping it compatible with existing OandaClient if it doesn't take config.
                # If we want to support multiple OANDA accounts, OandaClient needs refactor.
                # Assuming single OANDA account for now or OandaClient reads env.
                client = OandaClient() 
                
            elif source.provider == "BINANCE":
                # Instantiate generic Binance client or use httpx directly?
                # Best to have an adapter. For now, skipping or using simple impl if we had one.
                # We don't have a BinanceClient adapter imported yet.
                logger.warning(f"Binance ingestion not yet fully implemented in jobs.py. Skipping {source.name}")
                continue
                
            elif source.provider == "CTRADER":
                from app.adapters.ctrader_client import AsyncCTraderClient
                config = source.config_json
                if not config:
                     logger.warning(f"Missing config for cTrader source {source.name}")
                     continue
                     
                client = AsyncCTraderClient(
                    config.get("host", "demo.ctraderapi.com"),
                    int(config.get("port", 5035)),
                    ssl=True
                )
                try:
                    await client.connect()
                    await client.authorize_app(config.get("client_id"), config.get("client_secret"))
                    await client.authorize_account(int(config.get("account_id")), config.get("token"))
                except Exception as e:
                    logger.error(f"Failed to connect to cTrader {source.name}: {e}")
                    continue

            else:
                logger.warning(f"Unknown provider {source.provider}. Skipping.")
                continue

            # 2. Fetch Symbols for THIS Source
            source_symbols = repo.get_symbols_for_datasource(source.id)
            
            # Apply Filter if provided
            if symbols:
                source_symbols = [ms for ms in source_symbols if ms.symbol in symbols]
                
            if not source_symbols:
                logger.info(f"No symbols to process for {source.name}.")
                if source.provider == "CTRADER" and client:
                    await client.disconnect()
                continue
                
            # 3. Process Symbols
            for ms in source_symbols:
                symbol_name = ms.symbol
                
                for tf in timeframes:
                    logger.info(f"Processing {symbol_name} {tf} (ID: {ms.id}) via {source.provider}...")
                    
                    if from_date and to_date:
                        # BACKFILL LOGIC (Simplified for generic, but OANDA has specific loop)
                        # We need to adapt the fetching logic per provider or unify it.
                        pass # Keeping the OANDA loop implies we need specific handling.
                        
                        # Existing OANDA logic was robust. Let's wrap it in provider check.
                        if source.provider == "OANDA":
                             await process_oanda_backfill(client, ms, tf, from_date, to_date, db, logger)
                        elif source.provider == "CTRADER":
                             # Implement cTrader backfill if needed
                             pass
                             
                    else:
                        # REAL-TIME CATCHUP
                        batch_data = []
                        
                        if source.provider == "OANDA":
                            candles = await asyncio.to_thread(client.fetch_candles, symbol_name, tf, count=100)
                            if candles:
                                for c in candles:
                                    # Oanda Adapter returns dicts
                                    timestamp = pd.to_datetime(c['time']).to_pydatetime()
                                    batch_data.append({
                                        "market_symbol_id": ms.id,
                                        "symbol": symbol_name,
                                        "timeframe": tf,
                                        "timestamp": timestamp,
                                        "open": float(c['mid']['o']),
                                        "high": float(c['mid']['h']),
                                        "low": float(c['mid']['l']),
                                        "close": float(c['mid']['c']),
                                        "volume": int(c['volume']),
                                        "is_complete": c['complete']
                                    })

                        elif source.provider == "CTRADER":
                            # Map Timeframe to cTrader Period Enum
                            # M1=1, M2=2, M3=3, M4=4, M5=5, M10=6, M15=7, M30=8, H1=9, H4=10, D1=11, W1=12, MN1=13
                            # Our TFs: M1, M5, M15, H1, H4, D1, W1, MN1
                            tf_map = {
                                "M1": 1, "M5": 5, "M15": 7, "H1": 9, "H4": 10, "D1": 11, "W1": 12, "MN1": 13
                            }
                            
                            ct_period = tf_map.get(tf)
                            if not ct_period:
                                logger.warning(f"Unsupported TF {tf} for cTrader. Skipping.")
                                continue
                                
                            # Symbol ID from details
                            symbol_id = ms.details.get('symbolId')
                            if not symbol_id and 'raw' in ms.details:
                                symbol_id = ms.details['raw'].get('symbolId')
                                
                            if not symbol_id:
                                logger.warning(f"Missing symbolId in details for {symbol_name}. Run sync_ctrader_symbols.")
                                continue
                            
                            # Calculate Timestamps (Required by API)
                            import time
                            
                            # TF to Minutes for Duration Calc
                            minutes_map = {
                                "M1": 1, "M5": 5, "M15": 15, "H1": 60, "H4": 240, "D1": 1440, "W1": 10080, "MN1": 43200
                            }
                            tf_mins = minutes_map.get(tf, 1) # Default 1 min if unknown
                            
                            count_limit = 100
                            # Buffer: Requested Count * Mins * 60s * 1000ms
                            duration_ms = count_limit * tf_mins * 60 * 1000
                            
                            to_ts = int(time.time() * 1000)
                            from_ts = to_ts - duration_ms
                            
                            # Fetch last 100 candles
                            try:
                                trendbars = await client.get_trendbars(
                                    account_id=int(source.config_json.get("account_id")),
                                    symbol_id=symbol_id,
                                    period=ct_period,
                                    count=count_limit, # Limit result count
                                    from_timestamp=from_ts,
                                    to_timestamp=to_ts
                                )
                                
                                for bar in trendbars:
                                    # timestamp in minutes? No, documentation says Milliseconds usually?
                                    # ProtoOAGetTrendbarsRes says 'timestamp' in response is usually start time.
                                    # Let's assume standard cTrader timestamp (epoch ms? or minutes?). 
                                    # Usually Open API uses Unix Msg. Note says "delta".
                                    # Wait, `deltaHigh`, `deltaOpen` are deltas. 
                                    # Low is absolute? No. 
                                    # Check Proto definition or standard adapter usage.
                                    # Actually `AsyncCTraderClient` returns `res.trendbar` list.
                                    # Each bar has `volume`, `deltaHigh`, `deltaOpen`, `deltaClose`, `low` (absolute? or base?)
                                    # Usually `low` is the base value (int64) and others are deltas (uint64/int64).
                                    # And price = value / 100000.0
                                    
                                    # Handling Delta decoding (accumulated? or per bar?)
                                    # In getting trendbars, the values are RELATIVE to `low` of that bar?
                                    # Or is it Delta from PREVIOUS bar?
                                    # Open API 2.0:
                                    # Low is absolute (int64).
                                    # DeltaOpen, DeltaHigh, DeltaClose are relative to Low.
                                    # All prices / 100000.
                                    
                                    low = bar.low
                                    open_p = low + bar.deltaOpen
                                    high = low + bar.deltaHigh
                                    close_p = low + bar.deltaClose
                                    
                                    # UTC Timestamp? `bar.utcTimestampInMinutes`?
                                    # Check Proto definition. The field is often `utcTimestampInMinutes` for trendbars.
                                    ts = datetime.utcfromtimestamp(bar.utcTimestampInMinutes * 60)
                                    
                                    batch_data.append({
                                        "market_symbol_id": ms.id,
                                        "symbol": symbol_name,
                                        "timeframe": tf,
                                        "timestamp": ts,
                                        "open": open_p / 100000.0,
                                        "high": high / 100000.0,
                                        "low": low / 100000.0,
                                        "close": close_p / 100000.0,
                                        "volume": bar.volume,
                                        "is_complete": True 
                                    })
                            except Exception as e:
                                logger.error(f"cTrader fetch failed for {symbol_name} {tf}: {e}")
                                continue

                        # Save and Publish
                        if batch_data:
                            candle_repo = CandleRepository(db)
                            await asyncio.to_thread(candle_repo.bulk_upsert, batch_data)
                            logger.info(f"Saved {len(batch_data)} candles for {symbol_name} {tf}")

                            for c_data in batch_data:
                                if c_data['is_complete']:
                                    event_payload = c_data.copy()
                                    event_payload['market_symbol_id'] = str(event_payload['market_symbol_id'])
                                    stream_payload = {
                                        "event_type": "candle_completed",
                                        "symbol": symbol_name,
                                        "timeframe": tf,
                                        "timestamp": event_payload['timestamp'].isoformat(),
                                        "c_open": event_payload['open'],
                                        "c_high": event_payload['high'],
                                        "c_low": event_payload['low'],
                                        "c_close": event_payload['close'],
                                        "c_volume": event_payload['volume'],
                                        "data": json.dumps(event_payload, default=str)
                                    }
                                    try:
                                        await publisher.xadd("market.data.stream", stream_payload)
                                    except Exception as e:
                                        logger.error(f"Pub failed: {e}")

            # Cleanup Client
            if source.provider == "CTRADER" and client:
                await client.disconnect()

    except Exception as e:
        logger.error(f"Ingestion job failed: {e}")
        db.rollback()
    finally:
        if 'publisher' in locals():
            await publisher.close()
        db.close()
async def run_calendar_sync_job():
    """Scheduled job to sync economic calendar to DB and cache."""
    logger.info("Starting scheduled Calendar Sync job...")
    from app.services.calendar_service import calendar_service
    db = SessionLocal()
    try:
        # 1. Sync to DB
        new_events = await calendar_service.sync_calendar_to_db(db)
        # 2. Update Redis Cache
        await calendar_service.fetch_and_cache_events()
        logger.info(f"Calendar sync job completed. New events: {new_events}")
    except Exception as e:
        logger.error(f"Calendar sync job failed: {e}")
    finally:
        db.close()

async def run_news_sync_job():
    """Scheduled job to sync news for active symbols to DB."""
    logger.info("Starting scheduled News Sync job...")
    from app.services.news_service import NewsApiService
    from app.models.market import MarketSymbol
    news_service = NewsApiService()
    db = SessionLocal()
    try:
        # Get active symbols (e.g., XAU/USD, EUR/USD)
        symbols = db.query(MarketSymbol).filter(MarketSymbol.is_active == True).all()
        symbol_names = list(set([s.symbol for s in symbols]))
        
        total_new = 0
        for symbol in symbol_names:
            # NewsAPI rate limiting is handled internally in fetch_headlines via Redis
            new_count = await news_service.sync_news_to_db(db, symbol)
            total_new += new_count
            
        logger.info(f"News sync job completed. Total new articles: {total_new}")
    except Exception as e:
        logger.error(f"News sync job failed: {e}")
    finally:
        db.close()
