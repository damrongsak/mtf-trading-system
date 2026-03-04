import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from app.security import get_current_user
from app.models.user import User
from app.models.user_fund import Fund, UserFund, UserRole
from datetime import datetime
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

def test_list_funds(client, local_mock_db, mock_user):
    # Mock UserFund query
    uf = MagicMock(spec=UserFund)
    uf.fund_id = uuid.uuid4()
    uf.user_id = mock_user.id
    uf.role = UserRole.OWNER
    
    local_mock_db.query.return_value.filter.return_value.all.return_value = [uf]
    
    # Mock Fund query
    mock_fund = MagicMock(spec=Fund)
    mock_fund.id = uf.fund_id
    mock_fund.name = "Test Fund"
    mock_fund.description = "Desc"
    mock_fund.strategy_type = "MTF_SMC_BASIC" # Valid Enum
    mock_fund.asset_classes = ["FX"]
    mock_fund.max_risk_per_trade = 1.0
    mock_fund.default_lot_size = 0.1
    # Set explicit primitives for response model validation
    mock_fund.max_drawdown_threshold = 10.0
    mock_fund.max_portfolio_beta = 1.5
    mock_fund.gross_exposure_limit = 1000.0
    mock_fund.net_exposure_limit = 500.0
    mock_fund.position_limit_single = 10.0
    mock_fund.position_limit_sector = 20.0
    
    # First query is UserFund list. Second is Fund by ID.
    # We need side_effect for db.query to handle different models
    
    def side_effect_query(model):
        q = MagicMock()
        if model == UserFund:
            q.filter.return_value.all.return_value = [uf]
            # Also used for finding owner name inside the loop
            q.filter.return_value.first.side_effect = [uf] # Return mock UF as owner record
        elif model == Fund:
            q.filter.return_value.first.return_value = mock_fund
        elif model == User:
             q.filter.return_value.first.return_value = mock_user
        return q
        
    local_mock_db.query.side_effect = side_effect_query
    
    response = client.get("/api/v1/funds")
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["name"] == "Test Fund"
    assert data[0]["role"] == "OWNER"

def test_get_fund_detail(client, local_mock_db, mock_user):
    fund_id = uuid.uuid4()
    
    # Mock UserFund check
    uf = MagicMock(spec=UserFund)
    uf.role = UserRole.MANAGER
    
    # Mock Fund
    mock_fund = MagicMock(spec=Fund)
    mock_fund.id = fund_id
    mock_fund.name = "Detail Fund"
    mock_fund.description = "Detail Desc" # Must be str
    mock_fund.strategy_type = "MULTI_ASSET" # Valid Enum
    mock_fund.asset_classes = ["FX"]
    mock_fund.max_risk_per_trade = 2.0
    mock_fund.default_lot_size = 0.5
    mock_fund.max_drawdown_threshold = None
    mock_fund.max_portfolio_beta = None
    mock_fund.gross_exposure_limit = None
    mock_fund.net_exposure_limit = None
    mock_fund.position_limit_single = None
    mock_fund.position_limit_sector = None

    def side_effect_query(model):
        q = MagicMock()
        if model == UserFund:
            # Check access: returns user_fund
            q.filter.return_value.first.return_value = uf
        elif model == Fund:
            q.filter.return_value.first.return_value = mock_fund
        elif model == User:
             q.filter.return_value.first.return_value = mock_user
        return q
        
    local_mock_db.query.side_effect = side_effect_query
    
    response = client.get(f"/api/v1/funds/{fund_id}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "Detail Fund"
    assert data["role"] == "MANAGER"

def test_get_fund_not_found_or_denied(client, local_mock_db):
    local_mock_db.query.return_value.filter.return_value.first.return_value = None
    response = client.get(f"/api/v1/funds/{uuid.uuid4()}")
    assert response.status_code == 404

def test_create_fund(client, local_mock_db, mock_user):
    payload = {
        "name": "New Fund",
        "description": "My new fund",
        "strategy_type": "MTF_SMC_BASIC", # Valid
        "asset_classes": ["FX"], # Valid
        "max_risk_per_trade": 1.5,
        "default_lot_size": 0.01
    }
    
    def refresh_effect(obj):
        obj.id = uuid.uuid4()
        # Ensure default/values are present for response
        obj.strategy_type = "MTF_SMC_BASIC"
        obj.asset_classes = ["FX"]
        obj.max_risk_per_trade = 1.5
        obj.default_lot_size = 0.01
        obj.max_drawdown_threshold = None
        obj.max_portfolio_beta = None
        obj.gross_exposure_limit = None
        obj.net_exposure_limit = None
        obj.position_limit_single = None
        obj.position_limit_sector = None
        
    local_mock_db.refresh.side_effect = refresh_effect
    
    response = client.post("/api/v1/funds", json=payload)
    
    if response.status_code != 201:
        print(response.json())
    
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "New Fund"
    assert data["role"] == "OWNER"
    
    assert local_mock_db.add.call_count == 2 # Fund + UserFund

def test_update_fund_success(client, local_mock_db, mock_user):
    fund_id = uuid.uuid4()
    
    uf = MagicMock(spec=UserFund)
    uf.role = UserRole.OWNER
    
    mock_fund = MagicMock(spec=Fund)
    mock_fund.id = fund_id
    mock_fund.name = "Old Name"
    mock_fund.description = "Old Desc" # Must be str
    # Populate required fields for response model (Pydantic validation)
    mock_fund.strategy_type = "MTF_SMC_BASIC"
    mock_fund.asset_classes = []
    mock_fund.max_risk_per_trade = 1.0
    mock_fund.default_lot_size = 0.1
    mock_fund.max_drawdown_threshold = None
    mock_fund.max_portfolio_beta = None
    mock_fund.gross_exposure_limit = None
    mock_fund.net_exposure_limit = None
    mock_fund.position_limit_single = None
    mock_fund.position_limit_sector = None
    
    def side_effect_query(model):
        q = MagicMock()
        if model == UserFund:
            q.filter.return_value.first.return_value = uf
        elif model == Fund:
            q.filter.return_value.first.return_value = mock_fund
        return q
    local_mock_db.query.side_effect = side_effect_query
    
    payload = {"name": "Updated Name", "max_risk_per_trade": 5.0}
    response = client.put(f"/api/v1/funds/{fund_id}", json=payload)
    
    assert response.status_code == 200
    assert mock_fund.name == "Updated Name"
    assert mock_fund.max_risk_per_trade == 5.0
    mock_db_commit = local_mock_db.commit
    mock_db_commit.assert_called_once()

def test_delete_fund_success(client, local_mock_db):
    fund_id = uuid.uuid4()
    
    uf = MagicMock(spec=UserFund)
    uf.role = UserRole.OWNER
    
    mock_fund = MagicMock(spec=Fund)
    
    def side_effect_query(model):
        q = MagicMock()
        if model == UserFund:
            q.filter.return_value.first.return_value = uf
        elif model == Fund:
            q.filter.return_value.first.return_value = mock_fund
        return q
    local_mock_db.query.side_effect = side_effect_query
    
    response = client.delete(f"/api/v1/funds/{fund_id}")
    assert response.status_code == 204
    local_mock_db.delete.assert_called_with(mock_fund)
    local_mock_db.commit.assert_called_once()

def test_delete_fund_forbidden(client, local_mock_db):
    uf = MagicMock(spec=UserFund)
    uf.role = UserRole.VIEWER # Correct Enum
    
    local_mock_db.query.return_value.filter.return_value.first.return_value = uf
    
    response = client.delete(f"/api/v1/funds/{uuid.uuid4()}")
    assert response.status_code == 403
