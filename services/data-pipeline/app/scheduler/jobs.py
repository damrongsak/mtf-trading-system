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

import logging
import json
import asyncio
from datetime import timedelta
from sqlalchemy.dialects.postgresql import insert
from app.streaming.publisher import RedisPublisher
from app.utils.retry import async_retry
from app.utils.crypto import decrypt_data

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
                                 pass # Implement if needed
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
                                    "D1": 11, "D": 11, "W1": 12, "W": 12, "MN1": 13, "M": 13
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
                                for bar in trendbars:
                                    low = bar.low
                                    batch_data.append({
                                        "market_symbol_id": ms.id,
                                        "symbol": symbol_name,
                                        "timeframe": tf,
                                        "timestamp": datetime.utcfromtimestamp(bar.utcTimestampInMinutes * 60),
                                        "open": (low + bar.deltaOpen) / 100000.0,
                                        "high": (low + bar.deltaHigh) / 100000.0,
                                        "low": low / 100000.0,
                                        "close": (low + bar.deltaClose) / 100000.0,
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
                
                # Range: Last 24h to maintain hydration? Or last sync check?
                # For safety, lookback 1 day. Duplicates handled by DB.
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=1)
                
                logger.info(f"Syncing trades for account {account.id} ({start_date} - {end_date})")
                
                trades = await client_adapter.fetch_trade_history(start_date, end_date)
                
                new_event_count = 0
                
                for t_data in trades:
                    # Upsert to DB
                    # We need a deterministic UUID for the Trade record itself if we want to store it.
                    # Trade model has `trade_id` (PK).
                    # t_data has `trade_id` (Deal ID).
                    import uuid
                    # Create determinstic UUID for our DB
                    db_trade_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"{account.id}_{t_data['trade_id']}")
                    
                    # Check if exists to avoid re-publishing old events?
                    # Or upsert and check 'created_at' or 'updated_at'?
                    # Simpler: query existing.
                    existing = db.query(Trade).filter(Trade.trade_id == db_trade_id).first()
                    is_new = existing is None
                    
                    if is_new:
                        # Map to Model
                        new_trade = Trade(
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
                            metadata_json=t_data["metadata_json"]
                        )
                        db.add(new_trade)
                        new_event_count += 1
                        
                        # PUBLISH EVENT via STREAM (Persistence)
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
                            "pnl": str(t_data["pnl_usd"] or 0.0), # XADD needs strings
                            "close_time": t_data["exit_timestamp"].isoformat(),
                            "direction": t_data["direction"],
                            "lot_size": str(t_data["lot_size"])
                        }
                        await publisher.xadd("market.trade.stream", stream_payload)
                
                if new_event_count > 0:
                    db.commit()
                    logger.info(f"Synced {len(trades)} trades, {new_event_count} new events published.")
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
