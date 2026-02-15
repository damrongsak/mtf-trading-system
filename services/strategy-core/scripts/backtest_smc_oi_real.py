
import asyncio
import logging
import pandas as pd
import numpy as np
import vectorbt as vbt
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import sys
import os

# Add service root to path
sys.path.append(os.getcwd())



from app.database import SessionLocal
from app.models.market import MarketSymbol
from app.models.open_interest import OpenInterest
from app.backtest import fetch_data_from_db
from app.strategies.smc_oi_confluence_v1.strategy import strategy

# Configure Logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Helper Classes ---
class MockState:
    def __init__(self, symbol):
        self.symbol = symbol

class MockDataManager:
    def __init__(self, data):
        self.data = data
        
    def get_data(self, symbol):
        return self.data

# --- Main Backtest Logic ---
async def run_backtest(symbol="XAUUSD", days=30):
    logger.info(f"Starting Real Data Backtest for {symbol} ({days} days)...")
    
    db = SessionLocal()
    try:
        # 1. Fetch Market Data
        # Map symbol
        ms = db.query(MarketSymbol).filter(
            (MarketSymbol.symbol == symbol) | (MarketSymbol.symbol == symbol.replace("/", ""))
        ).first()
        
        if not ms:
            logger.error(f"Symbol {symbol} not found in DB")
            return

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        logger.info(f"Fetching Candles from {start_date} to {end_date}...")
        df = fetch_data_from_db(ms.id, "M15", start_date, end_date)
        
        if df.empty:
            logger.error("No candle data found.")
            return

        logger.info(f"Loaded {len(df)} candles.")

        # 2. Fetch All OI Snapshots
        logger.info("Fetching Historical OI Snapshots...")
        oi_records = db.query(OpenInterest).filter(
            OpenInterest.snapshot_at >= start_date
        ).order_by(OpenInterest.snapshot_at.asc()).all()
        
        # Organize OI by timestamp for fast lookup
        # We need a way to find "latest snapshot relative to current candle time"
        # Since loop is sequential, we can just maintain an index or filter.
        # Better: Convert to DataFrame for asof join? Or just list of dicts.
        
        oi_snapshots = []
        # Group by snapshot_at
        from itertools import groupby
        for date, group in groupby(oi_records, key=lambda x: x.snapshot_at):
            records = list(group)
            
            # Calculate Walls
            # Records has .strike, .call_oi, .put_oi
            max_put = max(records, key=lambda x: float(x.put_oi or 0))
            max_call = max(records, key=lambda x: float(x.call_oi or 0))
            
            levels = []
            levels.append({
                'type': 'PUT_WALL',
                'strike': float(max_put.strike),
                'strength': float(max_put.put_oi or 0)
            })
            levels.append({
                'type': 'CALL_WALL',
                'strike': float(max_call.strike),
                'strength': float(max_call.call_oi or 0)
            })
            
            snapshot = {
                "snapshot_at": date,
                "levels": levels
            }
            oi_snapshots.append(snapshot)
            
        logger.info(f"Loaded {len(oi_snapshots)} OI snapshots.")
        
        if not oi_snapshots:
            logger.warning("No OI data found! Backtest operates without OI context (might fail).")

    finally:
        db.close()

    # 3. Execution Loop
    entries = pd.Series(False, index=df.index)
    exits = pd.Series(False, index=df.index)
    
    # Pre-calculate what we can? No, strategy depends on expanding window logic often.
    # But for optimization, we pass slices.
    
    logger.info("Running Strategy Loop...")
    
    # We need a Mock for fetch_latest_oi_snapshot
    # It needs to return the snapshot closest to but not after 'current_time'
    
    current_sim_time = None
    
    def mock_fetch_oi():
        if not current_sim_time or not oi_snapshots:
            return None
        
        # Helper to normalize to naive UTC
        def to_naive(dt):
            if hasattr(dt, 'tz_localize'):
                # Start with simple naive conversion
                if dt.tzinfo is not None:
                    return dt.tz_localize(None)
                return dt
            # Standard datetime
            if dt.tzinfo is not None:
                return dt.replace(tzinfo=None)
            return dt

        sim_time_naive = to_naive(current_sim_time)

        # Find latest snapshot <= current_sim_time
        # Binary search or simple iteration (optimization possible)
        # Since we move forward, we can track index.
        valid_snaps = [s for s in oi_snapshots if to_naive(s["snapshot_at"]) <= sim_time_naive]
        if valid_snaps:
            # Return as object to match strategy expectation (oi_data.levels)
            snap = valid_snaps[-1]
            from types import SimpleNamespace
            return SimpleNamespace(snapshot_at=snap["snapshot_at"], levels=snap["levels"])
        return None

    state = MockState(symbol)
    
    # Patch the function in the strategy module
    with patch('app.strategies.smc_oi_confluence_v1.strategy.fetch_latest_oi_snapshot', side_effect=mock_fetch_oi):
        
        # Iterate (Warmup 50 bars)
        for i in range(50, len(df)):
            if i % 100 == 0:
                print(f"Processing bar {i}/{len(df)}...", end='\r')
                
            current_idx = df.index[i]
            current_sim_time = current_idx # Update time for mock
            
            # Slice data (Lookback)
            # Strategy expects 'data' dataframe.
            # Passing 1000 bars lookback should be enough for SMC
            start_idx = max(0, i - 500)
            window_df = df.iloc[start_idx : i+1]
            
            data_manager = MockDataManager(window_df)
            
            # Execute Strategy
            entry, exit, signal = await strategy(state, data_manager)
            
            if entry is not None and not entry.empty and entry.iloc[-1]:
                entries.iloc[i] = True
                logger.info(f"SIGNAL at {current_idx}: {signal['direction']} | {signal['reason']}")
            
            if exit is not None and not exit.empty and exit.iloc[-1]:
                exits.iloc[i] = True

    # 4. Analysis with VectorBT
    logger.info("\nCalculating Metrics...")
    
    pf = vbt.Portfolio.from_signals(
        df['close'],
        entries,
        exits,
        init_cash=10000,
        fees=0.0005, # Maker/Taker avg
        slippage=0.0005,
        freq='15min'
    )
    
    print("\n" + "="*50)
    print("BACKTEST RESULTS (Real Data)")
    print("="*50)
    print(pf.stats())
    print("="*50)
    
    # Trade List
    trades = pf.trades.records_readable
    if not trades.empty:
        print("\nLast 5 Trades:")
        print(trades.tail())
    else:
        print("\nNo Trades Executed.")

if __name__ == "__main__":
    days = 5
    if len(sys.argv) > 1:
        days = int(sys.argv[1])
    asyncio.run(run_backtest(days=days))
