from app.adapters.oanda import OandaClient
from app.database import SessionLocal
from app.models.candle import Candle
from app.repositories.candle_repository import CandleRepository
from app.repositories.market_repository import MarketRepository
from datetime import datetime, timedelta, timezone
import pandas as pd
import logging
import json
import asyncio
import traceback
from decimal import Decimal, ROUND_HALF_UP
from app.streaming.publisher import RedisPublisher
from app.utils.retry import async_retry
from app.utils.crypto import decrypt_data
from sqlalchemy.dialects.postgresql import insert
import json

def decrypt_and_parse(val):
    if not val: return {}
    
    # If it's already a dict, return it
    if isinstance(val, dict):
        return val
        
    if isinstance(val, str):
        # 1. Try decrypting
        try:
            decrypted = decrypt_data(val)
            if isinstance(decrypted, dict): return decrypted
            # If decrypted is still a string, it might be double-encoded JSON
            if isinstance(decrypted, str):
                try:
                    loaded = json.loads(decrypted)
                    if isinstance(loaded, dict): return loaded
                except:
                    pass
        except Exception:
            # Not an encrypted string or decryption failed
            pass
            
        # 2. Try direct JSON load
        try:
            loaded = json.loads(val)
            if isinstance(loaded, dict):
                return loaded
            # If loaded is still a string, try parsing it again (double-encoded)
            if isinstance(loaded, str):
                try:
                    nested = json.loads(loaded)
                    if isinstance(nested, dict): return nested
                except:
                    pass
        except Exception:
            pass
            
    return {}

def ensure_dict(val):
    return decrypt_and_parse(val)

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
            "from": current_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "count": 2500
        }
        if current_start == from_date:
            kwargs["includeFirst"] = True
        
        try:
            # Call adapter method with broker_symbol if available
            details = ensure_dict(ms.details)
            broker_sym = details.get("broker_symbol") or details.get("symbolName") if details else None
            candles = await fetch_candles_safe(client, symbol=symbol_name, timeframe=tf, broker_symbol=broker_sym, **kwargs)
            
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

async def process_ctrader_backfill(client, source, ms, tf, from_date, to_date, db, logger):
    """Refactored cTrader backfill logic for reuse."""
    tf_map = {
        "M1": 1, "M5": 5, "M15": 7, "H1": 9, "H4": 10, 
        "D1": 12, "W1": 13, "MN1": 14
    }
    ct_period = tf_map.get(tf)
    if not ct_period: return 0
    
    details = ensure_dict(ms.details)
    if not details:
        logger.error(f"Missing details for {ms.symbol} in cTrader backfill.")
        return 0
    symbol_id = details.get('symbol_id') or details.get('symbolId') or details.get('raw', {}).get('symbolId')
    if not symbol_id:
        logger.error(f"Missing symbol_id for {ms.symbol} in cTrader backfill.")
        return 0
    
    from_ts = int(from_date.timestamp() * 1000)
    to_ts = int(to_date.timestamp() * 1000)
    
    logger.info(f"Fetching cTrader candles for {ms.symbol} | TF: {tf} (Period: {ct_period}) | Count: 2000")
    
    config = ensure_dict(source.config_json)
    trendbars = await client.get_trendbars(
        account_id=int(config.get("account_id")),
        symbol_id=symbol_id,
        period=ct_period,
        count=2000,
        from_timestamp=from_ts,
        to_timestamp=to_ts
    )
    
    batch_data = []
    # [SYSTEM OPTIMIZATION]: cTrader Trendbars use a fixed scalar of 100,000
    # regardless of 'digits' for most price fields to maintain proto consistency.
    divisor = 100000.0
    for bar in trendbars:
        low_raw = bar.low
        if bar.deltaOpen > (low_raw * 0.5):
            open_p, high_p, close_p = bar.deltaOpen, bar.deltaHigh, bar.deltaClose
        else:
            open_p, high_p, close_p = low_raw + bar.deltaOpen, low_raw + bar.deltaHigh, low_raw + bar.deltaClose

        batch_data.append({
            "market_symbol_id": ms.id,
            "symbol": ms.symbol,
            "timeframe": tf,
            "timestamp": datetime.fromtimestamp(bar.utcTimestampInMinutes * 60, tz=timezone.utc),
            "open": round(open_p / divisor, 5),
            "high": round(high_p / divisor, 5),
            "low": round(low_raw / divisor, 5),
            "close": round(close_p / divisor, 5),
            "volume": bar.volume,
            "is_complete": True 
        })
    
    if batch_data:
        candle_repo = CandleRepository(db)
        await asyncio.to_thread(candle_repo.bulk_upsert, batch_data)
        return len(batch_data)
    return 0

async def run_ingestion_job(
    symbols: list[str] = None, 
    from_date: datetime = None, 
    to_date: datetime = None,
    target_timeframes: list[str] = None
):
    """
    Scheduled job to fetch and store candles.
    Args:
        symbols: Optional list of symbol names.
        from_date: Start for backfill.
        to_date: End for backfill (defaults to now).
        target_timeframes: Optional list of timeframes to process.
    """
    to_date = to_date or datetime.now(timezone.utc)
    logger.info(f"Starting ingestion job... Symbols: {symbols}, TFs: {target_timeframes}, Range: {from_date} - {to_date}")
    db = SessionLocal()
    
    # Imports inside function to avoid circular deps if any
    from app.models.market import MarketSymbol
    from app.models.data_source import DataSource
    from app.models.system_config import SystemConfig
    from app.models.open_interest import OpenInterest
    
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
    
    # Filter by target_timeframes if provided
    if target_timeframes:
        timeframes = [tf for tf in timeframes if tf in target_timeframes]
    
    try:
        # Diagnostic: Check latest OI entry
        latest_oi = db.query(OpenInterest).order_by(OpenInterest.snapshot_at.desc()).first()
        if latest_oi:
            logger.info(f"DIAGNOSTIC: Latest OI Snapshot in DB: {latest_oi.snapshot_at} (Created: {latest_oi.created_at})")
        else:
            logger.warning("DIAGNOSTIC: No OI data found in DB")

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
                config = decrypt_and_parse(source.config_json)
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
                
            # 3. Parallel Processing of Symbols & Timeframes
            semaphore = asyncio.Semaphore(10) # Limit concurrent tasks
            
            async def process_ms_tf(ms, tf):
                async with semaphore:
                    # Create a local session for this task to avoid sharing DB session across tasks
                    task_db = SessionLocal()
                    try:
                        symbol_name = ms.symbol
                        batch_data = []
                        
                        if from_date and to_date:
                            # EXPLICIT BACKFILL LOGIC
                            if source.provider == "OANDA":
                                 await process_oanda_backfill(client, ms, tf, from_date, to_date, task_db, logger)
                            elif source.provider == "CTRADER":
                                await process_ctrader_backfill(client, source, ms, tf, from_date, to_date, task_db, logger)
                        else:
                            # SMART CATCHUP / REAL-TIME
                            # 1. Determine local last candle
                            candle_repo = CandleRepository(task_db)
                            latest_candle = await asyncio.to_thread(candle_repo.get_latest_candle, ms.id, tf)
                            
                            # Define lookback window (default 100 units if empty)
                            catchup_start = from_date
                            if not catchup_start:
                                if latest_candle:
                                    catchup_start = latest_candle.timestamp
                                else:
                                    # Full reset or fresh symbol: seed with 7 days
                                    catchup_start = datetime.now(timezone.utc) - timedelta(days=7)

                            # If catchup is needed (> 1 candle interval + buffer)
                            interval_map = {
                                "M1": 1, "M5": 5, "M15": 15, "H1": 60, "H4": 240, 
                                "D1": 1440, "W1": 10080, "MN1": 43200
                            }
                            mins = interval_map.get(tf, 1440)
                            
                            catchup_performed = False
                            if (datetime.now(timezone.utc) - catchup_start).total_seconds() > (mins * 60 * 1.5):
                                logger.info(f"CATCH-UP REQUIRED: {ms.symbol} {tf} from {catchup_start}")
                                if source.provider == "OANDA":
                                    await process_oanda_backfill(client, ms, tf, catchup_start, datetime.now(timezone.utc), task_db, logger)
                                    catchup_performed = True
                                elif source.provider == "CTRADER":
                                    count = await process_ctrader_backfill(client, source, ms, tf, catchup_start, datetime.now(timezone.utc), task_db, logger)
                                    if count > 0:
                                        catchup_performed = True

                            # 2. Regular Real-time Catchup (Only if not already caught up via backfill)
                            if not catchup_performed:
                                if source.provider == "OANDA":
                                    details = ensure_dict(ms.details)
                                    broker_sym = details.get("broker_symbol") or details.get("symbolName") if details else None
                                    candles = await asyncio.to_thread(client.fetch_candles, symbol_name, tf, count=20, broker_symbol=broker_sym)
                                    if candles:
                                        for c in candles:
                                            timestamp = pd.to_datetime(c['time']).to_pydatetime()
                                            if timestamp.tzinfo is None:
                                                timestamp = timestamp.replace(tzinfo=timezone.utc)
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
                                    # Supports both full (D1, W1, MN1) and short (D, W, M) formats
                                    tf_map = {
                                        "M1": 1, "M5": 5, "M15": 7, "H1": 9, "H4": 10, 
                                        "D1": 12, "D": 12, "W1": 13, "W": 13, "MN1": 14, "M": 14
                                    }
                                    ct_period = tf_map.get(tf)
                                    if not ct_period: 
                                        logger.warning(f"Unsupported TF {tf} for cTrader. Skipping.")
                                        return
                                    
                                    details = ensure_dict(ms.details)
                                    if not details:
                                        logger.error(f"Missing details for {ms.symbol} in cTrader real-time catchup.")
                                        return
                                    symbol_id = details.get('symbol_id') or details.get('symbolId') or details.get('raw', {}).get('symbolId')
                                    if not symbol_id:
                                        logger.error(f"Missing symbol_id for {ms.symbol} in cTrader real-time catchup.")
                                        return
                                    
                                    minutes_map = {
                                        "M1": 1, "M5": 5, "M15": 15, "H1": 60, "H4": 240, 
                                        "D1": 1440, "D": 1440, "W1": 10080, "W": 10080, "MN1": 43200, "M": 43200
                                    }
                                    tf_mins = minutes_map.get(tf, 1)
                                    count_limit = 20 # Reduced from 100 for optimization
                                    duration_ms = count_limit * tf_mins * 60 * 1000
                                    to_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
                                    from_ts = to_ts - duration_ms
                                    
                                    # logger.debug(f"Fetching cTrader candles for {symbol_name} | TF: {tf} (Period: {ct_period}) | Count: {count_limit}")
                                    
                                    config = ensure_dict(source.config_json)
                                    trendbars = await client.get_trendbars(
                                        account_id=int(config.get("account_id")),
                                        symbol_id=symbol_id,
                                        period=ct_period,
                                        count=count_limit,
                                        from_timestamp=from_ts,
                                        to_timestamp=to_ts
                                    )
                                    
                                    if len(trendbars) > 0:
                                        # logger.debug(f"Received {len(trendbars)} bars for {symbol_name} {tf}")
                                        pass
                                    else:
                                        # logger.warning(f"No bars returned for {symbol_name} {tf} (Period: {ct_period}, Range: {from_ts}-{to_ts})")
                                        pass

                                    for bar in trendbars:
                                        # cTrader V2 Trendbars: Open/High/Close are deltas relative to Low.
                                        # BUG: Some broker feeds (or message sequences) send ABSOLUTE values in delta fields.
                                        # Heuristic: If delta is suspicious (e.g. > 50% of low), treat as absolute.
                                        low_raw = bar.low
                                        
                                        # [SYSTEM OPTIMIZATION]: cTrader Trendbars use a fixed scalar of 100,000
                                        # regardless of 'digits' for most price fields to maintain proto consistency.
                                        divisor = 100000.0
                                        open_delta = bar.deltaOpen
                                        high_delta = bar.deltaHigh
                                        close_delta = bar.deltaClose
                                        
                                        # If any delta is suspiciously large (> 50% of low), the feed is sending absolute values.
                                        if open_delta > (low_raw * 0.5):
                                            open_p = open_delta
                                            high_p = high_delta
                                            close_p = close_delta
                                        else:
                                            open_p = low_raw + open_delta
                                            high_p = low_raw + high_delta
                                            close_p = low_raw + close_delta

                                        open_p_norm = round(open_p / divisor, 5)
                                        high_p_norm = round(high_p / divisor, 5)
                                        low_p_norm = round(low_raw / divisor, 5)
                                        close_p_norm = round(close_p / divisor, 5)

                                        batch_data.append({
                                            "market_symbol_id": ms.id,
                                            "symbol": symbol_name,
                                            "timeframe": tf,
                                            "timestamp": datetime.fromtimestamp(bar.utcTimestampInMinutes * 60, tz=timezone.utc),
                                            "open": open_p_norm,
                                            "high": high_p_norm,
                                            "low": low_p_norm,
                                            "close": close_p_norm,
                                            "volume": bar.volume,
                                            "is_complete": True 
                                        })

                        # Save and Publish
                        if batch_data:
                            candle_repo = CandleRepository(task_db)
                            await asyncio.to_thread(candle_repo.bulk_upsert, batch_data)
                            
                            # Publish to stream and Update Cache
                            new_complete_candles = [c for c in batch_data if c['is_complete']]
                            
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
                                    await publisher.xadd("market.data.stream", stream_payload)
                            
                            # [OPTIMIZATION]: Only update Redis Cache if we have new complete candles
                            should_update_cache = len(new_complete_candles) > 0
                            
                            if should_update_cache:
                                try:
                                    from app.models.candle import Candle as CandleModel
                                    from sqlalchemy import desc
                                    
                                    # Limit DB query for cache to what is strictly necessary
                                    latest_candles = task_db.query(CandleModel).filter(
                                        CandleModel.market_symbol_id == ms.id,
                                        CandleModel.timeframe == tf
                                    ).order_by(desc(CandleModel.timestamp)).limit(500).all()
                                    
                                    if latest_candles:
                                        cache_data = []
                                        for c in reversed(latest_candles): 
                                            cache_data.append({
                                                "timestamp": c.timestamp.isoformat(),
                                                "open": float(c.open),
                                                "high": float(c.high),
                                                "low": float(c.low),
                                                "close": float(c.close),
                                                "volume": float(c.volume)
                                            })
                                        
                                        cache_key = f"market_data:candles:{ms.symbol}:{tf}"
                                        await publisher.redis.set(cache_key, json.dumps(cache_data))
                                except Exception as cache_ex:
                                    logger.warning(f"Failed to update Redis cache for {ms.symbol} {tf}: {cache_ex}")
                    except Exception as ex:
                        logger.error(f"Failed to process {ms.symbol} {tf}: {ex}")
                    finally:
                        task_db.close()

            # 3. Processing of Symbols & Timeframes
            if source.provider in ["CTRADER", "OANDA"]:
                # Sequential processing for cTrader and OANDA to avoid REQUEST_FREQUENCY_EXCEEDED or Cloudflare blocking
                for ms in source_symbols:
                    for tf in timeframes:
                        await process_ms_tf(ms, tf)
            else:
                # Parallel processing for others
                ingest_tasks = []
                for ms in source_symbols:
                    for tf in timeframes:
                        ingest_tasks.append(process_ms_tf(ms, tf))
                
                if ingest_tasks:
                    await asyncio.gather(*ingest_tasks)

            # Cleanup Client
            if source.provider == "CTRADER" and client:
                await client.disconnect()

    except Exception as e:
        logger.error(f"Ingestion job failed: {e}")
        logger.error(traceback.format_exc())
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
        await calendar_service.close()
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
        
        # Parallel news sync
        semaphore = asyncio.Semaphore(5)
        async def sync_symbol_news(symbol):
            async with semaphore:
                # Create a local session for each task
                task_db = SessionLocal()
                try:
                    return await news_service.sync_news_to_db(task_db, symbol)
                finally:
                    task_db.close()

        tasks = [sync_symbol_news(s) for s in symbol_names]
        results = await asyncio.gather(*tasks)
        total_new = sum(results)
            
        logger.info(f"News sync job completed. Total new articles: {total_new}")
    except Exception as e:
        logger.error(f"News sync job failed: {e}")
    finally:
        await news_service.close()
        db.close()

async def run_trade_sync_job():
    """Scheduled job to sync trade history from brokers (cTrader) and publish events."""
    logger.info("Starting scheduled Trade Sync job...")
    db = SessionLocal()
    publisher = RedisPublisher()
    
    try:
        await publisher.connect()
        
        # 1. Get Active Broker Accounts
        from app.models import BrokerAccount, Trade
        from app.adapters.ctrader import CTraderClient
        from sqlalchemy import func
        
        accounts = db.query(BrokerAccount).filter(BrokerAccount.is_active == True).all()
        logger.info(f"Found {len(accounts)} active broker accounts.")
        
        for account in accounts:
            if account.broker_name != "CTRADER":
                continue
                
            try:
                # Decrypt Credentials
                creds = decrypt_data(account.credentials_encrypted)
                
                # Determine Host based on Environment
                env_str = str(account.environment).lower() if account.environment else "demo"
                host = "live.ctraderapi.com" if env_str in ["live", "production", "real"] else "demo.ctraderapi.com"
                
                # Instantiate Adapter with Account-Specific Creds
                client_adapter = CTraderClient(
                    client_id=creds.get("client_id"),
                    client_secret=creds.get("client_secret"),
                    account_id=creds.get("account_id"),
                    token=creds.get("token"),
                    host=host,
                    port=int(creds.get("port", 5035))
                )
                
                # Range: Dynamic scan based on latest DB entry
                end_date = datetime.utcnow()
                
                # Query latest trade for this account to optimize polling
                latest_exit = db.query(func.max(Trade.exit_timestamp)).filter(Trade.broker_account_id == account.id).scalar()
                
                if latest_exit:
                    # Polling from latest entry minus 2 hours buffer for late arrivals
                    start_date = latest_exit - timedelta(hours=2)
                    logger.info(f"Optimized sync window for {account.id}: Starting from {start_date} (Latest DB: {latest_exit})")
                else:
                    start_date = end_date - timedelta(days=30)
                    logger.info(f"Full sync window for {account.id}: Starting from {start_date} (No history found)")
                
                trades = await client_adapter.fetch_trade_history(start_date, end_date)
                logger.info(f"Fetched {len(trades)} trades from cTrader adapter.")
                
                new_event_count = 0
                
                for t_data in trades:
                    import uuid
                    db_trade_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"{account.id}_{t_data['trade_id']}")
                    
                    # Use PostgreSQL UPSERT (ON CONFLICT DO UPDATE)
                    stmt = insert(Trade).values(
                        trade_id=db_trade_id,
                        broker_account_id=account.id,
                        broker_trade_id=t_data.get("broker_trade_id"),
                        broker_deal_id=t_data.get("broker_deal_id"),
                        symbol=t_data["symbol"],
                        strategy_name=t_data["strategy_name"],
                        signal_timestamp=t_data["signal_timestamp"],
                        status=t_data["status"],
                        direction=t_data["direction"],
                        entry_price=t_data["entry_price"],
                        exit_price=t_data["exit_price"],
                        sl_price=t_data["sl_price"],
                        tp_price=t_data["tp_price"],
                        lot_size=t_data["lot_size"],
                        risk_usd=t_data["risk_usd"],
                        commission=t_data.get("commission"),
                        swap=t_data.get("swap"),
                        gross_pnl=t_data.get("gross_pnl"),
                        pnl_usd=t_data["pnl_usd"],
                        exit_timestamp=t_data["exit_timestamp"],
                        metadata_json=t_data["metadata_json"],
                        updated_at=datetime.utcnow()
                    )
                    
                    # Update all fields on conflict
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['trade_id'],
                        set_={
                            "exit_price": stmt.excluded.exit_price,
                            "pnl_usd": stmt.excluded.pnl_usd,
                            "commission": stmt.excluded.commission,
                            "swap": stmt.excluded.swap,
                            "gross_pnl": stmt.excluded.gross_pnl,
                            "exit_timestamp": stmt.excluded.exit_timestamp,
                            "metadata_json": stmt.excluded.metadata_json,
                            "updated_at": stmt.excluded.updated_at
                        }
                    )
                    
                    res = db.execute(stmt)
                    if res.rowcount > 0:
                        new_event_count += 1
                        
                        # PUBLISH EVENT via STREAM
                        stream_payload = {
                            "event_type": "trade_closed",
                            "account_id": str(account.id),
                            "trade_id": str(db_trade_id),
                            "broker_trade_id": str(t_data.get("broker_trade_id")),
                            "broker_deal_id": str(t_data.get("broker_deal_id")),
                            "symbol": t_data["symbol"],
                            "commission": str(t_data.get("commission") or 0.0),
                            "swap": str(t_data.get("swap") or 0.0),
                            "gross_pnl": str(t_data.get("gross_pnl") or 0.0),
                            "pnl": str(t_data["pnl_usd"] or 0.0),
                            "close_time": t_data["exit_timestamp"].isoformat() if t_data["exit_timestamp"].tzinfo else t_data["exit_timestamp"].replace(tzinfo=timezone.utc).isoformat(),
                            "direction": t_data["direction"],
                            "lot_size": str(t_data["lot_size"])
                        }
                        await publisher.xadd("market.trade.stream", stream_payload)
                
                if len(trades) > 0:
                    db.commit()
                    logger.info(f"Synced {len(trades)} trades for account {account.id}, {new_event_count} events published.")
                else:
                    db.rollback() # Nothing to save
                
            except Exception as e:
                logger.error(f"Failed to sync account {account.id}: {e}")
                db.rollback()
                continue
                
    except Exception as e:
        logger.error(f"Trade sync job failed: {e}")
    finally:
        await publisher.close()
        db.close()

async def run_macro_sync_job():
    """Scheduled job to fetch Macro Indicators (DXY, VIX, GVZ) from yfinance and push to Redis."""
    logger.info("Starting scheduled Macro Sync job...")
    try:
        from app.adapters.yfinance_adapter import yfinance_adapter
        from app.streaming.publisher import RedisPublisher
        
        publisher = RedisPublisher()
        await publisher.connect()
        
        await yfinance_adapter.sync_all_macro(publisher)
        
        await publisher.close()
        logger.info("Macro sync job completed successfully.")
        
    except Exception as e:
        logger.error(f"Macro sync job failed: {e}")
        logger.error(f"GVZ sync job failed: {e}")

async def run_broker_sync_job():
    """Wrapper for Broker Sync (Phase 47)."""
    try:
        from app.services.sync_service import sync_service
        await sync_service.run_broker_sync()
    except Exception as e:
        logger.error(f"Broker Sync job failed: {e}")

async def run_cot_sync_job():
    """Scheduled job to fetch and store COT reports from CFTC."""
    logger.info("Starting scheduled COT Sync job...")
    from app.services.cot_service import cot_service
    import aiohttp
    
    url = "https://www.cftc.gov/dea/newcot/f_disagg.txt"
    db = SessionLocal()
    try:
        async with aiohttp.ClientSession() as session:
            logger.info(f"Fetching COT data from {url}")
            async with session.get(url, timeout=30.0) as response:
                logger.info(f"COT Response Status: {response.status}")
                response.raise_for_status()
                content = await response.read()
                logger.info(f"COT Content Received: {len(content)} bytes")
                
                # Using Gold as default symbol for this job
                # The parser handles filtering for 'GOLD - COMMODITY EXCHANGE INC.'
                records = await asyncio.to_thread(cot_service.parse_and_store, content, db, symbol="GOLD")
                logger.info(f"COT sync job completed. Processed {len(records)} records for GOLD. Status: {records.get('status')}")
            
    except Exception as e:
        logger.error(f"COT sync job failed: {e}")
    finally:
        db.close()

async def run_search_sync_job():
    """Scheduled job to sync market context via Google Search (SerpApi)."""
    logger.info("Starting scheduled Search Sync job...")
    from app.services.serpapi_service import SerpApiService
    from app.models.market import MarketSymbol
    
    search_service = SerpApiService()
    db = SessionLocal()
    try:
        # Get active symbols (e.g., XAU/USD, EUR/USD)
        symbols = db.query(MarketSymbol).filter(MarketSymbol.is_active == True).all()
        symbol_names = list(set([s.symbol for s in symbols]))
        
        # Parallel search sync
        semaphore = asyncio.Semaphore(3) # SerpApi rate limits might be strict
        async def sync_symbol_search(symbol):
            async with semaphore:
                # We normalize symbol to remove slashes if any for query, e.g. XAU/USD -> XAUUSD
                normalized_symbol = symbol.replace("/", "")
                return await search_service.fetch_and_cache_market_context(normalized_symbol)

        tasks = [sync_symbol_search(s) for s in symbol_names]
        results = await asyncio.gather(*tasks)
            
        logger.info(f"Search sync job completed. Synced {len(results)} symbols.")
    except Exception as e:
        logger.error(f"Search sync job failed: {e}")
    finally:
        await search_service.close()
        db.close()
