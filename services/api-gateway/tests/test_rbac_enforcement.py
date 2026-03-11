import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.models.user import User
from app.models.user_fund import Fund, UserFund, UserRole
from app.models.broker_account import BrokerAccount
from app.security import get_current_user
from app.utils.response import ResponseStatus
import uuid
import json
from uuid import UUID

@pytest.fixture
def fund_id():
    return uuid.uuid4()

@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.username = "testuser"
    return user

def setup_mock_rbac(mock_db, user_id, fund_id, role: UserRole):
    """Helper to mock UserFund record and Fund existence."""
    mock_user_fund = MagicMock(spec=UserFund)
    mock_user_fund.user_id = user_id
    mock_user_fund.fund_id = fund_id
    mock_user_fund.role = role
    
    mock_fund = MagicMock(spec=Fund)
    mock_fund.id = fund_id
    mock_fund.name = "Test Fund"
    mock_fund.description = "Test Description"
    mock_fund.strategy_type = "MTF_SMC_BASIC"
    mock_fund.asset_classes = ["FX"]
    mock_fund.max_risk_per_trade = 1.0
    mock_fund.default_lot_size = 0.01
    mock_fund.max_drawdown_threshold = 10.0
    mock_fund.max_portfolio_beta = 0.5
    mock_fund.gross_exposure_limit = 100.0
    mock_fund.net_exposure_limit = 50.0
    mock_fund.position_limit_single = 5.0
    mock_fund.position_limit_sector = 20.0
    
    def side_effect(model):
        q = MagicMock()
        if model == UserFund:
            q.filter.return_value.first.return_value = mock_user_fund
        elif model == Fund:
            q.filter.return_value.first.return_value = mock_fund
        return q
        
    mock_db.query.side_effect = side_effect
    return mock_user_fund, mock_fund

def test_rbac_view_only_fund_masking(client, mock_db_session, mock_user, fund_id):
    """VIEWER role should see masked credentials in broker accounts."""
    setup_mock_rbac(mock_db_session, mock_user.id, fund_id, UserRole.VIEWER)
    
    # Mock Broker Account
    mock_account = MagicMock(spec=BrokerAccount)
    mock_account.id = uuid.uuid4()
    mock_account.fund_id = fund_id
    mock_account.broker_name = "OANDA"
    mock_account.account_name = "Test Account"
    mock_account.account_number = "12345"
    mock_account.credentials_encrypted = b"encrypted_stuff"
    mock_account.risk_settings = {}
    mock_account.is_active = True
    mock_account.is_live = False
    mock_account.created_at = datetime.now()
    mock_account.supported_symbols = []
    
    # Setup list_accounts query with chaining support
    mock_query = MagicMock()
    # Support .join().join().filter().filter().all()
    mock_query.join.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.all.return_value = [mock_account]
    
    # Re-setup side effect to handle BrokerAccount too
    def side_effect(model):
        q = MagicMock()
        if model == UserFund:
            uf = MagicMock(spec=UserFund)
            uf.role = UserRole.VIEWER
            q.filter.return_value.first.return_value = uf
        elif model == BrokerAccount:
            return mock_query
        return q
    mock_db_session.query.side_effect = side_effect
    
    app.dependency_overrides[get_current_user] = lambda: mock_user
    
    response = client.get(f"/api/v1/accounts/?fund_id={fund_id}")
    
    assert response.status_code == 200
    data = response.json()
    # Masked credentials should be a dict with "masked" key
    assert "masked" in data["data"][0]["credentials"]
    assert "Insufficient" in data["data"][0]["credentials"]["masked"]
    
    app.dependency_overrides.pop(get_current_user)

def test_rbac_forbidden_action(client, mock_db_session, mock_user, fund_id):
    """TRADER role should NOT be allowed to delete a fund (OWNER only)."""
    setup_mock_rbac(mock_db_session, mock_user.id, fund_id, UserRole.TRADER)
    
    app.dependency_overrides[get_current_user] = lambda: mock_user
    
    response = client.delete(f"/api/v1/funds/{fund_id}")
    
    # RequireRole should raise 403
    assert response.status_code == 403
    # Check if it has detail in error message or just check status
    
    app.dependency_overrides.pop(get_current_user)

def test_rbac_manager_allowed_update(client, mock_db_session, mock_user, fund_id):
    """MANAGER role should be allowed to update a fund."""
    setup_mock_rbac(mock_db_session, mock_user.id, fund_id, UserRole.MANAGER)
    
    app.dependency_overrides[get_current_user] = lambda: mock_user
    
    payload = {"name": "Updated Fund"}
    response = client.put(f"/api/v1/funds/{fund_id}", json=payload)
    
    # Should NOT be 403. might fail later due to DB mocking but 200/404 is fine (it passed RequireRole)
    assert response.status_code != 403
    
    app.dependency_overrides.pop(get_current_user)

def test_rbac_no_fund_access(client, mock_db_session, mock_user, fund_id):
    """User with no role in a fund should be denied access."""
    # Mock DB Query returning None for UserFund
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    
    app.dependency_overrides[get_current_user] = lambda: mock_user
    
    response = client.get(f"/api/v1/funds/{fund_id}")
    
    assert response.status_code == 403
    
    app.dependency_overrides.pop(get_current_user)
