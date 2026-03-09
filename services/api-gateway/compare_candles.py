
import asyncio
from sqlalchemy import create_engine, text
import os

# Database URL from environment or fallback
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://trader:trader@mtf-postgres:5432/mtf_db")

# Mapping between OANDA and CTRADER symbols
SYMBOL_MAPPING = {
    "XAU_USD": "XAUUSD",
    "EUR_USD": "EURUSD",
    "GBP_USD": "GBPUSD" # Checking if GBPUSD exists in cTrader too
}

# Timeframes to compare
TIMEFRAMES = ["M1", "M5", "M15", "H1", "H4", "D1", "W1", "MN1"]

async def compare_candles():
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        print(f"{'Symbol (O/C)':<20} | {'TF':<5} | {'Source':<10} | {'Close':<12} | {'Timestamp (UTC)':<25}")
        print("-" * 100)
        
        for oanda_sym, ctrader_sym in SYMBOL_MAPPING.items():
            for tf in TIMEFRAMES:
                # Fetch latest OANDA candle
                oanda_query = text("""
                    SELECT c.close, c.timestamp 
                    FROM candles c
                    JOIN market_symbols ms ON c.market_symbol_id = ms.id
                    JOIN data_sources ds ON ms.data_source_id = ds.id
                    WHERE ms.symbol = :symbol AND c.timeframe = :tf AND ds.provider = 'OANDA'
                    ORDER BY c.timestamp DESC LIMIT 1
                """)
                oanda_res = conn.execute(oanda_query, {"symbol": oanda_sym, "tf": tf}).fetchone()
                
                # Fetch latest CTRADER candle
                ctrader_query = text("""
                    SELECT c.close, c.timestamp 
                    FROM candles c
                    JOIN market_symbols ms ON c.market_symbol_id = ms.id
                    JOIN data_sources ds ON ms.data_source_id = ds.id
                    WHERE ms.symbol = :symbol AND c.timeframe = :tf AND ds.provider = 'CTRADER'
                    ORDER BY c.timestamp DESC LIMIT 1
                """)
                ctrader_res = conn.execute(ctrader_query, {"symbol": ctrader_sym, "tf": tf}).fetchone()
                
                if oanda_res and ctrader_res:
                    o_close = float(oanda_res[0])
                    c_close = float(ctrader_res[0])
                    print(f"{oanda_sym + '/' + ctrader_sym:<20} | {tf:<5} | {'OANDA':<10} | {o_close:<12.5f} | {oanda_res[1]}")
                    print(f"{'':<20} | {'':<5} | {'CTRADER':<10} | {c_close:<12.5f} | {ctrader_res[1]}")
                    
                    diff = abs(o_close - c_close)
                    p_diff = (diff / o_close * 100) if o_close != 0 else 0
                    print(f"{'':<20} | {'':<5} | {'DIFF':<10} | {diff:<12.5f} ({p_diff:.4f}%)")
                    print("-" * 100)
                elif oanda_res or ctrader_res:
                    if oanda_res:
                        print(f"{oanda_sym:<20} | {tf:<5} | {'OANDA':<10} | {float(oanda_res[0]):<12.5f} | {oanda_res[1]}")
                    if ctrader_res:
                        print(f"{ctrader_sym:<20} | {tf:<5} | {'CTRADER':<10} | {float(ctrader_res[0]):<12.5f} | {ctrader_res[1]}")
                    print(f"{'':<20} | {'':<5} | {'CT/OA MISS':<10} | {''}")
                    print("-" * 100)

if __name__ == "__main__":
    asyncio.run(compare_candles())
