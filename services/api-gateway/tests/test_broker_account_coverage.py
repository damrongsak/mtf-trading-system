import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from app.security import get_current_user
from app.models.broker_account import BrokerAccount
from app.models.user_fund import Fund, UserFund, User, UserRole
from app.models.user_preferences import UserPreferences
from app.models.data_source import DataSource
from app.models.market import MarketSymbol, MarketCategory
import uuid

@pytest.fixture
def local_mock_db():
    return MagicMock()

@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.username = "test_user"
    return user

@pytest.fixture(autouse=True)
def override_dependency(local_mock_db, mock_user):
    app.dependency_overrides[get_db] = lambda: local_mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield
    app.dependency_overrides = {}

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_list_accounts_empty(client, local_mock_db, mock_user):
    local_mock_db.query.return_value.join.return_value.join.return_value.filter.return_value.all.return_value = []
    response = client.get("/api/v1/accounts/")
    assert response.status_code == 200
    assert response.json()["data"] == []

def test_list_accounts_success(client, local_mock_db, mock_user):
    acc = MagicMock(spec=BrokerAccount)
    acc.id = uuid.uuid4()
    acc.fund_id = uuid.uuid4() # Correct UUID
    acc.account_name = "My Oanda"
    acc.broker_name = "OANDA"
    acc.account_number = "12345" # String
    acc.supported_symbols = ["XAU/USD"]
    acc.risk_settings = {} # Dict
    acc.credentials_encrypted = "enc"
    acc.is_active = True
    acc.is_live = False
    acc.created_at = "2024-01-01"
    
    local_mock_db.query.return_value.join.return_value.join.return_value.filter.return_value.all.return_value = [acc]
    
    response = client.get("/api/v1/accounts/")
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["account_name"] == "My Oanda"

@pytest.mark.asyncio
async def test_create_account_success(client, local_mock_db, mock_user):
    # Mock Prefs for default fund
    fund_id = uuid.uuid4()
    prefs = MagicMock(spec=UserPreferences)
    prefs.default_fund_id = fund_id
    
    # Mock UserFund check
    uf = MagicMock(spec=UserFund)
    uf.role = UserRole.OWNER
    
    # Mock DB Query Chain
    def side_effect_query(model):
        q = MagicMock()
        if model == UserPreferences:
             q.filter.return_value.first.return_value = prefs
        elif model == UserFund:
             q.filter.return_value.first.return_value = uf
        elif model == BrokerAccount:
             # Check distinct account number
             q.filter.return_value.first.return_value = None 
        return q
    local_mock_db.query.side_effect = side_effect_query
    
    # Mock verify_oanda_credentials (async)
    with patch("app.routers.broker_account.verify_oanda_credentials", new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = None
        
        payload = {
            "broker_name": "OANDA",
            "account_name": "New Account",
            "credentials": {"api_key": "secret", "account_id": "123-123"},
            "is_live": False
        }
        
        # Mock Refresh to populate ID
        def refresh_effect(obj):
            obj.id = uuid.uuid4()
            obj.fund_id = fund_id
            obj.credentials_encrypted = "enc_string"
            obj.created_at = "2024-01-01"
            # Populate fields normally set by init or logic
            obj.risk_settings = None
            obj.supported_symbols = None
            obj.account_number = None
            
        local_mock_db.refresh.side_effect = refresh_effect

        response = client.post("/api/v1/accounts/", json=payload)
        
        if response.status_code != 201:
            print(f"DEBUG: {response.json()}")
            
        assert response.status_code == 201
        assert response.json()["data"]["broker_name"] == "OANDA"
        assert local_mock_db.add.called
        mock_verify.assert_called_once()

@pytest.mark.asyncio
async def test_create_account_oanda_fail(client, local_mock_db, mock_user):
    # Mock setup similar to success ...
    fund_id = uuid.uuid4()
    prefs = MagicMock(spec=UserPreferences)
    prefs.default_fund_id = fund_id
    uf = MagicMock(spec=UserFund)
    
    def side_effect_query(model):
        q = MagicMock()
        if model == UserPreferences: q.filter.return_value.first.return_value = prefs
        elif model == UserFund: q.filter.return_value.first.return_value = uf
        elif model == BrokerAccount: q.filter.return_value.first.return_value = None
        return q
    local_mock_db.query.side_effect = side_effect_query

    with patch("app.routers.broker_account.verify_oanda_credentials", new_callable=AsyncMock) as mock_verify:
        mock_verify.side_effect = ValueError("Invalid Token")
        
        payload = {
            "broker_name": "OANDA",
            "account_name": "Bad Account",
            "credentials": {"api_key": "bad", "account_id": "123"},
        }
        
        response = client.post("/api/v1/accounts/", json=payload)
        data = response.json()
        print(f"DEBUG Error Resp: {data}")
        assert response.status_code == 400
        
        # Check standard error response format
        if "message" in data:
            assert "Invalid Token" in data["message"]
        elif "detail" in data:
            assert "Invalid Token" in str(data["detail"])
        else:
             pytest.fail(f"Unknown error format: {data}")

def test_delete_account_success(client, local_mock_db, mock_user):
    acc_id = uuid.uuid4()
    fund_id = uuid.uuid4()
    
    mock_acc = MagicMock(spec=BrokerAccount)
    mock_acc.id = acc_id
    mock_acc.fund_id = fund_id
    
    mock_uf = MagicMock(spec=UserFund)
    
    def side_effect_query(model):
        q = MagicMock()
        if model == BrokerAccount:
            q.filter.return_value.first.return_value = mock_acc
        elif model == UserFund:
            q.filter.return_value.first.return_value = mock_uf
        return q
    local_mock_db.query.side_effect = side_effect_query
    
    response = client.delete(f"/api/v1/accounts/{acc_id}")
    assert response.status_code == 200
    local_mock_db.delete.assert_called_with(mock_acc)

@pytest.mark.asyncio
async def test_fetch_symbols_cold_start(client, local_mock_db, mock_user):
    acc_id = uuid.uuid4()
    fund_id = uuid.uuid4()
    
    mock_acc = MagicMock(spec=BrokerAccount)
    mock_acc.id = acc_id
    mock_acc.fund_id = fund_id
    mock_acc.broker_name = "OANDA"
    mock_acc.credentials_encrypted = "enc" # Needs decrypt mock
    mock_acc.is_live = False
    
    mock_uf = MagicMock(spec=UserFund)
    
    # Mock Decrypt
    with patch("app.routers.broker_account.decrypt_data") as mock_decrypt:
        mock_decrypt.return_value = {"api_key": "key", "account_id": "123"}
        
        # Mock Fetch Instruments helper (to avoid internal http call if we mocked it higher up)
        # But wait, endpoint has custom logic for cold start that calls httpx directly?
        # Re-reading code: valid logic uses `fetch_oanda_instruments` initially, then later does another `httpx` call for full details? 
        # Yes, lines 360 and 395. We need to mock both or `httpx` globally.
        
        # Strategy: Mock httpx.AsyncClient to handle both calls
        
        async def mock_get(*args, **kwargs):
            # First call (fetch_oanda_instruments helper) -> returns names
            # Second call (bulk detail) -> returns instruments list with type
            return MagicMock(status_code=200, json=lambda: {
                "instruments": [
                    {"name": "EUR_USD", "type": "CURRENCY", "displayName": "EUR/USD"},
                    {"name": "XAU_USD", "type": "CFD", "displayName": "Gold"}
                ]
            })

        with patch("httpx.AsyncClient", autospec=True) as MockClient:
            mock_inst = MockClient.return_value
            mock_inst.__aenter__.return_value = mock_inst
            mock_inst.get.side_effect = mock_get
            
            # DB Mocks
            def side_effect_query(model):
                q = MagicMock()
                if model == BrokerAccount: q.filter.return_value.first.return_value = mock_acc
                elif model == UserFund: q.filter.return_value.first.return_value = mock_uf
                elif model == DataSource: q.filter.return_value.first.return_value = None # Force cold start
                elif model == MarketCategory: q.all.return_value = [] # Force cat creation
                elif model == MarketSymbol: q.filter.return_value.first.return_value = None # Force creation
                return q
            local_mock_db.query.side_effect = side_effect_query
            
            response = client.post(f"/api/v1/accounts/{acc_id}/fetch-symbols")
            
            if response.status_code != 200:
                print(response.json())
                
            assert response.status_code == 200
            data = response.json()["data"]
            assert "EUR_USD" in data
            assert local_mock_db.add.call_count > 0 # DataSource, Categories, Symbols
