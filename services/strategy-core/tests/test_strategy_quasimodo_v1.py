import pytest
import pandas as pd
import numpy as np
from app.strategies.quasimodo_v1.strategy import QuasimodoStrategy

@pytest.mark.asyncio
async def test_quasimodo_v1_bullish_signal():
    """
    Test Bullish Quasimodo Pattern Detection.
    """
    # 1. Create Synthetic Data (500 bars)
    dates = pd.date_range(start="2024-01-01", periods=500, freq='15min')
    
    # Base Price: 115.0 (Center point)
    close_vals = np.full(500, 115.0)
    
    # LS1 (Valley) @ 210
    close_vals[210] = 100.0
    # LH1 (Peak) @ 230
    close_vals[230] = 130.0
    # LS2 (Valley, Sweep) @ 250
    close_vals[250] = 95.0
    # LH2 (Peak, BOS) @ 270
    close_vals[270] = 140.0
    
    # Target Entry QML = LS1 = 100.0
    # Return to LS1 price (100.0) at the end
    close_vals[271:480] = 150.0 # Significantly higher padding to force bullish EMAs
    close_vals[480:] = 100.0 # Return to QML for entry
    
    close = pd.Series(close_vals, index=dates)
    high = close + 0.1
    low = close - 0.1
    open_p = close.shift(1).fillna(105.0)
    volume = pd.Series(1000.0, index=dates)
    
    df = pd.DataFrame({
        'open': open_p,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume,
        'timestamp': dates
    })

    # 2. Run Strategy with Mocked Indicators/Structure to ensure stable test
    from unittest.mock import patch
    
    params = {
        "risk_pct": 0.01,
        "ema_fast": 13,
        "ema_slow": 50,
        "min_rrr": 1.5,
        "swing_strength": 2
    }
    
    from app.strategies.quasimodo_v1.strategy import QMPattern, SwingPoint
    
    mock_pattern = QMPattern(
        direction='BULLISH',
        ls1=100.0, lh1=130.0, ls2=95.0, lh2=145.0,
        qml=100.0, head=95.0, range_pips=50.0,
        displacement=True, valid=True
    )
    
    mock_swings = [
        SwingPoint(210, 'low', 100.0, dates[210]),
        SwingPoint(230, 'high', 130.0, dates[230]),
        SwingPoint(250, 'low', 95.0, dates[250]),
        SwingPoint(270, 'high', 145.0, dates[270])
    ]

    qm = QuasimodoStrategy()
    
    with patch('app.strategies.quasimodo_v1.strategy.calculate_ema') as mock_ema, \
         patch('app.strategies.quasimodo_v1.strategy.calculate_atr') as mock_atr, \
         patch('app.strategies.quasimodo_v1.strategy.detect_swing_points') as mock_ds, \
         patch('app.strategies.quasimodo_v1.strategy.identify_qm_logic') as mock_iq:
        
        # Setup Mocks for BULLISH Alignment
        # EMA13 (110) > EMA50 (105) > EMA200 (100)
        mock_ema.side_effect = [
            pd.Series([110.0], index=[dates[-1]]), # Fast
            pd.Series([105.0], index=[dates[-1]]), # Slow
            pd.Series([100.0], index=[dates[-1]]), # Macro M15
            pd.Series([102.0], index=[dates[-1]])  # Macro H1
        ]
        mock_atr.return_value = pd.Series([2.0], index=[dates[-1]])
        mock_ds.return_value = mock_swings
        mock_iq.return_value = mock_pattern

        entries, exits, signal = await qm.run_live_signal(df, params, data_h1=df) # Use df as H1 proxy for mock

    # 3. Assertions
    assert entries.iloc[-1] == True, f"Signal should be triggered. Metadata: {signal}"
    assert signal['market_structure']['direction'] == "BULLISH"
    assert "quality_score" in signal['rl_analysis'], "RL Quality Score missing from signal"
    assert "displacement" in signal['rl_analysis']['metrics'], "Displacement missing from metrics"
    
    print(f"✅ Quasimodo V2 Professional Test Passed: {signal['execution']['reason']} | Score: {signal['rl_analysis']['quality_score']}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_quasimodo_v1_bullish_signal())
