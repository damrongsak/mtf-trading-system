import os
import json
import base64
import argparse
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

def update_credentials(creds_path: str, account_number: str):
    if not os.path.exists(creds_path):
        print(f"Error: Credentials file not found at {creds_path}")
        return

    with open(creds_path, 'r') as f:
        new_creds = json.load(f)
    
    encrypted = encrypt_data(new_creds)
    # The existing database expectation is the encrypted string wrapped in JSON
    json_encrypted = json.dumps(encrypted)
    
    db_url = os.getenv("DATABASE_URL", "postgresql://trader:trader@mtf-postgres:5432/mtf_db")
    
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        cur.execute(
            "UPDATE broker_accounts SET credentials_encrypted = %s WHERE account_number = %s AND broker_name = 'CTRADER'",
            (json_encrypted, account_number)
        )
        
        conn.commit()
        print(f"Successfully updated {cur.rowcount} CTRADER accounts for account {account_number}.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update broker credentials securely.")
    parser.add_argument("creds_file", help="Path to JSON file containing credentials")
    parser.add_argument("account_number", help="Broker account number to update")
    
    args = parser.parse_args()
    update_credentials(args.creds_file, args.account_number)
