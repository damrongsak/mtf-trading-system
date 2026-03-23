import pytest
import pandas as pd
import numpy as np
from app.strategies.quasimodo_v1.strategy import QuasimodoStrategy

@pytest.mark.asyncio
async def test_quasimodo_v1_bullish_signal():
    """
    Test Bullish Quasimodo Pattern Detection.
    """
    # 1. Create Synthetic Data (300 bars)
    dates = pd.date_range(start="2024-01-01", periods=300, freq='15min')
    
    # Base Price: 105.0
    close_vals = np.full(300, 105.0)
    
    # LS1 (Valley)
    close_vals[210] = 100.0
    # LH1 (Peak)
    close_vals[230] = 110.0
    # LS2 (Valley, Sweep)
    close_vals[250] = 98.0
    # LH2 (Peak, BOS)
    close_vals[270] = 115.0
    
    # Trigger Point (Index -1)
    # Return to LS1 price (100.0)
    # EMA must be below 100.0. If base is 105, EMA will be ~105.
    # So we need to drop the base price after LH2.
    close_vals[271:-1] = 98.0
    close_vals[-1] = 100.0 
    
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
        'time': dates
    })

    # 2. Run Strategy
    params = {
        "risk_pct": 0.01,
        "ema_fast": 13,
        "ema_slow": 50,
        "min_rrr": 1.5,
        "swing_strength": 2
    }
    
    qm = QuasimodoStrategy()
    is_entry, is_exit, signal = await qm.run_live_signal(df, params)

    # 3. Assertions
    assert is_entry is True, f"Signal should be triggered. Metadata: {signal}"
    assert signal['direction'] == "BULLISH"
    assert "knowledge_score" in signal, "Semantic Multiplier (Km) missing from signal"
    assert "displacement" in signal['metadata']['pattern'], "Displacement missing from metadata"
    
    print(f"✅ Quasimodo V1 Test Passed: {signal['reason']} | Km: {signal['knowledge_score']}x")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_quasimodo_v1_bullish_signal())
