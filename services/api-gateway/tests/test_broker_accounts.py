import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.models.market import MarketSymbol, MarketCategory
from app.models.data_source import DataSource
from app.models.broker_account import BrokerAccount
from app.models.user import User
from app.models.user_fund import UserFund, UserRole, Fund
from app.security import get_current_user
import uuid

# --- Helpers to configure Mock Query Chain ---
def mock_query_chain(mock_db, return_value):
    """
    Configures mock_db.query(...).filter(...).first() to return `return_value`.
    This is a simplification; for complex tests, we might need more specific matching.
    """
    # Create the chain
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    # For .first()
    mock_filter.first.return_value = return_value
    # For .all()
    if isinstance(return_value, list):
         mock_filter.all.return_value = return_value
    else:
         mock_filter.all.return_value = [return_value] if return_value else []
    return mock_filter

@pytest.fixture
def override_auth(app_client, mock_current_user):
    from app.main import app
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)

@pytest.mark.asyncio
async def test_fetch_symbols_cached(client, mock_db_session, mock_current_user):
    # 1. Setup Data Objects
    account_id = uuid.uuid4()
    fund_id = uuid.uuid4()
    
    mock_account = BrokerAccount(
        id=account_id,
        fund_id=fund_id,
        broker_name="OANDA",
        is_live=False
    )
    
    mock_user_fund = UserFund(user_id=mock_current_user.id, fund_id=fund_id)
    
    # Mock DataSource and Symbols
    mock_ds = DataSource(id=uuid.uuid4(), name="OANDA")
    mock_symbols = [
        MarketSymbol(symbol="EUR_USD", data_source_id=mock_ds.id),
        MarketSymbol(symbol="GBP_USD", data_source_id=mock_ds.id)
    ]
    
    # 2. Configure DB Query Side_effect
    # The endpoint makes multiple queries: Account, UserFund, DataSource, MarketSymbol
    # We need side_effect to return different things depending on the model queried
    
    def query_side_effect(model):
        query_mock = MagicMock()
        filter_mock = MagicMock()
        
        if model == BrokerAccount:
            filter_mock.first.return_value = mock_account
        elif model == UserFund:
            filter_mock.first.return_value = mock_user_fund
        elif model == DataSource:
            filter_mock.first.return_value = mock_ds
        elif model == MarketSymbol:
            filter_mock.all.return_value = mock_symbols
            filter_mock.first.return_value = mock_symbols[0]
        else:
            filter_mock.first.return_value = None
            filter_mock.all.return_value = []
            
        query_mock.filter.return_value = filter_mock
        return query_mock

    mock_db_session.query.side_effect = query_side_effect
    
    # Override Auth
    from app.main import app
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    
    # 3. Call Endpoint
    with patch("app.routers.broker_account.decrypt_data", return_value={"api_key": "k", "account_id": "a"}):
         # Mock sync success
         mock_instruments_full = {"instruments": [{"name": "EUR_USD", "type": "CURRENCY", "displayName": "EUR/USD"}]}
         with patch("httpx.AsyncClient.get") as mock_http_get:
              mock_http_get.return_value = AsyncMock(status_code=200, json=lambda: mock_instruments_full)
              
              response = client.post(f"/api/v1/accounts/{account_id}/fetch-symbols")
              
              assert response.status_code == 200
              data = response.json()
              assert "Fetched and cached 1 symbols" in data['message']
              assert "EUR_USD" in data['data']
    
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_fetch_symbols_cold_start(client, mock_db_session, mock_current_user):
    # 1. Setup Data Objects
    account_id = uuid.uuid4()
    fund_id = uuid.uuid4()
    
    mock_account = BrokerAccount(
        id=account_id,
        fund_id=fund_id,
        broker_name="OANDA",
        is_live=False,
        credentials_encrypted="enc"
    )
    
    mock_user_fund = UserFund(user_id=mock_current_user.id, fund_id=fund_id)
    
    # Mock Queries: DataSource is None (triggers cold start)
    def query_side_effect(model):
        query_mock = MagicMock()
        filter_mock = MagicMock()
        
        if model == BrokerAccount:
            filter_mock.first.return_value = mock_account
        elif model == UserFund:
            filter_mock.first.return_value = mock_user_fund
        elif model == DataSource:
            filter_mock.first.return_value = DataSource(id=uuid.uuid4(), name="OANDA") # Found
        elif model == MarketCategory:
            filter_mock.all.return_value = [] # Allow creation of categories
        elif model == MarketSymbol:
            filter_mock.first.return_value = None # Allow creation of symbols
            filter_mock.all.return_value = []
        else:
             filter_mock.first.return_value = None
            
        query_mock.filter.return_value = filter_mock
        return query_mock

    mock_db_session.query.side_effect = query_side_effect
    
    # Override Auth
    from app.main import app
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    
    # 2. Mock Logic
    # The logic: 1. fetch_oanda_instruments (gets names) 2. httpx (gets full) 
    # Logic note: if fetch_oanda_instruments fails, it raises error. 
    
    mock_instruments_full = {
        "instruments": [
            {"name": "USD_JPY", "type": "CURRENCY", "displayName": "USD/JPY"}
        ]
    }

    with patch("app.routers.broker_account.decrypt_data", return_value={"api_key": "k", "account_id": "a"}):
        with patch("app.routers.broker_account.fetch_oanda_instruments", return_value=["USD_JPY"]) as mock_simple_fetch:
            with patch("httpx.AsyncClient.get") as mock_http_get:
                 mock_http_get.return_value = AsyncMock(status_code=200, json=lambda: mock_instruments_full)
                 
                 response = client.post(f"/api/v1/accounts/{account_id}/fetch-symbols")
                 
                 assert response.status_code == 200
                 data = response.json()
                 assert "Fetched and cached 1 symbols" in data['message']
                 assert "USD_JPY" in data['data']
                 
                 # Verify DB additions
                 # We expect db.add to be called for DataSource, Categories, and Symbols
                 assert mock_db_session.add.call_count >= 1 
                 
    app.dependency_overrides.clear()
