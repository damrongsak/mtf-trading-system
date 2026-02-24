import os
import json
import base64
from cryptography.fernet import Fernet
import psycopg2

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

def update_credentials():
    new_creds = {
        "host": "live.ctraderapi.com",
        "port": 5035,
        "token": "2bi0Ba_AS8sIpxtuGCvQxSaoZPEQEIGiez5tZfANPww",
        "client_id": "20383_R8XWLegmMzooUUNZ1BbrBiWXCrlypf1ucGPd5ioaQaptQLsY8B",
        "account_id": "40816494",
        "expires_at": 2628000,
        "client_secret": "Ba7u0sGyBKrGjzIC3jYMvLGqBQP6q2ofYiE4pFy1BPQtG6GFFW",
        "refresh_token": "KjmPeU97wyHt9nz7Q072TQCHJ-gTwC9BFiJ9Vx14pOQ"
    }
    
    encrypted = encrypt_data(new_creds)
    # The existing database expectation seems to be the encrypted string wrapped in JSON
    json_encrypted = json.dumps(encrypted)
    
    db_url = os.getenv("DATABASE_URL", "postgresql://trader:trader@mtf-postgres:5432/mtf_db")
    
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        # We identified two accounts with this number for this user/fund
        # 821e584f-056b-46a7-afff-0bdd655e9810 (ICMARKET)
        # 4438a19e-5d19-48c9-89d6-5134ee996591 (40816494)
        
        cur.execute(
            "UPDATE broker_accounts SET credentials_encrypted = %s WHERE account_number = %s AND broker_name = 'CTRADER'",
            (json_encrypted, "40816494")
        )
        
        conn.commit()
        print(f"Successfully updated {cur.rowcount} CTRADER accounts for account 40816494.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_credentials()
