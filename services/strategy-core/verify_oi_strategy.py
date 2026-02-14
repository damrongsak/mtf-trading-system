import asyncio
import pandas as pd
from unittest.mock import MagicMock
from app.strategies.oi_gamma_v1.strategy import strategy, fetch_latest_oi_snapshot
from app.analysis.liquidity_profile import GammaLevel, MarketRegime, LiquidityProfileAnalyzer

# Mock Data Manager
class MockDataManager:
    def get_data(self, symbol):
        # Return 100 candles
        dates = pd.date_range(end=pd.Timestamp.utcnow(), periods=100, freq='1h')
        df = pd.DataFrame({
            'open': [2000.0] * 100,
            'high': [2010.0] * 100,
            'low': [1990.0] * 100,
            'close': [2005.0] * 100, # Current price 2005
            'volume': [1000] * 100
        }, index=dates)
        return df

# Mock Strategy State
class MockState:
    symbol = "XAUUSD"
    config_json = {}

# Mock DB Fetch
async def run_test():
    print("Testing OI Gamma Strategy...")
    
    # Mock the fetch_latest_oi_snapshot function
    # We can't easily mock the module level function without patching, 
    # but we can monkeypatch it here since we imported it.
    
    import app.strategies.oi_gamma_v1.strategy as strategy_module
    
    # Mock OI Data
    mock_oi_data = {
        "records": [
            {'strike': 2000, 'call_oi': 100, 'put_oi': 1000, 'underlying_price': 2010}, # Put Wall
            {'strike': 2050, 'call_oi': 1000, 'put_oi': 100, 'underlying_price': 2010}, # Call Wall
        ],
        "snapshot_at": pd.Timestamp.utcnow(),
        "underlying_futures_price": 2010
    }
    
    strategy_module.fetch_latest_oi_snapshot = MagicMock(return_value=mock_oi_data)
    
    state = MockState()
    manager = MockDataManager()
    
    # Run Strategy
    entries, exits, signal = await strategy(state, manager)
    
    print(f"Signal: {signal}")
    
    if signal:
        print("✅ Strategy generated a signal!")
        print(f"Direction: {signal['direction']}")
        print(f"Reason: {signal['reason']}")
    else:
        print("❌ No signal generated (might be expected if price not near levels)")
        
    # Test Proximity Logic
    # Current Price 2005. Put Wall 2000. Diff 5. Threshold (0.1%) = 2.
    # 5 > 2 -> No Signal. Correct.
    
    # Let's Move Price closer to Put Wall (2000)
    print("\n--- Testing Signal Generation (Price at 2001) ---")
    dates = pd.date_range(end=pd.Timestamp.utcnow(), periods=100, freq='1h')
    df_close = pd.DataFrame({
        'open': [2000.0] * 100,
        'high': [2010.0] * 100,
        'low': [1990.0] * 100,
        'close': [2001.0] * 100, # Price 2001, within 2.0 of 2000
        'volume': [1000] * 100
    }, index=dates)
    
    manager.get_data = MagicMock(return_value=df_close)
    
    entries, exits, signal = await strategy(state, manager)
    print(f"Signal at 2001: {signal}")
    
    if signal and signal['direction'] == 'BULLISH':
        print("✅ Correctly generated BULLISH signal off Put Wall")
    else:
        print("❌ Failed to generate signal")

if __name__ == "__main__":
    asyncio.run(run_test())
