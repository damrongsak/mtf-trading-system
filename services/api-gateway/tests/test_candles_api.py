import pytest
from unittest.mock import MagicMock, patch
from app.security import get_current_user
from app.models.user import User
from app.models.data_source import DataSource
from app.models.market import MarketSymbol
import uuid

def test_get_candles_unauthorized(client, mock_db_session, mock_current_user):
    """Test that a user without fund access to a data source is denied"""
    # Override get_current_user
    client.app.dependency_overrides[get_current_user] = lambda: mock_current_user
    mock_current_user.is_superuser = False
    mock_current_user.id = str(uuid.uuid4())
    
    # Mock the access check query to return None
    # get_candles does: db.query(DataSource).join(BrokerAccount).join(UserFund).filter(...).first()
    mock_db_session.query.return_value.join.return_value.join.return_value.filter.return_value.first.return_value = None
    
    response = client.get("/api/v1/market/candles?symbol=XAUUSD&timeframe=H1&data_source=CTRADER")
    
    assert response.status_code == 403
    assert "Permission denied" in response.json()["message"]
    
    # Clean up
    client.app.dependency_overrides.pop(get_current_user)

def test_get_candles_authorized_success(client, mock_db_session, mock_current_user):
    """Test that a user with fund access can retrieve candles"""
    # Override get_current_user
    client.app.dependency_overrides[get_current_user] = lambda: mock_current_user
    mock_current_user.is_superuser = False
    mock_current_user.id = str(uuid.uuid4())
    
    # Mock access check (first query)
    mock_access = MagicMock(spec=DataSource)
    
    # Mock MarketSymbol lookup (second query)
    mock_symbol = MagicMock(spec=MarketSymbol)
    mock_symbol.id = str(uuid.uuid4())
    mock_symbol.symbol = "XAUUSD"
    mock_symbol.data_source = MagicMock(spec=DataSource)
    mock_symbol.data_source.name = "CTRADER"
    
    # Mock the sequence of queries
    # 1. Access check
    # 2. MarketSymbol lookup
    # 3. Candles retrieval
    
    # We need to distinguish between different models in query(Model)
    def mocked_query(model):
        q = MagicMock()
        if model == DataSource:
            q.join.return_value.join.return_value.filter.return_value.first.return_value = mock_access
        elif model == MarketSymbol:
            # For the MarketSymbol query which uses join(DataSource)
            q.join.return_value.filter.return_value.first.return_value = mock_symbol
        elif str(model).endswith("Candle'>"): # Mocking the Candle model query
            from app.models.candle import Candle
            q.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
                MagicMock(timestamp=1712280000, open=2000.0, high=2010.0, low=1990.0, close=2005.0, tick_volume=100)
            ]
        return q

    mock_db_session.query.side_effect = mocked_query
    
    response = client.get("/api/v1/market/candles?symbol=XAUUSD&timeframe=H1&data_source=CTRADER")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["data"]) == 1
    assert data["data"][0]["close"] == 2005.0

    # Clean up
    client.app.dependency_overrides.pop(get_current_user)

def test_get_candles_superuser_bypass(client, mock_db_session, mock_current_user):
    """Test that a superuser bypasses fund access checks"""
    # Override get_current_user
    client.app.dependency_overrides[get_current_user] = lambda: mock_current_user
    mock_current_user.is_superuser = True
    
    # Mock MarketSymbol lookup
    mock_symbol = MagicMock(spec=MarketSymbol)
    mock_symbol.id = str(uuid.uuid4())
    mock_symbol.symbol = "XAUUSD"
    mock_symbol.data_source = MagicMock(spec=DataSource)
    
    def mocked_query(model):
        q = MagicMock()
        if model == MarketSymbol:
            q.join.return_value.filter.return_value.first.return_value = mock_symbol
        elif str(model).endswith("Candle'>"):
            q.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        return q

    mock_db_session.query.side_effect = mocked_query
    
    response = client.get("/api/v1/market/candles?symbol=XAUUSD&timeframe=H1&data_source=CTRADER")
    assert response.status_code == 200

    # Clean up
    client.app.dependency_overrides.pop(get_current_user)
