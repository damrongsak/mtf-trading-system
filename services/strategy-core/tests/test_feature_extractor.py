import pytest
import pandas as pd
import numpy as np
from app.processing.feature_extractor import FeatureExtractor

@pytest.fixture
def sample_data():
    n = 200
    dates = pd.date_range(start='2024-01-01', periods=n, freq='H')
    close = np.linspace(100, 150, n) + np.random.normal(0, 1, n)
    high = close + 2
    low = close - 2
    open_ = close - 1
    volume = np.random.randint(100, 1000, n)
    
    return pd.DataFrame({
        'timestamp': dates,
        'open': open_,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume
    })

def test_extract_returns_none_for_empty_df():
    extractor = FeatureExtractor()
    df = pd.DataFrame()
    assert extractor.extract_from_dataframe(df) is None

def test_extract_returns_none_for_short_df(sample_data):
    extractor = FeatureExtractor()
    df = sample_data.head(10)
    assert extractor.extract_from_dataframe(df) is None

def test_extract_returns_features(sample_data):
    extractor = FeatureExtractor()
    features = extractor.extract_from_dataframe(sample_data, symbol="TEST", timeframe="1h")
    
    assert features is not None
    assert features['type'] == "FEATURE"
    assert features['symbol'] == "TEST"
    assert features['timeframe'] == "1h"
    
    # Check key indicators exist
    assert features['rsi_14'] is not None
    assert features['macd'] is not None
    assert features['bb_upper'] is not None
    
    # Check SMC structure
    assert 'smc' in features
    assert 'structure' in features['smc']

def test_extract_handles_nans(sample_data):
    extractor = FeatureExtractor()
    # Inject some NaNs
    sample_data.loc[190:, 'close'] = np.nan
    
    # Should handle gracefully (might return None for specific indicators but whole object should exist)
    # Actually, if the LAST row has NaNs, the result for that indicator might be None
    features = extractor.extract_from_dataframe(sample_data)
    
    # Just ensure it doesn't crash
    assert features is not None
    assert features['close'] is not None or np.isnan(features['close']) # depending on how latest is retrieved
    
    # safe_float should handle NaNs
    if pd.isna(sample_data.iloc[-1]['close']):
         # If close is NaN, most indicators will be NaN
         pass

