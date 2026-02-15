import asyncio
import os
import json
import base64
from cryptography.fernet import Fernet
# Adjust import path if needed, assuming running from /app
import sys
sys.path.append("/app")

from app.adapters.ctrader_client import AsyncCTraderClient
from app.database import AsyncSessionLocal
from app.models import BrokerAccount
from sqlalchemy import select

# Helper functions for decryption
def get_cipher():
    key = os.getenv("SETTINGS_ENCRYPTION_KEY")
    if not key:
        raise ValueError("SETTINGS_ENCRYPTION_KEY environment variable is not set")
    return Fernet(key.encode())

def decrypt_data(encrypted_str: str) -> dict:
    cipher = get_cipher()
    # Check if string or bytes. If stored as JSON string inside JSONB
    if isinstance(encrypted_str, str):
         try:
             # Try un-json-dumping first if it was double-encoded
             # (we suspect manual_refresh might have done this or original code)
             if encrypted_str.startswith('"') or encrypted_str.startswith('{'):
                 try_load = json.loads(encrypted_str)
                 # If it became a string again (base64)
                 if isinstance(try_load, str):
                     encrypted_str = try_load
         except:
             pass
    
    # ensure bytes
    if isinstance(encrypted_str, str):
        encrypted_bytes = base64.b64decode(encrypted_str)
    else:
        encrypted_bytes = base64.b64decode(encrypted_str) # assuming bytes? JSONB returns str usually

    decrypted_bytes = cipher.decrypt(encrypted_bytes)
    return json.loads(decrypted_bytes.decode('utf-8'))

async def main():
    print("Connecting to DB...")
    async with AsyncSessionLocal() as db:
        # Fetch account 40816494 Live
        
        result = await db.execute(select(BrokerAccount).where(
            BrokerAccount.account_number == '40816494',
            BrokerAccount.environment == 'live' 
        ))
        
        accounts = result.scalars().all()
        # Filter in python if is_active logic complex or just take first active
        active_accounts = [a for a in accounts if a.is_active]
        
        if not active_accounts:
            print("No active live account found for 40816494 in execution DB view")
            return

        target = active_accounts[0] # Pick first active
            
        print(f"Using Account ID (UUID): {target.id}")
        
        try:
            creds = decrypt_data(target.credentials_encrypted)
        except Exception as e:
            print(f"Decryption failed: {e}")
            import traceback
            traceback.print_exc()
            return

        token = creds.get("token")
        client_id = creds.get("client_id")
        client_secret = creds.get("client_secret")
        
        if not token:
            print("No token found in credentials.")
            return

        print(f"Token: {token[:10]}...")
        
        client = AsyncCTraderClient("live.ctraderapi.com", 5035)
        
        try:
            await client.connect()
            print("Connected to cTrader.")
            
            await client.authorize_app(client_id, client_secret)
            print("App Authorized.")
            
            print("Fetching Account List using Token...")
            accounts_list = await client.get_account_list(token)
            
            print(f"Found {len(accounts_list)} accounts linked to this token:")
            match_found = False
            for acc in accounts_list:
                aid = acc.ctidTraderAccountId
                is_live = acc.isLive
                print(f" - ID: {aid}, Live: {is_live}")
                
                if str(aid) == '40816494':
                    match_found = True
                    
            if match_found:
                 print("✅ SUCCESS: Account 40816494 is authorized!")
                 
                 print("Attempting Authorize Account + Get Trader (reproducing failure)...")
                 acc_id_int = int('40816494')
                 try:
                     await client.authorize_account(acc_id_int, token)
                     print("Account Authorized (or ALREADY_LOGGED_IN).")
                     
                     trader = await client.get_trader(acc_id_int)
                     print(f"✅ TRADER FETCHED! Balance: {trader.balance}")
                 except Exception as exc:
                     print(f"❌ Failed to get trader: {exc}")

            else:
                 print("❌ FAILURE: Account 40816494 is NOT in the authorized list!")
                 
        except Exception as e:
            print(f"Error checking cTrader: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await client.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
