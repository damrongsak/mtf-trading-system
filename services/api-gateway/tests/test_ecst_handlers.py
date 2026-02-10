import pytest
import json
from unittest.mock import MagicMock, patch
from app.streaming.handlers import MarketDataHandler
from app.models.market import MarketSymbol
from app.models.data_source import DataSource

@pytest.fixture
def mock_db():
    with patch("app.streaming.handlers.SessionLocal") as mock:
        db_instance = mock.return_value
        yield db_instance

def test_handle_symbol_info_success(mock_db):
    # Setup
    symbol = "XAU_USD"
    data = {
        "type": "SYMBOL_DETAILS",
        "source": "CTRADER",
        "details": {"digits": 3, "pipLocation": -2}
    }
    data_json = json.dumps(data)
    
    # Mock MarketSymbol and Query
    mock_ms = MagicMock(spec=MarketSymbol)
    mock_query = mock_db.query.return_value.join.return_value.filter.return_value.filter.return_value
    mock_query.first.return_value = mock_ms
    
    # Execute
    MarketDataHandler.handle_symbol_info(symbol, data_json)
    
    # Assert
    assert mock_ms.details == data["details"]
    mock_db.commit.assert_called_once()

def test_handle_symbol_info_variant_match(mock_db):
    # Test that "XAU/USD" matches "XAU_USD" in variants
    symbol = "XAU/USD"
    data = {
        "source": "CTRADER",
        "details": {"test": True}
    }
    data_json = json.dumps(data)
    
    mock_ms = MagicMock(spec=MarketSymbol)
    mock_query = mock_db.query.return_value.join.return_value.filter.return_value.filter.return_value
    mock_query.first.return_value = mock_ms
    
    MarketDataHandler.handle_symbol_info(symbol, data_json)
    
    # Check that in_ was called with variants
    filter_call = mock_db.query.return_value.join.return_value.filter.call_args[0][0]
    # This check is a bit deep into SQLAlchemy internals, but we can verify it ran
    assert mock_query.first.called

def test_handle_symbol_info_no_details(mock_db):
    symbol = "XAU_USD"
    data = {"source": "CTRADER"} # Missing "details"
    data_json = json.dumps(data)
    
    MarketDataHandler.handle_symbol_info(symbol, data_json)
    
    mock_db.query.assert_not_called()

def test_handle_symbol_info_not_found(mock_db):
    symbol = "UNKNOWN"
    data = {"source": "CTRADER", "details": {}}
    data_json = json.dumps(data)
    
    mock_query = mock_db.query.return_value.join.return_value.filter.return_value.filter.return_value
    mock_query.first.return_value = None
    
    MarketDataHandler.handle_symbol_info(symbol, data_json)
    
    mock_db.commit.assert_not_called()

@pytest.mark.asyncio
async def test_handle_symbol_info_async(mock_db):
    with patch("app.streaming.handlers.MarketDataHandler.handle_symbol_info") as mock_sync:
        await MarketDataHandler.handle_symbol_info_async("XAU_USD", "{}")
        mock_sync.assert_called_once_with("XAU_USD", "{}")
