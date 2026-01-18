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

async def process_oanda_backfill(client, ms, tf, from_date, to_date, db, logger):
    current_start = from_date
    total_saved = 0
    symbol_name = ms.symbol
    
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
                
            candle_repo = CandleRepository(db)
            await asyncio.to_thread(candle_repo.bulk_upsert, batch_data)
            
            total_saved += len(batch_data)
            
            last_ts = batch_data[-1]["timestamp"]
            if last_ts >= to_date or len(candles) < 2500:
                break
                
            current_start = last_ts
            
        except Exception as e:
            logger.error(f"Batch failed: {e}")
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
    default_timeframes = ["M1", "M5", "M15", "H1", "H4", "D", "W", "M"]
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
                            # Use get_candles or equivalent
                            # We need to map timeframe to cTrader enum
                            # And fetch.
                            # Assuming client has helper or we allow it.
                            # cTrader client in data-pipeline does NOT have fetch_candles helper yet?
                            # Check adapter.
                            pass

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
