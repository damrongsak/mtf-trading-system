
import asyncio
import logging
import sys
import os
import time

# Add parent directory to path to import app
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal
from app.models.broker_account import BrokerAccount
from app.models.data_source import DataSource
from app.utils.crypto import encrypt_data, decrypt_data

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("UpdateCreds")

NEW_ACCESS_TOKEN = "lN0ySqEpBUELurOeqh-jcOfefGzB9k6cmMZlNE3KA_s"
NEW_REFRESH_TOKEN = "a_orv62ZHd830VMkX93kYKlGH6jMlFPQaHsKVrC3O5g"
EXPIRES_IN = 2628000

async def update_creds():
    logger.info("Starting Credential Update...")
    db = SessionLocal()
    try:
        # 1. Update Broker Accounts
        accounts = db.query(BrokerAccount).filter(
            BrokerAccount.broker_name == "CTRADER", 
            BrokerAccount.is_active == True
        ).all()
        
        if not accounts:
            logger.error("No active cTrader accounts found.")
            return

        for account in accounts:
            logger.info(f"Updating account {account.account_name} ({account.id})...")
            
            creds = decrypt_data(account.credentials_encrypted)
            creds["token"] = NEW_ACCESS_TOKEN
            creds["refresh_token"] = NEW_REFRESH_TOKEN
            creds["expires_at"] = int(time.time()) + EXPIRES_IN
            
            account.credentials_encrypted = encrypt_data(creds)
            
            # 2. Update Matching Data Sources
            data_sources = db.query(DataSource).filter(DataSource.provider == "CTRADER").all()
            for ds in data_sources:
                 if not ds.config_json: continue
                 
                 ds_acc_id = str(ds.config_json.get("account_id", ""))
                 acc_id_str = str(creds.get("account_id", ""))
                 
                 if ds_acc_id == acc_id_str:
                     ds_config = dict(ds.config_json)
                     ds_config["token"] = NEW_ACCESS_TOKEN
                     ds_config["refresh_token"] = NEW_REFRESH_TOKEN
                     ds_config["expires_at"] = creds["expires_at"]
                     
                     ds.config_json = ds_config
                     db.add(ds)
                     logger.info(f"Synced to DataSource {ds.name}")
            
            db.commit()
            logger.info("SUCCESS: Credentials Updated.")

    except Exception as e:
        logger.error(f"Update failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(update_creds())
