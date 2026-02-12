
import pytest
import pandas as pd
import numpy as np
from app.analysis.market_regime import detect_regime, detect_fakeout_alignment, MarketRegime, calculate_dynamic_risk

@pytest.fixture
def mock_trending_df():
    # Create a synthetic trending DF (High ADX)
    # Price steadily increasing
    dates = pd.date_range(start='2024-01-01', periods=100, freq='15min')
    close = np.linspace(100, 200, 100)
    high = close + 2
    low = close - 2
    open_ = close - 1
    
    return pd.DataFrame({
        'open': open_,
        'high': high,
        'low': low,
        'close': close,
        'volume': 1000
    }, index=dates)

@pytest.fixture
def mock_ranging_df():
    # Create a synthetic ranging DF (Low ADX)
    dates = pd.date_range(start='2024-01-01', periods=100, freq='15min')
    # Sine wave with HIGH frequency (Period ~ 10 bars < ADX 14)
    x = np.linspace(0, 20*np.pi, 100) 
    close = 150 + 5 * np.sin(x)
    high = close + 1
    low = close - 1
    open_ = close - 0.5
    
    return pd.DataFrame({
        'open': open_,
        'high': high,
        'low': low,
        'close': close,
        'volume': 1000
    }, index=dates)

def test_detect_regime_trending(mock_trending_df):
    # With perfect linear thrend, ADX should be maxed out (100)
    regime = detect_regime(mock_trending_df)
    # Direction is UP
    assert regime == MarketRegime.TRENDING_UP

def test_detect_regime_ranging(mock_ranging_df):
    # Sine wave should produce lower ADX eventually
    # Note: ADX calculation needs some warmup
    regime = detect_regime(mock_ranging_df)
    # Might be RANGING or UNSTABLE depending on vectorbt implementation
    assert regime in [MarketRegime.RANGING, MarketRegime.UNSTABLE]

def test_detect_fakeout_alignment():
    # Create a scenario: Price sweeps a high and closes lower (Bearish SFP)
    dates = pd.date_range(start='2024-01-01', periods=20, freq='15min')
    df = pd.DataFrame({
        'open': [100]*20,
        'high': [102]*20,
        'low': [98]*20,
        'close': [100]*20,
        'volume': [1000]*20
    }, index=dates)
    
    # Modify last few candles to create a sweep
    # Candle -2: Established High at 105
    df.iloc[-4] = [100, 105, 98, 100, 1000] # High is 105
    
    # Candle -1: Sweep High (106) but Close Low (99)
    df.iloc[-1] = [100, 106, 99, 99, 5000] # Bearish SFP
    
    # Bias is BEARISH context
    fakeout = detect_fakeout_alignment(df, "BEARISH")
    assert fakeout == "SFP_HIGH"
    
    # Bias is BULLISH context (Trap against us?)
    fakeout_bull = detect_fakeout_alignment(df, "BULLISH")
    # A Bearish SFP (Sweep High) is NOT a fakeout aligning with a BULLISH bias (Sweep Low).
    # Wait, detect_fakeout_alignment returns the type of trap found IF it matches the bias?
    # No, logic says:
    # if last_sweep['type'] == 'bearish_sweep' and bias == 'BEARISH': return "SFP_HIGH"
    # So if we are Bearish, and see a Bearish Sweep, we confirm SFP_HIGH.
    
    # If we are Bullish, we want to see a Bullish Sweep (SFP_LOW).
    # Here we have a Bearish Sweep.
    assert fakeout_bull is None

def test_dynamic_risk():
    # 1. Trend Trade + No Fakeout = 1.0x
    r1 = calculate_dynamic_risk(MarketRegime.TRENDING_UP, is_fakeout=False, base_risk=100)
    assert r1 == 100.0
    
    # 2. Range Trade + Fakeout (SFP) = 1.2x (High Conviction)
    r2 = calculate_dynamic_risk(MarketRegime.RANGING, is_fakeout=True, base_risk=100)
    assert r2 == 120.0
    
    # 3. Trend Trade + Fakeout (Fading Trend?) = 0.5x
    r3 = calculate_dynamic_risk(MarketRegime.TRENDING_UP, is_fakeout=True, base_risk=100)
    assert r3 == 50.0
