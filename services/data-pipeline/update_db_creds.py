from cryptography.fernet import Fernet
import os
import json
import base64
import psycopg2
import time
import uuid

# Configuration
DB_URL_INTERNAL = os.getenv("DATABASE_URL", "postgresql://trader:trader@mtf-postgres:5432/mtf_db")
ENCRYPTION_KEY = os.getenv("SETTINGS_ENCRYPTION_KEY")

# Tokens from .env
CTRADER_TOKEN = os.getenv("CTRADER_TOKEN")
CTRADER_REFRESH_TOKEN = os.getenv("CTRADER_REFRESH_TOKEN")
CTRADER_DEMO_REFRESH_TOKEN = os.getenv("CTRADER_DEMO_REFRESH_TOKEN")

# App Credentials
CTRADER_CLIENT_ID = os.getenv("CTRADER_CLIENT_ID")
CTRADER_CLIENT_SECRET = os.getenv("CTRADER_CLIENT_SECRET")

NEW_EXPIRES_IN = 2628000 # 30 days
EXPIRES_AT = int(time.time() + NEW_EXPIRES_IN)

# cTrader Data Source
CTRADER_DATA_SOURCE_ID = "64d12d1a-353a-4eb0-ba46-b117c4ceedae"

if not all([ENCRYPTION_KEY, CTRADER_TOKEN, CTRADER_REFRESH_TOKEN]):
    print("ERROR: Missing required environment variables")
    exit(1)

cipher = Fernet(ENCRYPTION_KEY.encode())

def encrypt_data(data: dict) -> str:
    json_bytes = json.dumps(data).encode('utf-8')
    encrypted_bytes = cipher.encrypt(json_bytes)
    return base64.b64encode(encrypted_bytes).decode('utf-8')

def decrypt_data(encrypted_str: str) -> dict:
    try:
        if encrypted_str.startswith('"') and encrypted_str.endswith('"'):
            encrypted_str = json.loads(encrypted_str)
        encrypted_bytes = base64.b64decode(encrypted_str)
        decrypted_bytes = cipher.decrypt(encrypted_bytes)
        return json.loads(decrypted_bytes.decode('utf-8'))
    except Exception as e:
        print(f"Decryption error: {e}")
        return None

ACCOUNT_DATA = [
    {
        "account_number": "6023410",
        "account_id": "40816494",
        "broker_name": "icmarketssc",
        "account_name": "ICMarkets Live 6023410",
        "leverage": 1000,
        "currency": "USD",
        "balance": 104285,
        "live": True,
    },
    {
        "account_number": "9919680",
        "account_id": "46656483",
        "broker_name": "icmarketssc",
        "account_name": "ICMarkets Demo 9919680",
        "leverage": 1000,
        "currency": "USD",
        "balance": 200000,
        "live": False,
    },
    {
        "account_number": "8054381",
        "account_id": "179630",
        "broker_name": "fxpro",
        "account_name": "FxPro Live 8054381",
        "leverage": 30,
        "currency": "USD",
        "balance": 0,
        "live": True,
    },
    {
        "account_number": "1010319",
        "account_id": "200549",
        "broker_name": "pepperstone",
        "account_name": "Pepperstone Live 1010319",
        "leverage": 30,
        "currency": "JPY",
        "balance": 0,
        "live": True,
    },
    {
        "account_number": "1071818",
        "account_id": "23639265",
        "broker_name": "pepperstone",
        "account_name": "Pepperstone Live 1071818",
        "leverage": 30,
        "currency": "USD",
        "balance": 106,
        "live": True,
    },
    {
        "account_number": "8095395",
        "account_id": "46588795",
        "broker_name": "blackbullmarkets",
        "account_name": "BlackBull Live 8095395",
        "leverage": 1000,
        "currency": "USD",
        "balance": 0,
        "live": True,
    }
]

def update_db():
    conn = psycopg2.connect(DB_URL_INTERNAL)
    cur = conn.cursor()

    # 1. Update data_sources (General CTRADER provider config)
    print("Updating data_sources...")
    cur.execute("SELECT id, config_json FROM data_sources WHERE provider = 'CTRADER'")
    rows = cur.fetchall()
    for row_id, config_encrypted in rows:
        config = decrypt_data(config_encrypted)
        if config:
            config['token'] = CTRADER_TOKEN
            config['refresh_token'] = CTRADER_REFRESH_TOKEN
            config['expires_at'] = EXPIRES_AT
            new_config_encrypted = encrypt_data(config)
            cur.execute("UPDATE data_sources SET config_json = %s WHERE id = %s", (json.dumps(new_config_encrypted), row_id))
            print(f"Updated data_source {row_id}")

    # 2. Update/Add Broker Accounts & 1:1 Funds
    print("\nUpdating Broker Accounts & 1:1 Funds...")
    for acc in ACCOUNT_DATA:
        is_live = acc['live']
        host = "live.ctraderapi.com" if is_live else "demo.ctraderapi.com"
        
        credentials = {
            "host": host,
            "port": 5035,
            "account_id": acc['account_id'],
            "client_id": CTRADER_CLIENT_ID,
            "client_secret": CTRADER_CLIENT_SECRET,
            "token": CTRADER_TOKEN if is_live else CTRADER_DEMO_REFRESH_TOKEN,
            "refresh_token": CTRADER_REFRESH_TOKEN if is_live else CTRADER_DEMO_REFRESH_TOKEN,
            "expires_at": EXPIRES_AT
        }
        
        creds_encrypted = encrypt_data(credentials)
        
        # --- Fund Management (1:1 Logic) ---
        fund_name = f"{acc['account_name']} Fund"
        cur.execute("SELECT id FROM funds WHERE name = %s", (fund_name,))
        fund_existing = cur.fetchone()
        
        if fund_existing:
            fund_id = fund_existing[0]
            print(f"  Using existing Fund: {fund_name}")
        else:
            fund_id = str(uuid.uuid4())
            print(f"  Creating 1:1 Fund: {fund_name}")
            # Final fix: Added NOT NULL required columns
            cur.execute(
                """
                INSERT INTO funds (
                    id, name, description, strategy_type, asset_classes, 
                    max_risk_per_trade, default_lot_size, risk_percentage, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """,
                (fund_id, fund_name, f"Dedicated Fund for {acc['account_name']}", 'MTF_SMC_BASIC', 
                 json.dumps(['FX']), 10.0, 0.01, 0.01)
            )

        # --- Broker Account Management ---
        cur.execute("SELECT id FROM broker_accounts WHERE account_number = %s", (acc['account_number'],))
        existing = cur.fetchone()
        
        if existing:
            row_id = existing[0]
            print(f"  Updating account: {acc['account_name']} ({acc['account_number']})")
            cur.execute(
                """
                UPDATE broker_accounts 
                SET broker_name = %s, account_name = %s, credentials_encrypted = %s, 
                    is_live = %s, leverage = %s, currency = %s, balance_snapshot = %s, 
                    fund_id = %s, data_source_id = %s, updated_at = NOW()
                WHERE id = %s
                """,
                (acc['broker_name'], acc['account_name'], json.dumps(creds_encrypted), 
                 is_live, acc['leverage'], acc['currency'], acc['balance'],
                 fund_id, CTRADER_DATA_SOURCE_ID, row_id)
            )
        else:
            print(f"  Adding new account: {acc['account_name']} ({acc['account_number']})")
            new_id = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO broker_accounts (
                    id, fund_id, data_source_id, broker_name, account_name, account_number, 
                    credentials_encrypted, is_active, is_live, leverage, 
                    currency, balance_snapshot, created_at, updated_at, environment
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), %s
                )
                """,
                (new_id, fund_id, CTRADER_DATA_SOURCE_ID, acc['broker_name'], acc['account_name'], 
                 acc['account_number'], json.dumps(creds_encrypted), True, is_live, 
                 acc['leverage'], acc['currency'], acc['balance'], 'live' if acc['live'] else 'demo')
            )

    conn.commit()
    cur.close()
    conn.close()
    print("\nSuccess!")

if __name__ == "__main__":
    update_db()
