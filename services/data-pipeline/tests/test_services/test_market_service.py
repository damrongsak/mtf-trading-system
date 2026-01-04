import pytest
from app.services.market_service import MarketService
from app.models.market import MarketSymbol
from app.schemas import MarketSymbolUpdate
from fastapi import HTTPException

from unittest.mock import patch, MagicMock

def test_get_active_symbols(db_session, mock_market_symbol):
    with patch("app.services.market_service.MarketRepository") as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.get_active_symbols.return_value = [mock_market_symbol]
        
        symbols = MarketService.get_active_symbols(db_session, "OANDA")
        assert len(symbols) == 1
        assert symbols[0].symbol == "EUR_USD"


def test_update_status(db_session, mock_market_symbol):
    update_data = MarketSymbolUpdate(is_active=False)
    updated = MarketService.update_status(db_session, mock_market_symbol.id, update_data)
    
    assert updated.is_active == False
    
    # Verify DB
    db_session.refresh(mock_market_symbol)
    assert mock_market_symbol.is_active == False

def test_update_status_not_found(db_session):
    import uuid
    random_id = uuid.uuid4()
    with pytest.raises(HTTPException) as exc:
        MarketService.update_status(db_session, random_id, MarketSymbolUpdate(is_active=True))
    assert exc.value.status_code == 404
