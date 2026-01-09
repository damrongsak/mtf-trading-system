import pytest
import pandas as pd
import numpy as np
from app.indicators import calculate_indicator

def test_calculate_indicator():
    # Create sample DataFrame with more realistic data (not pure random)
    # to ensure pandas-ta can calculate indicators correctly
    np.random.seed(42)
    close = np.cumsum(np.random.randn(100)) + 100
    data = {
        "close": close,
        "high": close + 1,
        "low": close - 1,
        "open": close,
        "volume": np.random.randint(100, 1000, 100)
    }
    df = pd.DataFrame(data)
    
    # Calculate indicators
    df_result = calculate_indicator(df, strategy="Common")
    
    # Check if indicators were added
    columns = df_result.columns.tolist()
    
    # Check for at least one expected indicator column
    # pandas_ta adds columns like SMA_50, RSI_14, etc.
    has_rsi = any("RSI" in col for col in columns)
    has_sma = any("SMA" in col for col in columns)
    has_atr = any("ATR" in col for col in columns)
    
    assert has_rsi or has_sma or has_atr, f"No indicators found in {columns}"