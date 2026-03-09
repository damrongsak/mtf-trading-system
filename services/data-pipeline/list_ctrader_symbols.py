
import asyncio
import json
import os
from app.adapters.ctrader_client import AsyncCTraderClient

# Database context
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://trader:trader@mtf-postgres:5432/mtf_db")

async def list_ctrader_symbols():
    from sqlalchemy import create_engine, text
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        ds_res = conn.execute(text("SELECT config_json FROM data_sources WHERE provider = 'CTRADER' AND is_active = true")).fetchone()
        if not ds_res:
             print("No active cTrader data source.")
             return
        config = ds_res[0]

    client = AsyncCTraderClient(config['host'], config['port'])
    await client.connect()
    await client.authorize_app(config['client_id'], config['client_secret'])
    await client.authorize_account(int(config['account_id']), config['token'])

    symbols = await client.get_symbols_list(int(config['account_id']))
    
    # Filter for Gold related symbols
    gold_symbols = [s for s in symbols if "XAU" in s.symbolName or "GOLD" in s.symbolName or "XAUUSD" in s.symbolName]
    
    print(f"\nFound {len(gold_symbols)} gold-related symbols:")
    for s in gold_symbols:
        print(f"ID: {s.symbolId:<10} | Name: {s.symbolName}")

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(list_ctrader_symbols())
