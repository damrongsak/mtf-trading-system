
import asyncio
import logging
import sys
import os
import time
import json
import base64
from sqlalchemy.future import select
from datetime import datetime, timezone
from cryptography.fernet import Fernet
from typing import Optional, Dict

# Ensure app is in path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import get_db, SessionLocal

from app.models.market import MarketSymbol
from app.models.data_source import DataSource
from app.models.candle import Candle

# Models missing in data-pipeline app.models, defining locally for read-access
from sqlalchemy import Column, Integer, String, Boolean, Text
from app.database import Base

class BrokerAccount(Base):
    __tablename__ = "broker_accounts"
    id = Column(Integer, primary_key=True, index=True)
    broker_name = Column(String, index=True)
    credentials_encrypted = Column(Text)
    environment = Column(String)
    is_active = Column(Boolean, default=True)

# Crypto Utils (Inline implementation since not shared)
def get_cipher():
    key = os.getenv("SETTINGS_ENCRYPTION_KEY")
    if not key:
        logger.warning("SETTINGS_ENCRYPTION_KEY not set. Decryption may fail.")
        return None
        
    return Fernet(key.encode())

def decrypt_data(encrypted_str: str) -> dict:
    cipher = get_cipher()
    if not cipher:
        raise ValueError("Encryption Key Missing")
    encrypted_bytes = base64.b64decode(encrypted_str)
    decrypted_bytes = cipher.decrypt(encrypted_bytes)
    return json.loads(decrypted_bytes.decode('utf-8'))

# Adapter/Client Imports
from app.adapters.ctrader_client import AsyncCTraderClient
from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOAGetTickDataReq, ProtoOAGetTickDataRes

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("CandleBackfill")

# Local definition of TrendbarPeriod (based on Open API 2.0 specs)
class ProtoOATrendbarPeriod:
    M1 = 1
    M2 = 2
    M3 = 3
    M4 = 4
    M5 = 5
    M10 = 6
    M15 = 7
    M30 = 8
    H1 = 9
    H4 = 10
    H12 = 11
    D1 = 12
    W1 = 13
    MN1 = 14

# Local Timeframe Map
class ExtendedPeriod:
    M1 = ProtoOATrendbarPeriod.M1
    M5 = ProtoOATrendbarPeriod.M5
    M15 = ProtoOATrendbarPeriod.M15
    H1 = ProtoOATrendbarPeriod.H1
    H4 = ProtoOATrendbarPeriod.H4
    D1 = ProtoOATrendbarPeriod.D1
    W1 = ProtoOATrendbarPeriod.W1
    MN1 = ProtoOATrendbarPeriod.MN1

TIMEFRAME_MAP = {
    'M1': ExtendedPeriod.M1,
    'M5': ExtendedPeriod.M5,
    'M15': ExtendedPeriod.M15,
    'H1': ExtendedPeriod.H1,
    'H4': ExtendedPeriod.H4,
    'D': ExtendedPeriod.D1,
    'W': ExtendedPeriod.W1,   
    'M': ExtendedPeriod.MN1,
    'T15': 'TICK' # Special marker
}

async def backfill_candles():
    # Sync DB session
    db = SessionLocal()
    
    try:
        # 1. Find cTrader Account
        logger.info("Locating cTrader account...")
        account = db.query(BrokerAccount).filter(BrokerAccount.broker_name == "CTRADER", BrokerAccount.is_active == True).first()
        
        if not account:
            logger.error("No active cTrader account found.")
            return

        # 2. Decrypt Credentials
        try:
            credentials = decrypt_data(account.credentials_encrypted)
            client_id = credentials.get("client_id") or credentials.get("app_id")
            client_secret = credentials.get("client_secret") or credentials.get("secret")
            account_id = credentials.get("account_id")
            token = credentials.get("token")
            
            env = account.environment.lower() if account.environment else "demo"
            host = "live.ctraderapi.com" if env in ["live", "production"] else "demo.ctraderapi.com"
            port = 5035
            
        except Exception as e:
            logger.error(f"Failed to decrypt credentials: {e}")
            return

        # 3. Connect Client
        client = AsyncCTraderClient(host, port)
        try:
            await client.connect()
            await client.authorize_app(client_id, client_secret)
            await client.authorize_account(account_id, token)
            
            # 4. Target Symbols
            target_symbols = ["XAUUSD"] 
            
            # Find Data Source
            ds = db.query(DataSource).filter(DataSource.name == "CTRADER", DataSource.is_active == True).first()
            if not ds:
                logger.error("CTRADER Data Source not found")
                return

            def get_minutes(tf_str):
                if tf_str == 'M1': return 1
                if tf_str == 'M5': return 5
                if tf_str == 'M15': return 15
                if tf_str == 'H1': return 60
                if tf_str == 'H4': return 240
                if tf_str.startswith('D'): return 1440
                if tf_str.startswith('W'): return 10080
                if tf_str.startswith('M'): return 43200
                if tf_str == 'T15': return 1 # Approximation
                return 1

            for sym_name in target_symbols:
                ms = db.query(MarketSymbol).filter(
                    MarketSymbol.symbol == sym_name, 
                    MarketSymbol.data_source_id == ds.id, 
                    MarketSymbol.is_active == True
                ).first()
                
                if not ms or not ms.details or 'symbolId' not in ms.details:
                    logger.warning(f"Symbol {sym_name} not found or missing ID.")
                    continue
                
                symbol_id = ms.details['symbolId']
                # Digit based scaling is incorrect for raw cTrader values (always 10^5)
                # digits = ms.details.get('digits', 2)
                divisor = 100000.0

                for tf_name, tf_enum in TIMEFRAME_MAP.items():
                    logger.info(f"Processing {sym_name} {tf_name}...")
                    
                    try: 
                        candles_to_save = []
                        
                        if tf_name == 'T15':
                            # Fetch Ticks and Aggregate
                            to_ts = int(time.time() * 1000)
                            from_ts = to_ts - (2 * 60 * 60 * 1000) # Last 2 hours
                            
                            req = ProtoOAGetTickDataReq()
                            req.ctidTraderAccountId = int(account_id)
                            req.symbolId = int(symbol_id)
                            req.type = 1 # BID
                            req.fromTimestamp = from_ts
                            req.toTimestamp = to_ts
                            
                            resp = await client.send(req)
                            
                            if resp.payloadType == ProtoOAGetTickDataRes().payloadType:
                                res = ProtoOAGetTickDataRes()
                                res.ParseFromString(resp.payload)
                                
                                ticks = res.tickData
                                if not ticks:
                                    continue
                                    
                                # Decode Ticks
                                decoded_ticks = [] 
                                for t in ticks:
                                    decoded_ticks.append((t.timestamp, t.tick))
                                    
                                # Check for delta compression (heuristic)
                                if len(decoded_ticks) > 1:
                                    # If 2nd timestamp is small (< 1 year in ms), likely delta
                                    t1 = decoded_ticks[1][0]
                                    if t1 < 1000000000000: 
                                        decoded_ticks = []
                                        last_ts = 0
                                        last_p = 0
                                        for i, t in enumerate(ticks):
                                            if i == 0:
                                                last_ts = t.timestamp
                                                last_p = t.tick
                                            else:
                                                last_ts += t.timestamp
                                                last_p += t.tick
                                            decoded_ticks.append((last_ts, last_p))
                                    
                                # Aggregate T15
                                chunk_size = 15
                                for k in range(0, len(decoded_ticks), chunk_size):
                                    chunk = decoded_ticks[k:k+chunk_size]
                                    if not chunk: continue
                                    
                                    c_time = chunk[0][0]
                                    c_open = chunk[0][1]
                                    c_close = chunk[-1][1]
                                    c_high = max(t[1] for t in chunk)
                                    c_low = min(t[1] for t in chunk)
                                    
                                    candles_to_save.append({
                                        "market_symbol_id": ms.id,
                                        "timeframe": tf_name,
                                        "timestamp": datetime.fromtimestamp(c_time / 1000.0, timezone.utc),
                                        "open": c_open / divisor,
                                        "high": c_high / divisor,
                                        "low": c_low / divisor,
                                        "close": c_close / divisor,
                                        "volume": len(chunk)
                                    })
                            
                        else:
                            # Standard Timeframe
                            mins = get_minutes(tf_name)
                            
                            # Reduce count for long timeframes to avoid "INVALID_REQUEST"
                            req_count = 500
                            # Reduce Month and Week requests to avoid hitting data limits or timestamp issues
                            if tf_name in ['W', 'M', 'MN1', 'W1']:
                                req_count = 50 
                                
                            duration_ms = req_count * mins * 60 * 1000
                            now_ms = int(time.time() * 1000)
                            from_ms = int(now_ms - (duration_ms * 1.5))
                            
                            trendbars = await client.get_trendbars(
                                account_id=account_id,
                                symbol_id=symbol_id,
                                period=tf_enum,
                                count=req_count,
                                from_timestamp=from_ms,
                                to_timestamp=now_ms
                            )
                            
                            if trendbars:
                                for bar in trendbars:
                                    low = bar.low
                                    candles_to_save.append({
                                        "market_symbol_id": ms.id,
                                        "timeframe": tf_name,
                                        "timestamp": datetime.fromtimestamp(bar.utcTimestampInMinutes * 60, timezone.utc) if bar.utcTimestampInMinutes else datetime.now(timezone.utc),
                                        "open": (low + bar.deltaOpen) / divisor,
                                        "high": (low + bar.deltaHigh) / divisor,
                                        "low": low / divisor,
                                        "close": (low + bar.deltaClose) / divisor,
                                        "volume": bar.volume
                                    })

                        # Save to DB
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
                            logger.info(f"Saved {count} candles for {tf_name}")
                            
                    except Exception as e:
                        logger.error(f"Error processing {tf_name}: {e}")
                        continue

        except Exception as e:
            logger.error(f"Global Error: {e}")
        finally:
            await client.disconnect()

    except Exception as e:
        logger.error(f"DB Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(backfill_candles())
