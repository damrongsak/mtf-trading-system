
import os
import sys
import json
from sqlalchemy import create_engine, text
from cryptography.fernet import Fernet

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://trader:trader@postgres:5432/mtf_db")
ENCRYPTION_KEY = os.getenv("SETTINGS_ENCRYPTION_KEY")

def decrypt_data(encrypted_data):
    if not encrypted_data:
        return {}
    if not ENCRYPTION_KEY:
        raise ValueError("SETTINGS_ENCRYPTION_KEY not set")
    f = Fernet(ENCRYPTION_KEY)
    decrypted_json = f.decrypt(encrypted_data.encode()).decode()
    return json.loads(decrypted_json)

def main():
    if not ENCRYPTION_KEY:
        print(json.dumps({"error": "SETTINGS_ENCRYPTION_KEY not set in env"}))
        return

    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            query = text("SELECT credentials_encrypted, is_live FROM broker_accounts WHERE broker_name = 'CTRADER' ORDER BY created_at DESC LIMIT 1")
            result = conn.execute(query).fetchone()
            
            if not result:
                print(json.dumps({"error": "No cTrader account found"}))
                return

            creds = decrypt_data(result.credentials_encrypted)
            creds['is_live'] = result.is_live
            print(json.dumps(creds))
            
    except Exception as e:
        print(json.dumps({"error": str(e)}))

if __name__ == "__main__":
    main()
