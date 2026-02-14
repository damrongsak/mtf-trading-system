import os
from sqlalchemy import create_engine, text
import json

DATABASE_URL = "postgresql://trader:trader@mtf-postgres:5432/mtf_db"

def check_symbol():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT id, symbol, details FROM market_symbols WHERE symbol = 'XAUUSD';"))
        for row in result:
            print(f"ID: {row.id}")
            print(f"Symbol: {row.symbol}")
            print(f"Details: {json.dumps(row.details, indent=2)}")
            
            # Check candles count
            c_count = conn.execute(text(f"SELECT count(*) FROM candles WHERE market_symbol_id = '{row.id}';")).scalar()
            print(f"Candles Count: {c_count}")
            
            # Check latest candle
            latest = conn.execute(text(f"SELECT timestamp, open FROM candles WHERE market_symbol_id = '{row.id}' ORDER BY timestamp DESC LIMIT 1;")).first()
            if latest:
                print(f"Latest Candle: {latest.timestamp} | Open: {latest.open}")

if __name__ == "__main__":
    check_symbol()
