
import pytest
import pandas as pd
from app.market_data import SharedMarketDataManager
from datetime import datetime, timedelta

def test_market_data_update_tick_order_flow():
    manager = SharedMarketDataManager()
    symbol = "TEST_USD"
    start_time = datetime(2025, 1, 1, 10, 0, 0)
    
    # 1. First Tick (Neutral)
    manager.update_tick(symbol, 100.0, start_time)
    df = manager.get_data(symbol)
    assert len(df) == 1
    assert df.iloc[0]['delta'] == 0 # First tick neutral
    assert len(df.iloc[0]['footprint']) == 1
    assert df.iloc[0]['footprint'][0]['price'] == 100.0
    
    # 2. Buy Tick (Price Up)
    manager.update_tick(symbol, 100.1, start_time + timedelta(seconds=1))
    df = manager.get_data(symbol)
    print(df.iloc[-1]['footprint'])
    assert df.iloc[0]['close'] == 100.1
    # Delta should be +1 (1 tick buy)
    # But wait, logic: if side == 1: delta += 1.
    # Previous delta was 0. So 0 + 1 = 1.
    assert df.iloc[0]['delta'] == 1.0
    
    # Check Footprint
    # Should have entry for 100.1 with ask_vol=1
    fp = df.iloc[0]['footprint']
    level_100_1 = next((x for x in fp if x['price'] == 100.1), None)
    assert level_100_1 is not None
    assert level_100_1['ask_vol'] == 1.0
    
    # 3. Sell Tick (Price Down)
    manager.update_tick(symbol, 100.0, start_time + timedelta(seconds=2))
    df = manager.get_data(symbol)
    # Delta: 1 - 1 = 0
    assert df.iloc[0]['delta'] == 0.0
    level_100 = next((x for x in df.iloc[0]['footprint'] if x['price'] == 100.0), None)
    assert level_100['bid_vol'] == 1.0 # 1 from sell tick
    
    # 4. Continuation (Same Price)
    # Logic says: side = 0.
    # Delta shouldn't change?
    manager.update_tick(symbol, 100.0, start_time + timedelta(seconds=3))
    df = manager.get_data(symbol)
    assert df.iloc[0]['delta'] == 0.0
    
    # Volume check
    assert df.iloc[0]['volume'] == 4.0 # 4 ticks
