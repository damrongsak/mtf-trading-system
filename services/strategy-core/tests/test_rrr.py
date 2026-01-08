import pandas as pd
import pytest
from app.logic import calculate_target_price, check_rrr, SignalDirection
from app.smc import detect_order_blocks

# Mocking detect_order_blocks to control test data without relying on complex candle patterns
def mock_detect_order_blocks(df_h1):
    # Determine scenario based on a marker in the dataframe (hack for testing without DI)
    if 'scenario' not in df_h1.attrs:
        return []
        
    scenario = df_h1.attrs['scenario']
    
    if scenario == 'bullish_with_target':
        return [{
            "type": "bearish",
            "bottom": 2020.0, # Target above entry (e.g. 2010)
            "top": 2025.0,
            "index": 10
        }]
    elif scenario == 'bearish_with_target':
        return [{
            "type": "bullish",
            "top": 1980.0, # Target below entry (e.g. 1990)
            "bottom": 1975.0,
            "index": 10
        }]
    elif scenario == 'bad_rrr':
         return [{
            "type": "bearish",
            "bottom": 2002.0, # Target too close to entry (2000)
            "top": 2005.0,
            "index": 10
        }]
        
    return []

# Monkey patch
import app.logic
app.logic.detect_order_blocks = mock_detect_order_blocks


def test_calculate_target_price_fallback():
    # Setup dummy DF
    df = pd.DataFrame({'close': [100]})
    
    entry = 2000.0
    sl = 1990.0 # Risk = 10
    
    # 1. Bullish Fallback (No OBs)
    target = calculate_target_price(df, SignalDirection.BULLISH, entry, sl)
    # Expect 2R = 2000 + (10 * 2) = 2020
    assert target == 2020.0
    
    # 2. Bearish Fallback
    entry = 2000.0
    sl = 2010.0 # Risk = 10
    target = calculate_target_price(df, SignalDirection.BEARISH, entry, sl)
    # Expect 2R = 2000 - (10 * 2) = 1980
    assert target == 1980.0

def test_calculate_target_price_with_ob():
    df = pd.DataFrame({'close': [100]})
    entry = 2000.0
    sl = 1990.0
    
    # Case: Bullish with OB at 2020 (2R)
    df.attrs['scenario'] = 'bullish_with_target'
    target = calculate_target_price(df, SignalDirection.BULLISH, entry, sl)
    assert target == 2020.0
    
    # Case: Bearish with OB at 1980 (2R)
    df.attrs['scenario'] = 'bearish_with_target'
    entry = 2000.0
    sl = 2010.0
    target = calculate_target_price(df, SignalDirection.BEARISH, entry, sl)
    assert target == 1980.0

def test_check_rrr():
    entry = 2000.0
    sl = 1990.0 # Risk 10
    
    # Case 1: Target 2020 -> Reward 20. RRR = 2.0. Pass
    assert check_rrr(entry, sl, 2020.0) == True
    
    # Case 2: Target 2015 -> Reward 15. RRR = 1.5. Pass
    assert check_rrr(entry, sl, 2015.0) == True
    
    # Case 3: Target 2014 -> Reward 14. RRR = 1.4. Fail
    assert check_rrr(entry, sl, 2014.0) == False
    
    # Case 4: Zero Risk (should not divide by zero)
    assert check_rrr(entry, entry, 2020.0) == False

@pytest.mark.asyncio
async def test_smc_v1_strategy_rrr_integration():
    from app.registry import smc_v1_strategy
    from app.logic import SignalDirection
    from unittest.mock import MagicMock
    import pandas as pd
    import numpy as np
    
    # Mock State and DataManager
    state = MagicMock()
    state.symbol = "XAUUSD"
    state.timeframe = "M15"
    
    data_manager = MagicMock()
    
    # Create fake OHLC data
    # We need enough data to survive resampling (100+ rows)
    dates = pd.date_range(start='2024-01-01', periods=200, freq='15min')
    df = pd.DataFrame({
        'timestamp': dates,
        'open': 2000.0,
        'high': 2005.0,
        'low': 1995.0,
        'close': 2000.0,
        'volume': 1000
    })
    
    # Make the last few candles specific to trigger the strategy
    # 1. Macro Bias (H4): Close > EMA200
    # 2. Trigger (M15): Bullish Candle
    
    # We'll monkeypatch the specific checks to force them to pass, 
    # so we focus ONLY on RRR check.
    
    import app.registry
    
    # Mock logic functions
    app.registry.check_macro_bias = MagicMock(return_value=SignalDirection.BULLISH)
    app.registry.check_setup_zone = MagicMock(return_value=True)
    app.registry.check_trigger = MagicMock(return_value=True)
    app.registry.calculate_stop_loss = MagicMock(return_value=1990.0) # SL at 1990 (Risk 10)
    
    # Mock RRR functions
    # Scenario 1: Good RRR
    app.registry.calculate_target_price = MagicMock(return_value=2020.0) # Target 2020 (Reward 20). Ratio 2.0
    app.registry.check_rrr = MagicMock(return_value=True)
    
    data_manager.get_data.return_value = df
    
    # Run Strategy
    signal = await smc_v1_strategy(state, data_manager)
    
    assert signal is not None
    assert signal['direction'] == "BULLISH"
    assert signal['take_profit'] == 2020.0
    
    # Scenario 2: Bad RRR
    app.registry.check_rrr = MagicMock(return_value=False)
    
    signal = await smc_v1_strategy(state, data_manager)
    
    assert signal is None # Should be filtered

