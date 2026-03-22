import pytest
import pandas as pd
import numpy as np
from app.indicators.smc import detect_liquidity_sweeps, calculate_displacement_velocity
from app.analysis.market_regime import detect_expansion, get_market_context
from app.indicators.correlation import calculate_rolling_correlation, detect_smt_divergence

def create_synthetic_data(expansion=False, rows=100):
    prices = [2000.0]
    for i in range(rows - 1):
        change = np.random.normal(0, 5)
        if expansion and i > 80:
            change = 50.0  # Parabolic move
        prices.append(prices[-1] + change)
    
    df = pd.DataFrame({
        'open': prices,
        'high': [p + 2 for p in prices],
        'low': [p - 2 for p in prices],
        'close': [p + 1 for p in prices],
        'volume': [1000] * rows
    })
    return df

def test_momentum_threshold():
    """Verify that hyperbolic expansion triggers the V_d rejection."""
    # Create extreme expansion data
    df = create_synthetic_data(expansion=False, rows=300)
    # 1. Establish a long stable baseline
    df['open'] = 1000.0
    df['close'] = 1001.0
    df['high'] = 1002.0
    df['low'] = 999.0
    df['volume'] = 1000
    
    # 2. Inject a singular massive body in the last bar
    df.loc[df.index[-1], 'open'] = 1000.0
    df.loc[df.index[-1], 'close'] = 10000.0 # 9000% jump
    df.loc[df.index[-1], 'high'] = 10005.0
    df.loc[df.index[-1], 'low'] = 995.0
    df.loc[df.index[-1], 'volume'] = 10000 

    v_d = calculate_displacement_velocity(df)
    # V_d should be absolutely massive now
    assert v_d.iloc[-1] > 15 

def test_expansion_regime():
    """Verify market regime correctly identifies expansion."""
    df = create_synthetic_data(expansion=False, rows=300)
    # 1. Establish a long stable baseline
    df['open'] = 1000.0
    df['close'] = 1001.0
    
    # 2. Inject a singular massive hyperbolic spike at the end
    df.loc[df.index[-1], 'open'] = 1000.0
    df.loc[df.index[-1], 'close'] = 50000.0 # 5000% jump
    
    is_exp = detect_expansion(df)
    assert is_exp is True
    
    context = get_market_context(df)
    assert "EXPANSION_UP" in context['regime']
    # Risk should be reduced during expansion
    assert context['risk_multiplier'] < 1.0

def test_smt_divergence():
    """Verify SMT divergence detection (Inverse)."""
    df_gold = create_synthetic_data(rows=20)
    df_dxy = create_synthetic_data(rows=20)
    
    # Create inverse relationship normally
    for i in range(20):
        df_dxy.loc[df_dxy.index[i], 'close'] = 100 - (df_gold['close'].iloc[i] / 20)
        df_dxy.loc[df_dxy.index[i], 'high'] = 100 - (df_gold['low'].iloc[i] / 20)
        df_dxy.loc[df_dxy.index[i], 'low'] = 100 - (df_gold['high'].iloc[i] / 20)
    
    # Previous Highs
    prev_gold_high = df_gold['high'].iloc[:-1].max()
    prev_dxy_low = df_dxy['low'].iloc[:-1].min()

    # Inject Bearish SMT Divergence (Inverse):
    # Case B: Gold makes HH, DXY FAILS to make LL
    df_gold.loc[df_gold.index[-1], 'high'] = prev_gold_high + 10
    df_dxy.loc[df_dxy.index[-1], 'low'] = prev_dxy_low + 5
    
    res = detect_smt_divergence(df_gold, df_dxy, relationship="inverse")
    assert res['divergence'] == "BEARISH_SMT"

if __name__ == "__main__":
    pytest.main()
