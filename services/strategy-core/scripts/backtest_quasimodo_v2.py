import os
import sys
import asyncio
import pandas as pd
import numpy as np
import vectorbt as vbt
from datetime import datetime, timezone

# Add app to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal
from app.models.candle import Candle
from app.models.market import MarketSymbol
from app.strategies.quasimodo_v1.strategy import strategy_vectorized

async def run_v2_backtest():
    print("="*70)
    print("BACKTEST: QUASIMODO V2 | XAU_USD_YF (Yahoo Finance)")
    print("="*70)
    
    db = SessionLocal()
    try:
        # 1. Fetch Yahoo Finance Gold Symbol
        ms = db.query(MarketSymbol).filter(MarketSymbol.symbol == "XAU_USD_YF").first()
        if not ms:
            print("❌ XAU_USD_YF symbol not found in database.")
            return

        # 2. Load Candles (M15)
        print(f"Loading M15 candles for {ms.symbol}...")
        candles = db.query(Candle).filter(
            Candle.symbol == ms.symbol,
            Candle.timeframe == "M15"
        ).order_by(Candle.timestamp.asc()).all()
        
        if not candles:
            print("❌ No M15 candles found for backtest.")
            return
            
        df = pd.DataFrame([{
            "timestamp": c.timestamp,
            "open": float(c.open),
            "high": float(c.high),
            "low": float(c.low),
            "close": float(c.close),
            "volume": float(c.volume)
        } for c in candles])
        
        df.set_index("timestamp", inplace=True)
        print(f"Loaded {len(df)} candles.")

        # 3. Strategy Parameters (V2)
        params = {
            "swing_strength": 1,
            "ema_fast": 13,
            "ema_slow": 50,
            "ema_macro": 200,      # H4 Bias Proxy
            "rl_filter_threshold": 0.4 # More permissive for initial baseline
        }

        # 4. Run Strategy Logic
        print("Detecting patterns and calculating signals (MTF + RL)...")
        entries_series, exits_series = strategy_vectorized(df, params)
        
        # Vectorbt expects bool or 1/0/ -1
        # Convert Series to match index
        entries = entries_series == 1
        short_entries = entries_series == -1
        
        print(f"Signals detected: Long={entries.sum()}, Short={short_entries.sum()}")

        if entries.sum() == 0 and short_entries.sum() == 0:
            print("No signals detected in this period.")
            return

        # 5. Portfolio Construction
        pf = vbt.Portfolio.from_signals(
            df['close'],
            entries=entries,
            exits=None, # Use SL/TP
            short_entries=short_entries,
            short_exits=None,
            sl_stop=0.02, # 2% SL
            tp_stop=0.04, # 4% TP
            init_cash=10000,
            fees=0.0005,  # 0.05% institutional fee
            freq='15T'
        )

        print("\n" + "="*70)
        print("PERFORMANCE METRICS (V2 Enhanced)")
        print("="*70)
        print(pf.stats())

    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(run_v2_backtest())
