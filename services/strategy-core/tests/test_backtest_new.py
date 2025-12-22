import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
import pandas as pd
from app.backtest import fetch_data_from_db

@pytest.fixture
def mock_db_engine():
    with patch('app.backtest.engine') as mock_engine:
        # Create a mock connection
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        yield mock_engine, mock_conn

def test_fetch_data_from_db_calls_correct_sql(mock_db_engine):
    mock_engine, mock_conn = mock_db_engine
    
    # Setup mock return data
    mock_data = {
        'timestamp': [datetime(2023, 1, 1)],
        'open': [1.0], 
        'high': [1.1], 
        'low': [0.9], 
        'close': [1.0], 
        'volume': [100]
    }
    # pd.read_sql returns a DataFrame
    # We need to mock pd.read_sql
    with patch('app.backtest.pd.read_sql') as mock_read_sql:
        mock_read_sql.return_value = pd.DataFrame(mock_data)
        
        market_symbol_id = "test-uuid"
        timeframe = "H1"
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 2)
        
        df = fetch_data_from_db(market_symbol_id, timeframe, start_date, end_date)
        
        # Verify it called read_sql with correct params
        assert mock_read_sql.called
        call_args = mock_read_sql.call_args
        # args[0] is query, args[1] is conn
        # kwargs['params'] should contain our filters
        
        params = call_args[1]['params']
        assert params['market_symbol_id'] == market_symbol_id
        assert params['timeframe'] == timeframe
        assert params['start_date'] == start_date
        assert params['end_date'] == end_date
        
        # Verify result is a dataframe
        assert not df.empty
        assert 'timestamp' in df.columns
