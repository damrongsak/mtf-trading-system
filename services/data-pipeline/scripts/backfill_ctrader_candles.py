
import asyncio
import logging
import sys
import os
import time
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Boolean, Text

# Ensure app is in path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal, Base
from app.models.market import MarketSymbol
from app.models.data_source import DataSource
from app.models.candle import Candle
from app.models.broker_account import BrokerAccount
from app.utils.crypto import decrypt_data, encrypt_data
from app.adapters.ctrader_client import AsyncCTraderClient
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOATrendbarPeriod

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("CandleBackfill")

# Map our timeframe strings to cTrader ProtoOATrendbarPeriod
TIMEFRAME_MAP = {
    "M1": ProtoOATrendbarPeriod.M1,
    "M5": ProtoOATrendbarPeriod.M5,
    "M15": ProtoOATrendbarPeriod.M15,
    "H1": ProtoOATrendbarPeriod.H1,
    "H4": ProtoOATrendbarPeriod.H4,
    "D1": ProtoOATrendbarPeriod.D1,
    "W1": ProtoOATrendbarPeriod.W1,
    "MN1": ProtoOATrendbarPeriod.MN1,
}

async def backfill_candles(days: int = 30):
    # Sync DB session
    db = SessionLocal()
    
    try:
        # 1. Find cTrader Account
        logger.info("Locating cTrader account...")
        account = db.query(BrokerAccount).filter(BrokerAccount.broker_name == "CTRADER", BrokerAccount.is_active == True).first()
        
        credentials = {}
        if not account:
            logger.info("Account with name 'CTRADER' not found. Searching all active accounts...")
            all_accounts = db.query(BrokerAccount).filter(BrokerAccount.is_active == True).all()
            for acc in all_accounts:
                try:
                    creds = decrypt_data(acc.credentials_encrypted)
                    if "client_id" in creds or "app_id" in creds:
                        account = acc
                        credentials = creds
                        logger.info(f"Found cTrader account in DB: {acc.broker_name} ({acc.id})")
                        break
                except: continue

        if account and not credentials:
            try:
                credentials = decrypt_data(account.credentials_encrypted)
            except Exception as e:
                logger.error(f"Failed to decrypt credentials for {account.broker_name}: {e}")

        # 2. Fallback to Environment Variables
        client_id = credentials.get("client_id") or credentials.get("app_id") or os.getenv("CTRADER_CLIENT_ID")
        client_secret = credentials.get("client_secret") or credentials.get("secret") or os.getenv("CTRADER_CLIENT_SECRET")
        account_id = credentials.get("account_id") or os.getenv("CTRADER_ACCOUNT_ID")
        token = credentials.get("token") or os.getenv("CTRADER_TOKEN")
        
        if not all([client_id, client_secret, account_id, token]):
            logger.error(f"Missing cTrader credentials.")
            return

        env = (account.environment.lower() if account and account.environment else os.getenv("CTRADER_ENV", "demo")).lower()
        host = "live.ctraderapi.com" if env in ["live", "production"] else "demo.ctraderapi.com"
        port = 5035
        
        logger.info(f"Using cTrader Account: {account_id} on {host}")

        # 3. Target Symbols (Fetch from DB)
        ds = db.query(DataSource).filter(DataSource.name == "CTRADER", DataSource.is_active == True).first()
        if not ds:
            logger.error("CTRADER Data Source not found")
            return

        active_symbols = db.query(MarketSymbol).filter(
            MarketSymbol.data_source_id == ds.id, 
            MarketSymbol.is_active == True
        ).all()

        if not active_symbols:
            logger.warning("No active cTrader symbols found.")
            return

        divisor = 100000.0
        end_ts = int(time.time() * 1000)
        start_ts = end_ts - (days * 24 * 60 * 60 * 1000)

        # Connection management wrapper
        client = None

        async def get_connected_client():
            nonlocal client
            if client and client._connected:
                return client
            
            if client:
                try: await client.disconnect()
                except: pass
            
            client = AsyncCTraderClient(host, port)
            await client.connect()
            await client.authorize_app(client_id, client_secret)
            await client.authorize_account(account_id, token)
            return client

        for ms in active_symbols:
            sym_name = ms.symbol
            logger.info(f"Processing symbol: {sym_name}")
            
            symbol_id = ms.details.get('symbolId')
            if not symbol_id and 'raw' in ms.details:
                symbol_id = ms.details['raw'].get('symbolId')
            
            if not symbol_id: continue

            for tf_name, tf_enum in TIMEFRAME_MAP.items():
                if tf_name == 'T15': continue
                
                logger.info(f"  Timeframe: {tf_name}")
                current_to_ts = end_ts
                total_saved = 0
                
                while current_to_ts > start_ts:
                    try:
                        c = await get_connected_client()
                        req_count = 2000 
                        trendbars = await c.get_trendbars(
                            account_id=account_id,
                            symbol_id=symbol_id,
                            period=tf_enum,
                            count=req_count,
                            from_timestamp=start_ts,
                            to_timestamp=current_to_ts
                        )
                        
                        if not trendbars:
                            break
                        
                        candles_to_save = []
                        earliest_bar_ts = current_to_ts
                        
                        for bar in trendbars:
                            bar_ts = bar.utcTimestampInMinutes * 60 * 1000
                            if bar_ts < earliest_bar_ts:
                                earliest_bar_ts = bar_ts
                            
                            if bar_ts < start_ts: continue
                                
                            low = bar.low
                            candles_to_save.append({
                                "market_symbol_id": ms.id,
                                "symbol": ms.symbol,
                                "timeframe": tf_name,
                                "timestamp": datetime.fromtimestamp(bar_ts / 1000.0, timezone.utc),
                                "open": (low + bar.deltaOpen) / divisor,
                                "high": (low + bar.deltaHigh) / divisor,
                                "low": low / divisor,
                                "close": (low + bar.deltaClose) / divisor,
                                "volume": bar.volume
                            })

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
                            logger.info(f"    Saved {count} candles. Total: {total_saved}. Earliest: {datetime.fromtimestamp(earliest_bar_ts/1000)}")
                        
                        if earliest_bar_ts >= current_to_ts:
                            break
                        current_to_ts = earliest_bar_ts - 1
                        
                        if len(trendbars) < 100: # Heuristic for end of data
                            break
                            
                    except Exception as e:
                        logger.error(f"    Error in chunk for {tf_name}: {e}. Retrying in 5s...")
                        if client:
                            client._connected = False # Force reconnect
                        await asyncio.sleep(5)
                        continue
                        
                logger.info(f"  Finished {sym_name} {tf_name}. Total candles: {total_saved}")

        if client:
            await client.disconnect()

    except Exception as e:
        logger.error(f"Global Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args()
    
    asyncio.run(backfill_candles(days=args.days))
