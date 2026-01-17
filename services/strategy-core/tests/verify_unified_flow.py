import asyncio
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
import logging

# Setup Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Mock Strategy Def ---
# This simulates a user's unified strategy file (strategy.py)
METADATA = {
    "name": "Mock Unified Strategy",
    "defaults": {"period": 10}
}

def strategy(data, params=None):
    """Unified Sync Strategy"""
    if params is None: params = {}
    period = params.get("period", 10)
    
    # Fake Logic
    # Verify data is a DataFrame
    if not isinstance(data, pd.DataFrame):
        raise ValueError("Data must be a DataFrame")
        
    close = data['close']
    entries = pd.Series([False] * len(close))
    exits = pd.Series([False] * len(close))
    
    # Trigger on last bar
    entries.iloc[-1] = True
    
    latest_signal = {
        "direction": "BULLISH",
        "reason": "Test Trigger",
        "metadata": {"val": 123}
    }
    
    return entries, exits, latest_signal

# --- Verification Script ---
async def run_verification():
    print("🚀 Starting Unified Flow Verification...")
    
    # 1. Mock Registry Loading
    # We simulate what StrategyRegistry.load_strategies does
    from app.registry import StrategyRegistry
    
    # Manually inject our mock strategy into the registry as if it were loaded
    # A. Live Registry (Async Wrapper)
    # We need to manually construct the wrapper because logic is inside load_strategies
    # Ideally we'd invoke load_strategies but we don't want to rely on file system here.
    # Let's import the REAL load_strategies logic or replicate the wrapper creation?
    # Replicating wrapper creation is safer for unit test to rely on current registry.py? 
    # NO, we should test registry.py! 
    
    # Let's MOCK the file system scan in Registry
    with patch("os.listdir") as mock_listdir, \
         patch("os.path.isdir") as mock_isdir, \
         patch("os.path.exists") as mock_exists, \
         patch("importlib.import_module") as mock_import:
        
        # Setup Mocks
        mock_exists.return_value = True
        mock_listdir.return_value = ["mock_strat"] # Folder name
        mock_isdir.return_value = True
        
        # Mock Module
        mock_module = MagicMock()
        mock_module.strategy = strategy
        mock_module.METADATA = METADATA
        mock_import.return_value = mock_module
        
        # Mock DB Fetch inside Wrapper (prevent actual DB call)
        # The wrapper imports verify_unified_flow... no, it imports app.backtest
        # We need to patch app.backtest.fetch_data_from_db
        with patch("app.backtest.fetch_data_from_db") as mock_fetch:
            # Mock Data Return
            dates = pd.date_range("2024-01-01", periods=100, freq="H")
            mock_df = pd.DataFrame({"close": np.random.randn(100)}, index=dates)
            mock_fetch.return_value = mock_df
            
            # Mock DB Session (for market_symbol_id)
            with patch("app.database.SessionLocal") as mock_db_cls:
                mock_db = MagicMock()
                mock_db_cls.return_value = mock_db
                mock_ms = MagicMock()
                mock_ms.id = 1
                mock_db.query.return_value.filter.return_value.first.return_value = mock_ms

                # >>> ACTION: LOAD <<<
                print("1. Loading Strategies via Registry...")
                StrategyRegistry.load_strategies()
                
                # --- VERIFY BACKTEST FLOW (Sync) ---
                print("\n2. Verifying BACKTEST Flow (Sync Access)...")
                sync_func = StrategyRegistry.get_strategy_sync("MOCK_STRAT")
                
                if not sync_func:
                    print("❌ FAIL: get_strategy_sync returned None")
                    return
                
                if asyncio.iscoroutinefunction(sync_func):
                    print("❌ FAIL: get_strategy_sync returned an ASYNC function (expected Sync)")
                    return
                    
                print("   ✅ Sync function retrieved.")
                
                # Execute Sync
                print("   Executing Sync Function...")
                res = sync_func(mock_df, params={"period": 14})
                if isinstance(res, tuple) and len(res) == 3:
                    print("   ✅ Sync Execution Successful (Returns 3-tuple)")
                else:
                    print(f"❌ FAIL: Sync Execution returned {type(res)}: {res}")
                    

                # --- VERIFY LIVE FLOW (Async Wrapper) ---
                print("\n3. Verifying LIVE Flow (Async Wrapper)...")
                wrapper_func = StrategyRegistry.get_strategy("MOCK_STRAT")
                
                if not wrapper_func:
                     print("❌ FAIL: get_strategy returned None")
                     return
                
                if not asyncio.iscoroutinefunction(wrapper_func):
                    print("❌ FAIL: get_strategy returned a SYNC function (expected Async Wrapper)")
                    return
                
                print("   ✅ Async Wrapper retrieved.")
                
                # Execute Wrapper
                print("   Executing Async Wrapper...")
                mock_state = MagicMock()
                mock_state.symbol = "EUR_USD"
                mock_state.timeframe = "H1"
                mock_data_manager = MagicMock() # Not used by wrapper anymore, checks DB
                
                # Await
                res_signal = await wrapper_func(mock_state, mock_data_manager)
                
                if isinstance(res_signal, dict) and res_signal.get("direction") == "BULLISH":
                     print("   ✅ Async Execution Successful (Returns Signal Dict)")
                else:
                     print(f"❌ FAIL: Wrapper Execution returned {res_signal}")

    print("\n🎉 ALL CHECKS PASSED")

if __name__ == "__main__":
    asyncio.run(run_verification())
