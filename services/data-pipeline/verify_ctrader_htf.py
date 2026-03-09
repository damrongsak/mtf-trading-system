
import asyncio
import json
import os
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, text
from app.adapters.ctrader_client import AsyncCTraderClient

# Database context
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://trader:trader@mtf-postgres:5432/mtf_db")

async def verify_ctrader_htf():
    # 1. Get cTrader Config
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        ds_res = conn.execute(text("SELECT id, config_json FROM data_sources WHERE provider = 'CTRADER' AND is_active = true")).fetchone()
        if not ds_res:
             print("No active cTrader data source.")
             return
        ds_id, config = ds_res
        
        # Get Symbol ID for XAUUSD (Using confirmed ID 41)
        ms_res = conn.execute(text("SELECT id FROM market_symbols WHERE symbol = 'XAUUSD' AND data_source_id = :ds_id"), {"ds_id": ds_id}).fetchone()
        if not ms_res:
            print("XAUUSD symbol not found for cTrader.")
            return
        ms_id = ms_res[0]

    symbol_id = 41 # Confirmed from list_symbols

    client = AsyncCTraderClient(config['host'], config['port'])
    await client.connect()
    await client.authorize_app(config['client_id'], config['client_secret'])
    await client.authorize_account(int(config['account_id']), config['token'])

    tf_map = {"H1": 9, "H4": 10, "D1": 12}
    
    # Use wide range to find latest anyway
    to_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
    from_ts = to_ts - (30 * 24 * 60 * 60 * 1000) # 30 days
    
    print(f"\n{'TF':<5} | {'Source':<10} | {'Close':<12} | {'Timestamp (UTC)':<25}")
    print("-" * 75)

    for tf_name, period in tf_map.items():
        try:
            bars = await client.get_trendbars(
                account_id=int(config['account_id']),
                symbol_id=symbol_id,
                period=period,
                count=100, # Get more to be sure
                from_timestamp=from_ts,
                to_timestamp=to_ts
            )
            
            if bars:
                latest_bar = bars[-1]
                divisor = 100000.0
                low_raw = latest_bar.low
                
                if latest_bar.deltaOpen > (low_raw * 0.5):
                    close_p = latest_bar.deltaClose
                else:
                    close_p = low_raw + latest_bar.deltaClose
                
                broker_close = round(close_p / divisor, 5)
                broker_ts = datetime.fromtimestamp(latest_bar.utcTimestampInMinutes * 60, tz=timezone.utc)
                
                print(f"{tf_name:<5} | {'BROKER':<10} | {broker_close:<12.5f} | {broker_ts}")
                
                # Fetch latest from DB
                with engine.connect() as conn:
                    db_res = conn.execute(text("""
                        SELECT close, timestamp FROM candles 
                        WHERE market_symbol_id = :ms_id AND timeframe = :tf 
                        ORDER BY timestamp DESC LIMIT 1
                    """), {"ms_id": ms_id, "tf": tf_name}).fetchone()
                    
                    if db_res:
                        db_close = float(db_res[0])
                        db_ts = db_res[1]
                        if db_ts.tzinfo is None:
                            db_ts = db_ts.replace(tzinfo=timezone.utc)
                        
                        print(f"{'':<5} | {'DB':<10} | {db_close:<12.5f} | {db_ts}")
                        
                        if db_ts == broker_ts:
                             if abs(db_close - broker_close) < 0.00001:
                                 print(f"{'':<5} | {'STATUS':<10} | MATCHED ✅")
                             else:
                                 print(f"{'':<5} | {'STATUS':<10} | PRICE MISMATCH ⚠️")
                        else:
                             print(f"{'':<5} | {'STATUS':<10} | LAGGING ❌")
                    else:
                        print(f"{'':<5} | {'DB':<10} | NO DATA")
            else:
                print(f"{tf_name:<5} | BROKER returned no data.")
        except Exception as e:
             print(f"{tf_name:<5} | ERROR: {e}")
        print("-" * 75)

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(verify_ctrader_htf())
