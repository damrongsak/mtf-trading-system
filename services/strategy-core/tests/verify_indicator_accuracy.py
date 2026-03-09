import pandas as pd
import numpy as np
import sys
import os

# Add service path to sys.path
sys.path.append("/app")

from app.indicators.trend import calculate_ema
from app.indicators.volatility import calculate_atr

def test_ema_accuracy():
    print("Testing EMA Accuracy...")
    # Create simple data: 1, 2, 3, 4, 5
    data = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    span = 3
    
    # Standard Pandas EWM formula (adjust=False):
    # EMA_0 = Price_0
    # EMA_t = alpha * Price_t + (1 - alpha) * EMA_{t-1}
    # where alpha = 2 / (span + 1)
    
    # For span=3, alpha = 2/4 = 0.5
    # EMA_0 = 1.0
    # EMA_1 = 0.5 * 2.0 + 0.5 * 1.0 = 1.0 + 0.5 = 1.5
    # EMA_2 = 0.5 * 3.0 + 0.5 * 1.5 = 1.5 + 0.75 = 2.25
    # EMA_3 = 0.5 * 4.0 + 0.5 * 2.25 = 2.0 + 1.125 = 3.125
    # EMA_4 = 0.5 * 5.0 + 0.5 * 3.125 = 2.5 + 1.5625 = 4.0625
    
    expected = [1.0, 1.5, 2.25, 3.125, 4.0625]
    result = calculate_ema(data, span=span)
    
    print(f"EMA Result: {result.tolist()}")
    print(f"Expected: {expected}")
    
    for r, e in zip(result.tolist(), expected):
        assert abs(r - e) < 1e-6, f"EMA mismatch: {r} != {e}"
    
    print("✅ EMA Accuracy Verified.")

def test_atr_accuracy():
    print("Testing ATR Accuracy...")
    # Create data with known TR
    # TR = max(H-L, |H-Cp|, |L-Cp|)
    high = pd.Series([10.0, 12.0, 15.0, 14.0, 16.0])
    low = pd.Series([8.0, 10.0, 13.0, 11.0, 14.0])
    close = pd.Series([9.0, 11.0, 14.0, 12.0, 15.0])
    
    # TR:
    # 0: 10-8 = 2
    # 1: max(12-10, |12-9|, |10-9|) = max(2, 3, 1) = 3
    # 2: max(15-13, |15-11|, |13-11|) = max(2, 4, 2) = 4
    # 3: max(14-11, |14-14|, |11-14|) = max(3, 0, 3) = 3
    # 4: max(16-14, |16-12|, |14-12|) = max(2, 4, 2) = 4
    
    # ATR(3) using Wilder's smoothing (standard in VectorBT/TradingView)
    # ATR_0 (SMA fallback for first 3): (2 + 3 + 4) / 3 = 3.0
    # ATR_1: (3.0 * (3-1) + 3) / 3 = (6 + 3) / 3 = 3.0
    # ATR_2: (3.0 * (3-1) + 4) / 3 = (6 + 4) / 3 = 3.3333333
    
    # VectorBT ATR usually matches TA-Lib/Wilder's
    result = calculate_atr(high, low, close, window=3)
    
    print(f"ATR Result (latest): {result.iloc[-1]}")
    # We expect roughly 3.3333 for the last bar if window=3
    assert abs(result.iloc[-1] - 3.3333333) < 1e-6, f"ATR mismatch: {result.iloc[-1]}"
    
    print("✅ ATR Accuracy Verified.")

if __name__ == "__main__":
    try:
        test_ema_accuracy()
        test_atr_accuracy()
        print("\n🎉 All Indicators Verified for Accuracy!")
    except Exception as e:
        print(f"\n❌ Verification Failed: {e}")
        sys.exit(1)
