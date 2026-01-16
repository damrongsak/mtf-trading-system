import pandas as pd
import pytest
from unittest.mock import MagicMock, patch
from app.logic import calculate_target_price, check_rrr, SignalDirection

# Mock function for detect_order_blocks
def mock_detect_order_blocks(df_h1):
    if 'scenario' not in df_h1.attrs:
        return []
    scenario = df_h1.attrs['scenario']
    if scenario == 'bullish_with_target':
        return [{
            "type": "bearish",
            "bottom": 2020.0,
            "top": 2025.0,
            "index": 10
        }]
    elif scenario == 'bearish_with_target':
        return [{
            "type": "bullish",
            "top": 1980.0,
            "bottom": 1975.0,
            "index": 10
        }]
    elif scenario == 'bad_rrr':
         return [{
            "type": "bearish",
            "bottom": 2002.0,
            "top": 2005.0,
            "index": 10
        }]
    return []

def test_calculate_target_price_fallback():
    df = pd.DataFrame({'close': [100]})
    entry = 2000.0
    sl = 1990.0
    
    with patch("app.logic.detect_order_blocks", return_value=[]):
        target = calculate_target_price(df, SignalDirection.BULLISH, entry, sl)
        assert target == 2020.0
        
        entry = 2000.0
        sl = 2010.0
        target = calculate_target_price(df, SignalDirection.BEARISH, entry, sl)
        assert target == 1980.0

def test_calculate_target_price_with_ob():
    df = pd.DataFrame({'close': [100]})
    entry = 2000.0
    sl = 1990.0
    
    with patch("app.logic.detect_order_blocks", side_effect=mock_detect_order_blocks):
        df.attrs['scenario'] = 'bullish_with_target'
        target = calculate_target_price(df, SignalDirection.BULLISH, entry, sl)
        assert target == 2020.0
        
        df.attrs['scenario'] = 'bearish_with_target'
        entry = 2000.0
        sl = 2010.0
        target = calculate_target_price(df, SignalDirection.BEARISH, entry, sl)
        assert target == 1980.0

def test_check_rrr():
    entry = 2000.0
    sl = 1990.0
    assert check_rrr(entry, sl, 2020.0) == True
    assert check_rrr(entry, sl, 2015.0) == True
    assert check_rrr(entry, sl, 2014.0) == False
    assert check_rrr(entry, entry, 2020.0) == False

@pytest.mark.asyncio
async def test_smc_v1_strategy_rrr_integration():
    from app.strategies.smc_v1.strategy import strategy as smc_v1_strategy
    
    state = MagicMock()
    state.symbol = "XAUUSD"
    state.timeframe = "M15"
    data_manager = MagicMock()
    
    dates = pd.date_range(start='2024-01-01', periods=200, freq='15min')
    df = pd.DataFrame({
        'timestamp': dates,
        'open': 2000.0, 'high': 2005.0, 'low': 1995.0, 'close': 2000.0, 'volume': 1000
    })
    data_manager.get_data.return_value = df

    # Properly patch the registry functions
    with patch("app.registry.check_macro_bias", return_value=SignalDirection.BULLISH), \
         patch("app.registry.check_setup_zone", return_value=True), \
         patch("app.registry.check_trigger", return_value=True), \
         patch("app.registry.calculate_stop_loss", return_value=1990.0), \
         patch("app.registry.calculate_target_price", return_value=2020.0), \
         patch("app.registry.check_rrr", return_value=True):
        
        signal = await smc_v1_strategy(state, data_manager)
        assert signal is not None
        assert signal['direction'] == "BULLISH"
        assert signal['take_profit'] == 2020.0

    with patch("app.registry.check_macro_bias", return_value=SignalDirection.BULLISH), \
         patch("app.registry.check_setup_zone", return_value=True), \
         patch("app.registry.check_trigger", return_value=True), \
         patch("app.registry.calculate_stop_loss", return_value=1990.0), \
         patch("app.registry.calculate_target_price", return_value=2020.0), \
         patch("app.registry.check_rrr", return_value=False):
        
        signal = await smc_v1_strategy(state, data_manager)
        assert signal is None