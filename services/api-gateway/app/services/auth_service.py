
import logging
import os
import time
import httpx
from sqlalchemy.orm import Session
from app.models.broker_account import BrokerAccount
from app.utils.crypto import encrypt_data, decrypt_data

logger = logging.getLogger(__name__)

async def refresh_ctrader_token_internal(account: BrokerAccount, db: Session, force: bool = False):
    """
    Internal logic to refresh cTrader token.
    Updates the database record directly.
    Returns True if refreshed, False if skipped/failed.
    """
    try:
        creds = decrypt_data(account.credentials_encrypted)
        refresh_token = creds.get("refresh_token")
        
        if not refresh_token:
            logger.warning(f"Account {account.id} has no refresh token")
            return False

        # Check expiry if not forced
        if not force:
            expires_at = creds.get("expires_at")
            if expires_at:
                # Refresh if expiring in < 3 days (259200 seconds)
                # 3 days = 3 * 24 * 3600 = 259200
                remaining = expires_at - int(time.time())
                if remaining > 259200:
                    logger.info(f"Account {account.id} token valid for {remaining}s. Skipping.")
                    return False
            else:
                # If expires_at is missing, we SHOULD refresh to populate it and ensure validity
                logger.info(f"Account {account.id} has no expiry timestamp. Refreshing to sync.")

        payload = {
            "provider": "CTRADER",
            "config": {
                 "host": "live.ctraderapi.com" if account.is_live else "demo.ctraderapi.com",
                 "port": 5035,
                 "client_id": creds.get("client_id"),
                 "client_secret": creds.get("client_secret"),
                 "refresh_token": refresh_token
            }
        }
        
        DATA_SERVICE_URL = os.getenv("DATA_PIPELINE_URL", "http://data-pipeline:8000")
            
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{DATA_SERVICE_URL}/api/v1/discovery/refresh-token",
                json=payload,
                timeout=20.0
            )
            
            if resp.status_code != 200:
                logger.error(f"Data Pipeline Error for {account.id}: {resp.text}")
                return False
                
            data = resp.json()
            new_access_token = data.get("access_token")
            new_refresh_token = data.get("refresh_token")
            expires_in = data.get("expires_in", 2592000)
            
            # Update Creds
            creds["token"] = new_access_token
            creds["refresh_token"] = new_refresh_token
            creds["expires_at"] = int(time.time()) + int(expires_in)
            
            account.credentials_encrypted = encrypt_data(creds)
            
            # Sync to DataSources (api-gateway & data-pipeline share DB)
            from app.models.data_source import DataSource
            
            def sync_db_updates():
                # Find all CTRADER sources
                data_sources = db.query(DataSource).filter(DataSource.provider == "CTRADER").all()
                
                for ds in data_sources:
                    if not ds.config_json:
                        continue
                        
                    # Check if this Source uses the same account_id
                    ds_acc_id = str(ds.config_json.get("account_id", ""))
                    acc_id_str_local = str(creds.get("account_id", ""))
                    
                    if ds_acc_id == acc_id_str_local:
                        # Update this Source
                        ds_config = dict(ds.config_json)
                        ds_config["token"] = new_access_token
                        ds_config["refresh_token"] = new_refresh_token
                        ds_config["expires_at"] = creds["expires_at"]
                        
                        ds.config_json = ds_config
                        db.add(ds)
                        logger.info(f"Synced refreshed token to DataSource {ds.name} (ID: {ds.id})")

                # Sync to other BrokerAccount records with the same account_id
                acc_id_str_local = str(creds.get("account_id", ""))
                other_accounts = db.query(BrokerAccount).filter(
                    BrokerAccount.broker_name == "CTRADER",
                    BrokerAccount.id != account.id
                ).all()
                
                for other_acc in other_accounts:
                    try:
                        other_creds = decrypt_data(other_acc.credentials_encrypted)
                        if str(other_creds.get("account_id", "")) == acc_id_str_local:
                            other_creds["token"] = new_access_token
                            other_creds["refresh_token"] = new_refresh_token
                            other_creds["expires_at"] = creds["expires_at"]
                            other_acc.credentials_encrypted = encrypt_data(other_creds)
                            db.add(other_acc)
                            logger.info(f"Synced refreshed token to duplicate BrokerAccount {other_acc.id}")
                    except Exception as sync_err:
                        logger.error(f"Failed to sync to duplicate account {other_acc.id}: {sync_err}")

                db.commit()

            await asyncio.to_thread(sync_db_updates)
            
            logger.info(f"Successfully refreshed token for account {account.id}")
            return True
            
    except Exception as e:
        logger.error(f"Internal refresh failed for {account.id}: {e}")
        return False
