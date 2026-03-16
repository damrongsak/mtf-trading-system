from cryptography.fernet import Fernet
import os
import json
import base64
import psycopg2

# Configuration
# Use localhost because I'll run this from the host but pointing to mapped port, 
# wait, actually better to run it inside a container where names work.
DB_URL_INTERNAL = os.getenv("DATABASE_URL", "postgresql://trader:trader@mtf-postgres:5432/mtf_db")

ENCRYPTION_KEY = os.getenv("SETTINGS_ENCRYPTION_KEY")
NEW_TOKEN = os.getenv("CTRADER_TOKEN")
NEW_REFRESH_TOKEN = os.getenv("CTRADER_REFRESH_TOKEN")

if not all([ENCRYPTION_KEY, NEW_TOKEN, NEW_REFRESH_TOKEN]):
    print("ERROR: Missing required environment variables (SETTINGS_ENCRYPTION_KEY, CTRADER_TOKEN, CTRADER_REFRESH_TOKEN)")
    exit(1)

cipher = Fernet(ENCRYPTION_KEY.encode())

def encrypt_data(data: dict) -> str:
    json_bytes = json.dumps(data).encode('utf-8')
    encrypted_bytes = cipher.encrypt(json_bytes)
    return base64.b64encode(encrypted_bytes).decode('utf-8')

def decrypt_data(encrypted_str: str) -> dict:
    encrypted_bytes = base64.b64decode(encrypted_str)
    decrypted_bytes = cipher.decrypt(encrypted_bytes)
    return json.loads(decrypted_bytes.decode('utf-8'))

def update_db():
    conn = psycopg2.connect(DB_URL_INTERNAL)
    cur = conn.cursor()

    # 1. Update data_sources
    print("Updating data_sources...")
    cur.execute("SELECT id, config_json FROM data_sources WHERE provider = 'CTRADER'")
    rows = cur.fetchall()
    for row_id, config_encrypted in rows:
        config = decrypt_data(config_encrypted)
        config['token'] = NEW_TOKEN
        config['refresh_token'] = NEW_REFRESH_TOKEN
        # Update expires_at to something in the future if possible, or just keep it
        # The original was 1775815201 (around 2026-04-20)
        new_config_encrypted = encrypt_data(config)
        # Ensure it's stored as a JSON string literal for jsonb
        cur.execute("UPDATE data_sources SET config_json = %s WHERE id = %s", (json.dumps(new_config_encrypted), row_id))
        print(f"Updated data_source {row_id}")

    # 2. Update broker_accounts
    print("Updating broker_accounts...")
    cur.execute("SELECT id, credentials_encrypted FROM broker_accounts WHERE broker_name = 'CTRADER'")
    rows = cur.fetchall()
    for row_id, creds_encrypted in rows:
        creds = decrypt_data(creds_encrypted)
        creds['token'] = NEW_TOKEN
        creds['refresh_token'] = NEW_REFRESH_TOKEN
        new_creds_encrypted = encrypt_data(creds)
        # Ensure it's stored as a JSON string literal for jsonb
        cur.execute("UPDATE broker_accounts SET credentials_encrypted = %s WHERE id = %s", (json.dumps(new_creds_encrypted), row_id))
        print(f"Updated broker_account {row_id}")

    conn.commit()
    cur.close()
    conn.close()
    print("Success!")

if __name__ == "__main__":
    update_db()
