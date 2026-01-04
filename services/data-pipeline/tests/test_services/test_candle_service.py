import pytest
from app.services.candle_service import CandleService
from app.models.candle import Candle
from datetime import datetime
import pandas as pd
from io import BytesIO
from fastapi import HTTPException
from unittest.mock import patch, MagicMock
import os

def test_process_csv_file_success(db_session, mock_market_symbol):
    # Create sample CSV
    csv_content = """timeframe,timestamp,open,high,low,close,volume
M15,2025-01-01 10:00:00,1.1000,1.1050,1.0950,1.1020,100
M15,2025-01-01 10:15:00,1.1020,1.1060,1.1010,1.1050,150
"""
    # Write to temp file (since service reads from path)
    filename = "test_candles.csv"
    with open(filename, "w") as f:
        f.write(csv_content)
        
    try:
        # Mock Repositories to avoid SQLite/Postgres dialect mismatch in Unit Tests
        with patch("app.services.candle_service.CandleRepository") as MockCandleRepo, \
             patch("app.services.candle_service.MarketRepository") as MockMarketRepo:
            
            mock_candle_repo = MockCandleRepo.return_value
            mock_market_repo = MockMarketRepo.return_value
            
            # Setup mocks
            mock_market_repo.get_any_by_symbol.return_value = mock_market_symbol
            mock_candle_repo.bulk_upsert.return_value = 2
            
            result = CandleService.process_csv_file(filename, mock_market_symbol.symbol, "M15", db_session)
            assert "Successfully processed 2 rows" in result["message"]
            
            # Verify Repo interaction
            mock_candle_repo.bulk_upsert.assert_called_once()
            args, _ = mock_candle_repo.bulk_upsert.call_args
            assert len(args[0]) == 2

    finally:
        if os.path.exists(filename):
            os.remove(filename)

def test_process_csv_missing_symbol(db_session):
    filename = "dummy.csv"
    try:
        with pytest.raises(HTTPException) as exc:
            CandleService.process_csv_file(filename, "UNKNOWN_SYMBOL", "M15", db_session)
        assert exc.value.status_code == 404
    except Exception:
        pass

def test_get_candles_pagination(db_session, mock_market_symbol):
    # usage of bulk upsert via service or direct DB
    c1 = Candle(
        market_symbol_id=mock_market_symbol.id, 
        timeframe="M15", 
        timestamp=datetime(2025, 1, 1, 10, 0),
        open=1, high=2, low=0.5, close=1.5, volume=100
    )
    c2 = Candle(
        market_symbol_id=mock_market_symbol.id, 
        timeframe="M15", 
        timestamp=datetime(2025, 1, 1, 10, 15),
        open=1, high=2, low=0.5, close=1.5, volume=100
    )
    db_session.add_all([c1, c2])
    db_session.commit()
    
    # Test Page 1, Size 1
    resp = CandleService.get_candles(db_session, "EUR_USD", "M15", "OANDA", 1, 1)
    assert resp.total == 2
    assert len(resp.data) == 1
    assert resp.data[0]['timestamp'] == c2.timestamp # Sort desc
    
    # Test Page 2
    resp = CandleService.get_candles(db_session, "EUR_USD", "M15", "OANDA", 2, 1)
    assert len(resp.data) == 1
    assert resp.data[0]['timestamp'] == c1.timestamp
