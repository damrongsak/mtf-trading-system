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
        "client_id": "20383_R8XWLegmMzooUUNZ1BbrBiWXCrlypf1ucGPd5ioaQaptQLsY8B",
        "client_secret": "Ba7u0sGyBKrGjzIC3jYMvLGqBQP6q2ofYiE4pFy1BPQtG6GFFW",
        "token": "VonH4k7jzrdnWZRWqKqZsDJLON4p8UvxLo9GQIMYcI0",
        "refresh_token": "S3e8wJGusaVw36qMXkc6YXz7AZoai9NS13ULELPN5js",
        "account_id": "40816494"
    }
    
    encrypted = encrypt_data(new_creds)
    # Wrap in quotes to make it a valid JSON string for JSONB column
    json_encrypted = json.dumps(encrypted)
    
    db_url = os.getenv("DATABASE_URL", "postgresql://trader:trader@mtf-postgres:5432/mtf_db")
    
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        cur.execute(
            "UPDATE broker_accounts SET credentials_encrypted = %s, account_number = %s WHERE broker_name = 'CTRADER'",
            (json_encrypted, "40816494")
        )
        
        conn.commit()
        print(f"Successfully updated {cur.rowcount} CTRADER accounts.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_credentials()
