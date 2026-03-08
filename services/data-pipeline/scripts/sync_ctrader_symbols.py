
import asyncio
import logging
import sys
import os
import json
import base64
from cryptography.fernet import Fernet
from sqlalchemy.future import select

# Ensure app is in path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import get_db, SessionLocal
from app.models.market import MarketSymbol
from app.models.data_source import DataSource
from app.database import Base
from sqlalchemy import Column, Integer, String, Boolean, Text

from app.adapters.ctrader_client import AsyncCTraderClient
from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOASubscribeSpotsReq

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SyncCTrader")

from app.models.broker_account import BrokerAccount

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

# --- Main Sync Logic ---
async def sync_symbols():
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
            creds = decrypt_data(account.credentials_encrypted)
            client_id = creds.get("client_id") or creds.get("app_id")
            client_secret = creds.get("client_secret") or creds.get("secret")
            account_id = creds.get("account_id")
            token = creds.get("token")
            
            env = account.environment.lower() if account.environment else "demo"
            host = "live.ctraderapi.com" if env in ["live", "production"] else "demo.ctraderapi.com"
            port = 5035
        except Exception as e:
            logger.error(f"Failed to decrypt credentials: {e}")
            return

        # 3. Find Data Source ID
        ds = db.query(DataSource).filter(DataSource.name == "CTRADER").first()
        if not ds:
            logger.error("CTRADER Data Source not found in DB")
            return

        # 4. Connect & Fetch
        client = AsyncCTraderClient(host, port)
        try:
            await client.connect()
            await client.authorize_app(client_id, client_secret)
            await client.authorize_account(account_id, token)
            
            logger.info("Fetching symbols list...")
            # Fetch minimal list to map Names -> IDs
            symbols_list = await client.get_symbols_list(account_id)
            # Map Name -> ID
            name_to_id = {s.symbolName: s.symbolId for s in symbols_list}
            
            logger.info("Fetching DB symbols to sync...")
            # Get only active symbols for cTrader or those we want to enable
            # For now, let's sync all symbols in our DB that are associated with cTrader
            db_symbols = db.query(MarketSymbol).filter(MarketSymbol.data_source_id == ds.id, MarketSymbol.is_active == True).all()
            
            ids_to_fetch = []
            symbol_map = {} # ID -> DB_Record

            for ms in db_symbols:
                # Resolve ID
                # Try exact match first, then clean
                sid = name_to_id.get(ms.symbol)
                if not sid:
                     clean = ms.symbol.replace("/", "").replace("_", "")
                     sid = name_to_id.get(clean)
                
                if sid:
                    ids_to_fetch.append(sid)
                    symbol_map[sid] = ms
                else:
                    logger.warning(f"Symbol {ms.symbol} not found in cTrader account.")

            if not ids_to_fetch:
                logger.info("No matching symbols found to sync.")
                return

            logger.info(f"Fetching full details for {len(ids_to_fetch)} symbols...")
            full_details = await client.get_symbols_full(account_id, ids_to_fetch)
            
            updated_count = 0
            for details in full_details:
                sid = details.symbolId
                ms = symbol_map.get(sid)
                if not ms: continue
                
                # Attempt to parse currencies from DB symbol (e.g. "EUR/USD" or "XAU_USD")
                base_curr = None
                quote_curr = None
                if ms.symbol:
                    # Strategy 1: Delimiter based
                    slashed = ms.symbol.replace("_", "/")
                    if "/" in slashed:
                        parts = slashed.split("/")
                        if len(parts) == 2:
                            base_curr = parts[0]
                            quote_curr = parts[1]
                    # Strategy 2: Standard 6-char pair (e.g. XAUUSD, EURUSD)
                    elif len(ms.symbol) == 6:
                        base_curr = ms.symbol[:3]
                        quote_curr = ms.symbol[3:]

                # Default values
                std_details = {
                    "symbol_id": sid,
                    "lot_size": int(details.lotSize) if details.HasField('lotSize') else 10000000,
                    "digits": details.digits if details.HasField('digits') else 5,
                    "pipPosition": details.pipPosition if details.HasField('pipPosition') else -4,
                    "minLot": float(details.minVolume) / 100.0 if details.HasField('minVolume') else 0.01,
                    "maxLot": float(details.maxVolume) / 100.0 if details.HasField('maxVolume') else 100.0,
                    "lotStep": float(details.stepVolume) / 100.0 if details.HasField('stepVolume') else 0.01,
                    "step_volume": float(details.stepVolume) / 100.0 if details.HasField('stepVolume') else 0.01,
                    "baseCurrency": base_curr,
                    "quoteCurrency": quote_curr,
                    "raw": {
                        "symbolId": sid,
                        "digits": details.digits,
                        "lotSize": details.lotSize if details.HasField('lotSize') else None
                    }
                }
                
                # Update DB
                ms.details = std_details
                logger.info(f"Updated {ms.symbol}: Digits={std_details['digits']}, PipPos={std_details['pipPosition']}")
                updated_count += 1
            
            db.commit()
            logger.info(f"Successfully synced {updated_count} symbols.")

        except Exception as e:
            logger.error(f"API Error: {e}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            await client.disconnect()

    except Exception as e:
        logger.error(f"DB Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(sync_symbols())
