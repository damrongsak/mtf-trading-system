import os
import json
import base64
from cryptography.fernet import Fernet
import psycopg2
from urllib.parse import urlparse

# Get config from env
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://trader:trader@mtf-postgres:5432/mtf_db")
ENCRYPTION_KEY = os.getenv("SETTINGS_ENCRYPTION_KEY")

if not ENCRYPTION_KEY:
    print("ERROR: SETTINGS_ENCRYPTION_KEY not found in environment")
    exit(1)

cipher = Fernet(ENCRYPTION_KEY.encode())

def decrypt_data(encrypted_str: str) -> dict:
    try:
        # Check if it's already a JSON string containing the base64
        if encrypted_str.startswith('"') and encrypted_str.endswith('"'):
            encrypted_str = json.loads(encrypted_str)
        
        encrypted_bytes = base64.b64decode(encrypted_str)
        decrypted_bytes = cipher.decrypt(encrypted_bytes)
        return json.loads(decrypted_bytes.decode('utf-8'))
    except Exception as e:
        return {"error": str(e), "original": encrypted_str[:50] + "..."}

def verify():
    print(f"Connecting to DB: {DATABASE_URL}")
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    print("\n--- data_sources (CTRADER) ---")
    cur.execute("SELECT id, name, config_json FROM data_sources WHERE provider = 'CTRADER'")
    for row_id, name, config_enc in cur.fetchall():
        config = decrypt_data(config_enc)
        token_snippet = config.get('token', 'MISSING')[:10] + "..." if config.get('token') else 'N/A'
        print(f"ID: {row_id} | Name: {name}")
        print(f"  Token: {token_snippet}")
        if 'error' in config:
            print(f"  Error: {config['error']}")

    print("\n--- broker_accounts (CTRADER) ---")
    cur.execute("SELECT id, account_name, credentials_encrypted FROM broker_accounts WHERE broker_name = 'CTRADER'")
    for row_id, name, creds_enc in cur.fetchall():
        creds = decrypt_data(creds_enc)
        token_snippet = creds.get('token', 'MISSING')[:10] + "..." if creds.get('token') else 'N/A'
        print(f"ID: {row_id} | Name: {name}")
        print(f"  Token: {token_snippet}")
        if 'error' in creds:
            print(f"  Error: {creds['error']}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    verify()
