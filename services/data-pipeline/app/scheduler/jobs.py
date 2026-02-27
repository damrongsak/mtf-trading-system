from app.adapters.oanda import OandaClient
from app.database import SessionLocal
from app.models.candle import Candle
from app.repositories.candle_repository import CandleRepository
from app.repositories.market_repository import MarketRepository
from datetime import datetime, timedelta
import pandas as pd
import logging
import json
import asyncio
from app.streaming.publisher import RedisPublisher
from app.utils.retry import async_retry
from app.utils.crypto import decrypt_data
from sqlalchemy.dialects.postgresql import insert

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
                            # BACKFILL LOGIC
                            if source.provider == "OANDA":
                                 await process_oanda_backfill(client, ms, tf, from_date, to_date, task_db, logger)
                            elif source.provider == "CTRADER":
                                # cTrader Backfill using get_trendbars
                                tf_map = {
                                    "M1": 1, "M5": 5, "M15": 7, "H1": 9, "H4": 10, 
                                    "D1": 12, "W1": 13, "MN1": 14
                                }
                                ct_period = tf_map.get(tf)
                                if not ct_period: return
                                
                                symbol_id = ms.details.get('symbolId') or ms.details.get('raw', {}).get('symbolId')
                                if not symbol_id: return
                                
                                from_ts = int(from_date.timestamp() * 1000)
                                to_ts = int(to_date.timestamp() * 1000)
                                
                                logger.info(f"Triggering cTrader backfill for {ms.symbol} {tf} from {from_date} to {to_date}")
                                
                                trendbars = await client.get_trendbars(
                                    account_id=int(source.config_json.get("account_id")),
                                    symbol_id=symbol_id,
                                    period=ct_period,
                                    count=2000, # Max allowed usually
                                    from_timestamp=from_ts,
                                    to_timestamp=to_ts
                                )
                                
                                for bar in trendbars:
                                    low_raw = bar.low
                                    # [SYSTEM OPTIMIZATION]: cTrader Trendbars use a fixed scalar of 100,000
                                    divisor = 100000.0
                                    
                                    # Delta handling logic (same as real-time)
                                    if bar.deltaOpen > (low_raw * 0.5):
                                        open_p, high_p, close_p = bar.deltaOpen, bar.deltaHigh, bar.deltaClose
                                    else:
                                        open_p, high_p, close_p = low_raw + bar.deltaOpen, low_raw + bar.deltaHigh, low_raw + bar.deltaClose

                                    batch_data.append({
                                        "market_symbol_id": ms.id,
                                        "symbol": ms.symbol,
                                        "timeframe": tf,
                                        "timestamp": datetime.fromtimestamp(bar.utcTimestampInMinutes * 60),
                                        "open": open_p / divisor,
                                        "high": high_p / divisor,
                                        "low": low_raw / divisor,
                                        "close": close_p / divisor,
                                        "volume": bar.volume,
                                        "is_complete": True 
                                    })
                        else:
                            # REAL-TIME CATCHUP
                            if source.provider == "OANDA":
                                candles = await asyncio.to_thread(client.fetch_candles, symbol_name, tf, count=100)
                                if candles:
                                    for c in candles:
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
                                # Supports both full (D1, W1, MN1) and short (D, W, M) formats
                                tf_map = {
                                    "M1": 1, "M5": 5, "M15": 7, "H1": 9, "H4": 10, 
                                    "D1": 12, "D": 12, "W1": 13, "W": 13, "MN1": 14, "M": 14
                                }
                                ct_period = tf_map.get(tf)
                                if not ct_period: 
                                    logger.warning(f"Unsupported TF {tf} for cTrader. Skipping.")
                                    return
                                
                                symbol_id = ms.details.get('symbolId') or ms.details.get('raw', {}).get('symbolId')
                                if not symbol_id: return
                                
                                import time
                                minutes_map = {
                                    "M1": 1, "M5": 5, "M15": 15, "H1": 60, "H4": 240, 
                                    "D1": 1440, "D": 1440, "W1": 10080, "W": 10080, "MN1": 43200, "M": 43200
                                }
                                tf_mins = minutes_map.get(tf, 1)
                                count_limit = 100
                                duration_ms = count_limit * tf_mins * 60 * 1000
                                to_ts = int(time.time() * 1000)
                                from_ts = to_ts - duration_ms
                                
                                trendbars = await client.get_trendbars(
                                    account_id=int(source.config_json.get("account_id")),
                                    symbol_id=symbol_id,
                                    period=ct_period,
                                    count=count_limit,
                                    from_timestamp=from_ts,
                                    to_timestamp=to_ts
                                )
                                
                                if len(trendbars) > 0:
                                    logger.info(f"Received {len(trendbars)} bars for {symbol_name} {tf}")
                                else:
                                    logger.warning(f"No bars returned for {symbol_name} {tf} (Period: {ct_period}, Range: {from_ts}-{to_ts})")

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

                                    open_p_norm = open_p / divisor
                                    high_p_norm = high_p / divisor
                                    low_p_norm = low_raw / divisor
                                    close_p_norm = close_p / divisor

                                    # cTrader Gold Quirk: Some feeds (e.g. IC Markets etc) send doubled price (likely Bid+Ask aggregate or scaling issue).
                                    # If the price is > 3500 for Gold from CTRADER source, it's likely doubled.
                                    # This is an anomaly detection threshold, not a fixed target.
                                    # [USER CORRECTION]: Gold price is ~5000 in 2026. Do not normalize.
                                    # if source.provider == "CTRADER" and symbol_name == 'XAUUSD' and close_p_norm > 3500:
                                    #    open_p_norm /= 2.0
                                    #    high_p_norm /= 2.0
                                    #    low_p_norm /= 2.0
                                    #    close_p_norm /= 2.0
                                    #    if bar == trendbars[0]:
                                    #        logger.info(f"NORMALIZATION [CTRADER/XAUUSD]: Detected doubled price in close ({close_p_norm * 2.0:.2f}). Applied 2x divisor. Final: {close_p_norm:.2f}")

                                    batch_data.append({
                                        "market_symbol_id": ms.id,
                                        "symbol": symbol_name,
                                        "timeframe": tf,
                                        "timestamp": datetime.utcfromtimestamp(bar.utcTimestampInMinutes * 60),
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
                            # ... publish to stream ...
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
                    except Exception as ex:
                        logger.error(f"Failed to process {ms.symbol} {tf}: {ex}")
                    finally:
                        task_db.close()

            # 3. Processing of Symbols & Timeframes
            if source.provider == "CTRADER":
                # Sequential processing for cTrader to avoid REQUEST_FREQUENCY_EXCEEDED
                for ms in source_symbols:
                    for tf in timeframes:
                        await process_ms_tf(ms, tf)
            else:
                # Parallel processing for others (e.g. OANDA)
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
        from app.models.execution import BrokerAccount, Trade
        from app.adapters.ctrader import CTraderClient
        
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
                
                # Range: Scan last 30 days for regular maintenance.
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=30)
                
                logger.info(f"Syncing trade history for account {account.id} ({start_date} - {end_date})")
                
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
                        index_elements=['broker_deal_id'],
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
                            "close_time": t_data["exit_timestamp"].isoformat(),
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

async def run_gvz_sync_job():
    """Scheduled job to fetch Gold Volatility Index (^GVZ) from yfinance and push to Redis."""
    logger.info("Starting scheduled GVZ Sync job...")
    try:
        import yfinance as yf
        from app.streaming.publisher import RedisPublisher
        
        # Period: 1d to get the most recent daily close
        gvz = yf.Ticker("^GVZ")
        hist = gvz.history(period="1d")
        
        if hist.empty:
            logger.warning("No GVZ data found from yfinance.")
            return

        latest_value = float(hist['Close'].iloc[-1])
        timestamp = str(hist.index[-1].isoformat())
        
        payload = {
            "symbol": "^GVZ",
            "value": latest_value,
            "timestamp": timestamp,
            "updated_at": datetime.now().isoformat()
        }
        
        publisher = RedisPublisher()
        await publisher.connect()
        # Key: market_data:gvz (used by strategy-core as projected volatility input)
        await publisher.redis.set("market_data:gvz", json.dumps(payload))
        await publisher.close()
        
        logger.info(f"GVZ sync job completed: {latest_value} at {timestamp}")
        
    except Exception as e:
        logger.error(f"GVZ sync job failed: {e}")

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
                response.raise_for_status()
                content = await response.read()
                
                # Using Gold as default symbol for this job
                # The parser handles filtering for 'GOLD - COMMODITY EXCHANGE INC.'
                records = await asyncio.to_thread(cot_service.parse_and_store, content, db, symbol="GOLD")
                logger.info(f"COT sync job completed. Processed {len(records)} records for GOLD.")
            
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
