import pandas as pd
from sqlalchemy import text
from app.database import engine

def check_data():
    with engine.connect() as conn:
        # 1. Check Market Symbol ID
        query_sym = text("SELECT id, symbol FROM market_symbols WHERE symbol = 'XAU_USD'")
        result = conn.execute(query_sym).fetchone()
        
        if not result:
            print("ERROR: Symbol 'XAU/USD' not found in market_symbols table.")
            # List all symbols
            all_syms = conn.execute(text("SELECT symbol FROM market_symbols")).fetchall()
            print(f"INFO: Available symbols: {[s[0] for s in all_syms]}")
            return

        symbol_id = result[0]
        print(f"INFO: Found XAU/USD with ID: {symbol_id}")

        # 2. Check Candles Count for various timeframes
        timeframes = ['M15', 'H1', 'D', 'W', 'M']
        for tf in timeframes:
            query_count = text(f"""
                SELECT count(*), min(timestamp), max(timestamp) 
                FROM candles 
                WHERE market_symbol_id = :sid AND timeframe = :tf
            """)
            res = conn.execute(query_count, {"sid": symbol_id, "tf": tf}).fetchone()
            count, min_ts, max_ts = res
            print(f"INFO: Timeframe {tf} - Count: {count}, Range: {min_ts} to {max_ts}")

        # 3. List all distinct timeframes found for this symbol
        query_distinct = text("SELECT DISTINCT timeframe FROM candles WHERE market_symbol_id = :sid")
        distinct_tfs = conn.execute(query_distinct, {"sid": symbol_id}).fetchall()
        print(f"INFO: All distinct timeframes for XAU_USD: {[t[0] for t in distinct_tfs]}")

if __name__ == "__main__":
    check_data()
