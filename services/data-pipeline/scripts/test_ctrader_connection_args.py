
import asyncio
import os
import sys
import json
import argparse

# Add parent directory to path to import app modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.adapters.ctrader_client import AsyncCTraderClient

async def test_connection(creds):
    client_id = creds.get('client_id')
    client_secret = creds.get('client_secret')
    token = creds.get('token')
    account_id = creds.get('account_id')
    is_live = creds.get('is_live', False)
    
    if not all([client_id, client_secret, token, account_id]):
        print("Missing credentials fields.")
        return

    host = "live.ctraderapi.com" if is_live else "demo.ctraderapi.com"
    port = 5035
    
    print(f"Testing Connect to {host}:{port} for Account {account_id}...")
    
    client = AsyncCTraderClient(host, port, ssl=True)
    
    try:
        await client.connect()
        print("Connected.")
        
        await client.authorize_app(client_id, client_secret)
        print("App Authorized.")
        
        await client.authorize_account(int(account_id), token)
        print("Account Authorized.")
        
        print("SUCCESS: Connection verified.")
        
    except Exception as e:
        print(f"FAILED: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('creds', help='JSON string of credentials')
    args = parser.parse_args()
    
    creds = json.loads(args.creds)
    asyncio.run(test_connection(creds))
