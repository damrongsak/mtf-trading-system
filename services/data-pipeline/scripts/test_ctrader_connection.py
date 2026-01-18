
import asyncio
import os
import sys
import json
from sqlalchemy import create_engine, text
from cryptography.fernet import Fernet

# Add parent directory to path to import app modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.adapters.ctrader_client import AsyncCTraderClient

# Database Connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://trader:trader@postgres:5432/mtf_db")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY") or os.getenv("SETTINGS_ENCRYPTION_KEY") # Ensure this matches the one used by API Gateway

# Helper to decrypt (simplified version of api-gateway logic)
def decrypt_data(encrypted_data):
    if not encrypted_data:
        return {}
    if not ENCRYPTION_KEY:
        raise ValueError("ENCRYPTION_KEY not set")
    f = Fernet(ENCRYPTION_KEY)
    decrypted_json = f.decrypt(encrypted_data.encode()).decode()
    return json.loads(decrypted_json)

async def test_connection():
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # Get the latest cTrader account
        query = text("SELECT id, account_number, credentials_encrypted, is_live FROM broker_accounts WHERE broker_name = 'CTRADER' ORDER BY created_at DESC LIMIT 1")
        result = conn.execute(query).fetchone()
        
        if not result:
            print("No cTrader account found in DB.")
            return

        print(f"Testing cTrader Account: {result.account_number} (Live: {result.is_live})")
        
        # We need the ENCRYPTION_KEY from the environment.
        # Since we are running this inside the container (hopefully), it might share envs or we need to pass it.
        # API Gateway likely generated the key.
        # NOTE: If we can't decrypt easily because of key mismatch, this test is hard.
        # But wait, api-gateway and data-pipeline might share the same .env file or env vars in docker-compose?
        
        try:
            creds = decrypt_data(result.credentials_encrypted)
        except Exception as e:
            print(f"Decryption failed: {e}")
            print("Ensure ENCRYPTION_KEY is set correctly.")
            return

        client_id = creds.get('client_id')
        client_secret = creds.get('client_secret')
        token = creds.get('token')
        account_id = creds.get('account_id')
        
        if not all([client_id, client_secret, token, account_id]):
            print("Missing credentials fields.")
            print(f"Found: {list(creds.keys())}")
            return

        print("Credentials decrypted successfully.")
        
        # Connect
        host = "live.ctraderapi.com" if result.is_live else "demo.ctraderapi.com"
        port = 5035
        
        client = AsyncCTraderClient(host, port, ssl=True)
        
        try:
            print(f"Connecting to {host}:{port}...")
            await client.connect()
            print("Connected.")
            
            print("Authorizing App...")
            await client.authorize_app(client_id, client_secret)
            print("App Authorized.")
            
            print(f"Authorizing Account {account_id}...")
            await client.authorize_account(int(account_id), token)
            print("Account Authorized.")
            
            print("SUCCESS: Connection and Authorization verified.")
            
            # Additional: Verify Symbol List fetch
            print("Fetching Symbols...")
            # Ideally client has a method for this, or we construct the message
            # But just auth is enough proof for now.
            
        except Exception as e:
            print(f"FAILED: {e}")
        finally:
            await client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_connection())
