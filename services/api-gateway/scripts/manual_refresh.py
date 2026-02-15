import os
import json
import asyncio
import httpx
import base64
from cryptography.fernet import Fernet
import psycopg2
from datetime import datetime
import time

# Helper functions
def get_cipher():
    key = os.getenv("SETTINGS_ENCRYPTION_KEY")
    if not key:
        raise ValueError("SETTINGS_ENCRYPTION_KEY environment variable is not set")
    return Fernet(key.encode())

def encrypt_data(data: dict) -> str:
    cipher = get_cipher()
    json_bytes = json.dumps(data).encode('utf-8')
    encrypted_bytes = cipher.encrypt(json_bytes)
    return base64.b64encode(encrypted_bytes).decode('utf-8')

def decrypt_data(encrypted_str: str) -> dict:
    cipher = get_cipher()
    encrypted_bytes = base64.b64decode(encrypted_str)
    decrypted_bytes = cipher.decrypt(encrypted_bytes)
    return json.loads(decrypted_bytes.decode('utf-8'))

async def refresh_token():
    db_url = os.getenv("DATABASE_URL", "postgresql://trader:trader@mtf-postgres:5432/mtf_db")
    
    print(f"Connecting to DB: {db_url}...")
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
    except Exception as e:
        print(f"DB Connection Failed: {e}")
        return

    # Get cTrader accounts
    print("Fetching active cTrader accounts...")
    cur.execute("SELECT id, credentials_encrypted, is_live, account_number FROM broker_accounts WHERE broker_name = 'CTRADER' AND is_active = true")
    rows = cur.fetchall()
    
    print(f"Found {len(rows)} accounts.")

    for row in rows:
        acc_id, enc_creds, is_live, acc_num = row
        print(f"Checking account {acc_num} (ID: {acc_id}, Live: {is_live})...")
        
        try:
            # Need to handle JSONB string vs object? 
            # psycopg2 returns dict for JSONB usually if registered? 
            # Or string? "credentials_encrypted" is defined as JSONB in SQL but stored as string in python code?
            # In update_ctrader_creds.py: json.dumps(encrypted) -> stored as JSON string "..." inside JSONB.
            # So we get a string that is a JSON string of the encrypted string?
            # Let's inspect type.
            
            creds_raw = enc_creds
            if isinstance(creds_raw, str):
                # If it's a JSON string wrapping the actual string
                 try:
                     creds_raw = json.loads(creds_raw)
                 except:
                     pass
            
            # Now creds_raw should be the base64 encrypted string
            creds = decrypt_data(creds_raw)
            refresh_token = creds.get("refresh_token")
            
            if not refresh_token:
                print("No refresh token found.")
                continue
            
            print(f"Refresh Token found (starts with {refresh_token[:5]}...)")

            payload = {
                "provider": "CTRADER",
                "config": {
                     "host": "live.ctraderapi.com" if is_live else "demo.ctraderapi.com",
                     "port": 5035,
                     "client_id": creds.get("client_id"),
                     "client_secret": creds.get("client_secret"),
                     "account_id": creds.get("account_id"),
                     "token": creds.get("token"),
                     "refresh_token": refresh_token
                }
            }
            
            # Call data-pipeline
            # Script runs inside api-gateway container on same network as data-pipeline
            url = "http://data-pipeline:8000/api/v1/discovery/refresh-token"
            
            async with httpx.AsyncClient() as client:
                print(f"Calling {url}...")
                resp = await client.post(url, json=payload, timeout=30.0)
                
                if resp.status_code != 200:
                    print(f"Failed to refresh: {resp.status_code} - {resp.text}")
                    continue
                    
                data = resp.json()
                new_access = data.get("access_token")
                new_refresh = data.get("refresh_token")
                expires_in = data.get("expires_in", 2592000)
                
                print(f"Token refreshed! New Access: {new_access[:5]}...")
                
                # Update Creds
                creds["token"] = new_access
                creds["refresh_token"] = new_refresh
                creds["expires_at"] = int(time.time()) + int(expires_in)
                
                # Re-encrypt
                new_enc = encrypt_data(creds)
                
                # Store as JSON string inside JSONB?
                # The schema is JSONB. We stored `json.dumps(encrypted)` in previous script.
                # Let's match that convention.
                json_enc_store = json.dumps(new_enc)
                
                cur.execute(
                    "UPDATE broker_accounts SET credentials_encrypted = %s, updated_at = NOW() WHERE id = %s",
                    (json_enc_store, acc_id)
                )
                conn.commit()
                print("Database updated.")
                
        except Exception as e:
            print(f"Error processing account {acc_id}: {e}")
            import traceback
            traceback.print_exc()
            
    cur.close()
    conn.close()

if __name__ == "__main__":
    asyncio.run(refresh_token())
