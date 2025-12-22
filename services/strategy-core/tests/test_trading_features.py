
import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
from datetime import datetime
# from app.adapters.oanda_history import OandaHistoryAdapter
from app.indicators import calculate_indicator
import app.indicators
print(f"DEBUG: app.indicators dir: {dir(app.indicators)}")

@pytest.fixture
def mock_oanda_adapter():
    with patch('app.adapters.oanda_history.SessionLocal') as mock_db, \
         patch('app.adapters.oanda.SessionLocal') as mock_db_parent:
        mock_session = MagicMock()
        mock_db.return_value = mock_session
        mock_db_parent.return_value = mock_session
        
        # Mock DataSource query
        mock_ds = MagicMock()
        mock_ds.id = "test-id"
        mock_ds.config_json = {"account_id": "123", "token": "abc"}
        mock_session.query.return_value.filter.return_value.first.return_value = mock_ds
        
        # with patch('v20.Context') as mock_context:
        #     adapter = OandaHistoryAdapter()
        #     yield adapter, mock_context
        yield None, None

def test_fetch_candles_range(mock_oanda_adapter):
    adapter, mock_context = mock_oanda_adapter
    
    # Mock v20 response
    mock_response = MagicMock()
    mock_response.status = 200
    
    mock_candle = MagicMock()
    mock_candle.complete = True
    mock_candle.time = "2023-01-01T00:00:00Z"
    mock_candle.mid.o = 1.0
    mock_candle.mid.h = 1.1
    mock_candle.mid.l = 0.9
    mock_candle.mid.c = 1.05
    mock_candle.volume = 100
    
    mock_response.get.return_value = [mock_candle]
    adapter.ctx.instrument.candles.return_value = mock_response
    
    # Test fetch
    df = adapter.fetch_candles_range("EUR_USD", "H1", count=10)
    
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "close" in df.columns
    assert df.iloc[0]["close"] == 1.05

def test_calculate_indicator():
    # Create sample DataFrame
    data = {
        "close": np.random.random(100),
        "high": np.random.random(100),
        "low": np.random.random(100),
        "open": np.random.random(100),
        "volume": np.random.random(100)
    }
    df = pd.DataFrame(data)
    
    # Calculate indicators
    df_result = calculate_indicator(df, strategy="Common")
    
    # Check if indicators were added
    # Common strategy adds SMA_50, SMA_200, RSI_14, ATR_14 (approx names)
    # pandas_ta column names can vary slightly but usually match standard patterns
    
    columns = df_result.columns.tolist()
    # Check for at least one expected indicator column
    # e.g. RSI_14 or similar
    
    has_rsi = any("RSI" in col for col in columns)
    assert has_rsi
