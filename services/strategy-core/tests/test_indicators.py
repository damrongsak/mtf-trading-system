import pandas as pd
import numpy as np
import pytest
from app.indicators import (
    calculate_ema, 
    calculate_atr, 
    calculate_rsi, 
    calculate_macd, 
    calculate_bbands, 
    calculate_adx,
    calculate_volume_profile
)

@pytest.fixture
def ohlcv_data():
    # Create synthetic OHLCV data
    n = 100
    dates = pd.date_range(start='2024-01-01', periods=n, freq='H')
    close = np.linspace(100, 150, n) + np.random.normal(0, 1, n)
    high = close + 2
    low = close - 2
    open_ = close - 1
    volume = np.random.randint(100, 1000, n)
    
    return pd.DataFrame({
        'open': open_,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume
    }, index=dates)

def test_calculate_ema(ohlcv_data):
    close = ohlcv_data['close']
    ema = calculate_ema(close, span=20)
    
    assert isinstance(ema, pd.Series)
    assert len(ema) == len(close)
    assert not ema.isna().all()

def test_calculate_atr(ohlcv_data):
    atr = calculate_atr(ohlcv_data['high'], ohlcv_data['low'], ohlcv_data['close'], window=14)
    
    assert isinstance(atr, pd.Series)
    assert len(atr) == len(ohlcv_data)
    # ATR should be generally positive
    assert (atr.dropna() > 0).all()

def test_calculate_rsi(ohlcv_data):
    rsi = calculate_rsi(ohlcv_data['close'], window=14)
    
    assert isinstance(rsi, pd.Series)
    assert len(rsi) == len(ohlcv_data)
    # RSI between 0 and 100
    valid_rsi = rsi.dropna()
    assert (valid_rsi >= 0).all() and (valid_rsi <= 100).all()

def test_calculate_macd(ohlcv_data):
    macd_df = calculate_macd(ohlcv_data['close'])
    
    assert isinstance(macd_df, pd.DataFrame)
    assert len(macd_df) == len(ohlcv_data)
    # Check standardized columns
    assert 'macd' in macd_df.columns
    assert 'signal' in macd_df.columns
    assert 'hist' in macd_df.columns

def test_calculate_bbands(ohlcv_data):
    bb = calculate_bbands(ohlcv_data['close'])
    
    assert isinstance(bb, pd.DataFrame)
    assert len(bb) == len(ohlcv_data)
    assert 'upper' in bb.columns
    assert 'lower' in bb.columns
    assert 'middle' in bb.columns
    # Basic logic check: Upper > Lower
    valid = bb.dropna()
    assert (valid['upper'] >= valid['lower']).all()

def test_calculate_adx(ohlcv_data):
    adx_df = calculate_adx(ohlcv_data['high'], ohlcv_data['low'], ohlcv_data['close'], length=14)
    
    assert isinstance(adx_df, pd.DataFrame)
    assert len(adx_df) == len(ohlcv_data)
    # Check normalized lowercase columns
    assert 'adx' in adx_df.columns
    assert 'dmp' in adx_df.columns
    assert 'dmn' in adx_df.columns

def test_calculate_volume_profile(ohlcv_data):
    vp = calculate_volume_profile(ohlcv_data['close'], ohlcv_data['volume'], bins=10)
    
    assert isinstance(vp, pd.DataFrame)
    assert len(vp) == 10 # Bins
    assert 'price_level' in vp.columns
    assert 'volume' in vp.columns
    # Total volume in profile should approx match total volume (simple bucketing)
    # It won't match exactly if we drop NaNs or clipping issues, but here we cover full range
    assert vp['volume'].sum() == ohlcv_data['volume'].sum()
