#!/usr/bin/env python3
import pandas as pd
import numpy as np
import vectorbt as vbt
from sqlalchemy import create_engine
import json
import os
import sys
from datetime import datetime, timedelta

# Add app to path
sys.path.append('/app')

from app.strategies.quasimodo_v1.strategy import strategy_vectorized
from app.database import SessionLocal
from app.models.market import MarketSymbol
from app.models.data_source import DataSource

# ============= CONFIG =============
SYMBOL = "XAU_USD"
TIMEFRAME = "M15"
START_DATE = datetime.now() - timedelta(days=30)
END_DATE = datetime.now()

def load_data():
    db = SessionLocal()
    try:
        # Resolve symbol ID
        ms = db.query(MarketSymbol).filter(MarketSymbol.symbol == SYMBOL).first()
        if not ms:
            print(f"Error: Symbol {SYMBOL} not found")
            return None
        
        market_symbol_id = ms.id
        
        from app.backtest import fetch_data_from_db
        df = fetch_data_from_db(
            market_symbol_id=market_symbol_id,
            timeframe=TIMEFRAME,
            start_date=START_DATE,
            end_date=END_DATE
        )
        if df is not None and not df.empty:
            df = df.sort_index()
        return df
    finally:
        db.close()

def main():
    print("=" * 70)
    print(f"BACKTEST: QUASIMODO V1 | {SYMBOL} {TIMEFRAME}")
    print("=" * 70)
    
    df = load_data()
    if df is None or df.empty:
        print("No data found.")
        return

    # Ensure clean float data for Numba
    df = df.astype({'open': float, 'high': float, 'low': float, 'close': float})
    
    print(f"Loaded {len(df)} candles.")
    
    # Execution
    entries, exits = strategy_vectorized(df, params={})
    
    long_entries = (entries == 1).astype(bool)
    long_exits = (exits == 1).astype(bool)
    short_entries = (entries == -1).astype(bool)
    short_exits = (exits == -1).astype(bool)
    
    print(f"Signals detected: Long={long_entries.sum()}, Short={short_entries.sum()}")
    
    if long_entries.sum() == 0 and short_entries.sum() == 0:
        print("No signals generated.")
        return

    # Portfolio
    pf = vbt.Portfolio.from_signals(
        df['close'],
        entries=long_entries,
        exits=long_exits,
        short_entries=short_entries,
        short_exits=short_exits,
        init_cash=10000.0,
        fees=0.0001,
        slippage=0.0001
    )
    
    stats = pf.stats()
    print("\n" + "=" * 70)
    print("PERFORMANCE METRICS")
    print("=" * 70)
    print(stats)
    
    # Save Results
    results = {
        "metrics": stats.to_dict(),
        "total_trades": int(stats.get('Total Trades', 0)),
        "win_rate": float(stats.get('Win Rate [%]', 0)),
        "total_return_pct": float(stats.get('Total Return [%]', 0)),
        "max_drawdown_pct": float(stats.get('Max Drawdown [%]', 0))
    }
    
    with open('/app/quasimodo_backtest_results.json', 'w') as f:
        json.dump(results, f, indent=4, default=str)
    
    print(f"\nResults saved to /app/quasimodo_backtest_results.json")

if __name__ == "__main__":
    main()
