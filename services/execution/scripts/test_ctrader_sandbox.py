import asyncio
import os
import sys
import json
import logging

# Setup Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add app to path
sys.path.append('/app')

from app.adapters.ctrader import CTraderOrderAdapter

async def test_connection():
    print("🚀 Starting cTrader Sandbox Connection Test...")
    
    # Credentials from DB
    credentials = {
        "host": "live.ctraderapi.com", # Try demo if live fails
        "port": 5035,
        "client_id": "20383_R8XWLegmMzooUUNZ1BbrBiWXCrlypf1ucGPd5ioaQaptQLsY8B",
        "client_secret": "Ba7u0sGyBKrGjzIC3jYMvLGqBQP6q2ofYiE4pFy1BPQtG6GFFW",
        "account_id": "40816494",
        "token": "45PcGE9xJQcYyGhSqYHnCgJq54078kjEvrJSbI6VfDI"
    }
    
    # Use CTraderOrderAdapter
    adapter = CTraderOrderAdapter(
        client_id=credentials["client_id"],
        client_secret=credentials["client_secret"],
        account_id=credentials["account_id"],
        token=credentials["token"],
        host=credentials["host"]
    )
    
    try:
        print(f"📡 Connecting to {credentials['host']}...")
        summary = await adapter.get_account_summary()
        print(f"✅ Connection Successful!")
        print(f"💰 Account Summary: {json.dumps(summary, indent=2)}")
        
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        
        # Try Demo Host if Live failed
        if credentials["host"] == "live.ctraderapi.com":
            print("🔄 Retrying with demo.ctraderapi.com...")
            adapter.host = "demo.ctraderapi.com"
            adapter.client.host = "demo.ctraderapi.com"
            try:
                summary = await adapter.get_account_summary()
                print(f"✅ Connection Successful (Demo)!")
                print(f"💰 Account Summary: {json.dumps(summary, indent=2)}")
            except Exception as e2:
                print(f"❌ Connection Failed (Demo): {e2}")

if __name__ == "__main__":
    asyncio.run(test_connection())
