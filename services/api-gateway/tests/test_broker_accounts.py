from unittest.mock import MagicMock
from app.models.broker_account import BrokerAccount
from app.models.user_fund import UserFund, UserRole, Fund
from app.schemas.response import ResponseStatus
import uuid

def test_create_account_with_risk_override(client, mock_db_session, mock_current_user):
    """Test POST /api/v1/accounts with risk_settings and supported_symbols"""
    from app.security import get_current_user
    
    fund_id = uuid.uuid4()
    
    # Mock Fund existence and User permission
    mock_fund = MagicMock(spec=Fund)
    mock_fund.id = fund_id
    
    mock_user_fund = MagicMock(spec=UserFund)
    mock_user_fund.role = UserRole.OWNER
    
    def query_side_effect(model):
        mock_query = MagicMock()
        # Logic for determining what to return based on joins or filters is tricky with MagicMock side_effect
        # Simplified: If querying UserFund, return the mocked permission
        # If querying Fund, return mocked Fund
        if model == UserFund:
             mock_query.filter.return_value.first.return_value = mock_user_fund
        elif model == Fund:
             mock_query.filter.return_value.first.return_value = mock_fund
        return mock_query

    mock_db_session.query.side_effect = query_side_effect
    
    app = client.app
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    
    payload = {
        "fund_id": str(fund_id),
        "broker_name": "OANDA",
        "account_name": "Risk Account",
        "account_number": "001",
        "credentials": {"api_key": "k", "account_id": "i", "environment": "practice"},
        "is_live": False,
        "supported_symbols": ["BTC/USD", "ETH/USD"],
        "risk_settings": {"max_risk_per_trade": 5.0}
    }
    
    # Manually ensure defaults that DB usually handles
    def side_effect(instance):
        instance.id = uuid.uuid4()
        from datetime import datetime
        instance.created_at = datetime.utcnow()
        if instance.is_active is None: instance.is_active = True
        if instance.is_live is None: instance.is_live = False
        
    mock_db_session.refresh.side_effect = side_effect
    
    response = client.post("/api/v1/accounts", json=payload)
    
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == ResponseStatus.SUCCESS
    assert data["data"]["supported_symbols"] == ["BTC/USD", "ETH/USD"]
    assert data["data"]["risk_settings"]["max_risk_per_trade"] == 5.0
    
    # Verify persistence
    account_arg = mock_db_session.add.call_args[0][0]
    assert isinstance(account_arg, BrokerAccount)
    assert account_arg.supported_symbols == ["BTC/USD", "ETH/USD"]
    assert account_arg.risk_settings == {"max_risk_per_trade": 5.0}

    app.dependency_overrides.pop(get_current_user)

def test_update_account_symbols(client, mock_db_session, mock_current_user):
    """Test PUT /api/v1/accounts/{id} updating supported_symbols"""
    from app.security import get_current_user
    
    account_id = uuid.uuid4()
    
    mock_account = MagicMock(spec=BrokerAccount)
    mock_account.id = account_id
    mock_account.fund_id = uuid.uuid4()
    mock_account.supported_symbols = ["OLD"]
    mock_account.risk_settings = {}
    mock_account.broker_name = "OANDA"
    mock_account.account_name = "My Account"
    mock_account.account_number = "123"
    mock_account.is_active = True
    mock_account.is_live = False
    mock_account.created_at = "2024-01-01T00:00:00Z"
    
    mock_user_fund = MagicMock(spec=UserFund)
    mock_user_fund.role = UserRole.OWNER
    
    # Complex query mocking for:
    # 1. Get Account (to find fund_id)
    # 2. Get UserFund (to check permission on fund_id)
    
    # In `broker_account.py`, it likely does:
    # account = db.query(BrokerAccount).get(id)
    # user_fund = db.query(UserFund).filter(...).first()
    
    def query_side_effect(model):
        mock_query = MagicMock()
        if model == BrokerAccount:
            mock_query.filter.return_value.first.return_value = mock_account
        elif model == UserFund:
            mock_query.filter.return_value.first.return_value = mock_user_fund
        return mock_query
        
    mock_db_session.query.side_effect = query_side_effect
    
    app = client.app
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    
    payload = {
        "supported_symbols": ["NEW", "LIST"]
    }
    
    response = client.put(f"/api/v1/accounts/{account_id}", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["supported_symbols"] == ["NEW", "LIST"]
    assert mock_account.supported_symbols == ["NEW", "LIST"]
    
    app.dependency_overrides.pop(get_current_user)

def test_create_account_default_fund(client, mock_db_session, mock_current_user):
    """Test POST /api/v1/accounts without fund_id uses default"""
    from app.security import get_current_user
    from app.models.user_preferences import UserPreferences
    
    fund_id = uuid.uuid4()
    
    # Mock Prefs
    mock_prefs = MagicMock(spec=UserPreferences)
    mock_prefs.default_fund_id = fund_id
    
    mock_fund = MagicMock(spec=Fund)
    mock_fund.id = fund_id
    
    mock_user_fund = MagicMock(spec=UserFund)
    mock_user_fund.role = UserRole.OWNER
    
    def query_side_effect(model):
        mock_query = MagicMock()
        if model == UserPreferences:
             mock_query.filter.return_value.first.return_value = mock_prefs
        elif model == UserFund:
             mock_query.filter.return_value.first.return_value = mock_user_fund
        elif model == Fund:
             mock_query.filter.return_value.first.return_value = mock_fund
        return mock_query

    mock_db_session.query.side_effect = query_side_effect
    
    app = client.app
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    
    payload = {
        # NO fund_id
        "broker_name": "OANDA",
        "account_name": "Default Fund Account",
        "credentials": {"api_key": "k", "account_id": "i", "environment": "practice"}
    }
    
    # Defaults fixture
    def side_effect(instance):
        instance.id = uuid.uuid4()
        from datetime import datetime
        instance.created_at = datetime.utcnow()
        if instance.is_active is None: instance.is_active = True
        if instance.is_live is None: instance.is_live = False
    mock_db_session.refresh.side_effect = side_effect

    response = client.post("/api/v1/accounts", json=payload)
    
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == ResponseStatus.SUCCESS
    assert data["data"]["fund_id"] == str(fund_id)

    app.dependency_overrides.pop(get_current_user)
