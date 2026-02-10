import pytest
from unittest.mock import MagicMock
from app.utils.helpers import resolve_market_symbol
from app.models.market import MarketSymbol
from app.models.data_source import DataSource

def test_resolve_market_symbol_variants():
    db = MagicMock()
    mock_ms = MagicMock(spec=MarketSymbol)
    
    # 1st call for query setup, 2nd for ct_ms check
    mock_q1 = MagicMock()
    mock_q2 = MagicMock()
    db.query.side_effect = [mock_q1, mock_q2]
    
    # ct_ms query chain
    mock_q2.join.return_value.filter.return_value.first.return_value = mock_ms
    
    result = resolve_market_symbol(db, "XAU/USD")
    
    assert result == mock_ms

def test_resolve_market_symbol_explicit_source():
    db = MagicMock()
    mock_ms = MagicMock(spec=MarketSymbol)
    
    # query.filter().filter().first()
    mock_query = MagicMock()
    db.query.return_value = mock_query
    
    # 1st filter (DataSource.name), 2nd filter (variants)
    mock_query.join.return_value.filter.return_value.filter.return_value.first.return_value = mock_ms
    
    result = resolve_market_symbol(db, "XAU_USD", data_source="CTRADER_LIVE")
    
    assert result == mock_ms
    # Verify filter was called at least twice
    assert mock_query.join.return_value.filter.called
    assert mock_query.join.return_value.filter.return_value.filter.called
