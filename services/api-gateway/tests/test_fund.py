from unittest.mock import MagicMock, patch
from app.models.user_fund import Fund, UserFund, User
from app.schemas.response import ResponseStatus
import uuid

def test_get_funds_success(client, mock_db_session, mock_current_user):
    """Test GET /api/v1/funds returns user's accessible funds"""
    from app.security import get_current_user
    
    # Setup mock data
    fund1_id = uuid.uuid4()
    fund2_id = uuid.uuid4()
    
    mock_fund1 = MagicMock(spec=Fund)
    mock_fund1.id = fund1_id
    mock_fund1.name = "Test Fund 1"
    mock_fund1.description = "Description 1"
    mock_fund1.strategy_type = "MTF_SMC_BASIC"
    mock_fund1.asset_classes = ["FX"]
    mock_fund1.max_risk_per_trade = 10.0
    mock_fund1.default_lot_size = 0.01
    mock_fund1.max_drawdown_threshold = 10.0
    mock_fund1.max_portfolio_beta = 0.5
    mock_fund1.gross_exposure_limit = 100.0
    mock_fund1.net_exposure_limit = 50.0
    mock_fund1.position_limit_single = 5.0
    mock_fund1.position_limit_sector = 20.0
    
    mock_fund2 = MagicMock(spec=Fund)
    mock_fund2.id = fund2_id
    mock_fund2.name = "Test Fund 2"
    mock_fund2.description = "Description 2"
    mock_fund2.strategy_type = "MULTI_ASSET"
    mock_fund2.asset_classes = ["CRYPTO"]
    mock_fund2.max_risk_per_trade = 20.0
    mock_fund2.default_lot_size = 0.01
    mock_fund2.max_drawdown_threshold = 20.0
    mock_fund2.max_portfolio_beta = 0.5
    mock_fund2.gross_exposure_limit = 100.0
    mock_fund2.net_exposure_limit = 50.0
    mock_fund2.position_limit_single = 5.0
    mock_fund2.position_limit_sector = 20.0
    
    mock_user_fund1 = MagicMock(spec=UserFund)
    mock_user_fund1.fund_id = fund1_id
    mock_user_fund1.role = MagicMock(value="OWNER")
    
    mock_user_fund2 = MagicMock(spec=UserFund)
    mock_user_fund2.fund_id = fund2_id
    mock_user_fund2.role = MagicMock(value="TRADER")
    
    # Setup query side effect
    def query_side_effect(model):
        mock_query = MagicMock()
        if model == UserFund:
            # First call is valid list, subsequent might be for owner check
            mock_query.filter.return_value.all.return_value = [mock_user_fund1, mock_user_fund2]
            mock_query.filter.return_value.first.return_value = None # Assume no owner found to simplify
        elif model == Fund:
            # Simplistic: return mock_fund1 then mock_fund2? Hard to distinguish without filter args check
            # But the router loops results.
            # Let's return a specific mock if possible, or just one that satisfies.
            # Strategy: The test iterates user_funds. 
            pass
        return mock_query
        
    # Better approach: Just mock behavior based on call order or inspection
    # Since side_effect via function is complex to maintain state, let's just make the list long enough
    # returning defaults if needed.
    # Actually, simpler: mock_db_session.query called with UserFund -> return list.
    # Called with Fund -> return mock_fund (generic). 
    
    mock_query_user_fund = MagicMock()
    mock_query_user_fund.filter.return_value.all.return_value = [mock_user_fund1, mock_user_fund2]
    mock_query_user_fund.filter.return_value.first.return_value = None # No owner found

    mock_query_fund = MagicMock()
    mock_query_fund.filter.return_value.first.side_effect = [mock_fund1, mock_fund2]
    
    def side_effect(model):
        if model == UserFund:
            return mock_query_user_fund
        if model == Fund:
            return mock_query_fund
        return MagicMock()

    mock_db_session.query.side_effect = side_effect
    
    # Override dependency
    app = client.app
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    
    response = client.get("/api/v1/funds")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == ResponseStatus.SUCCESS
    assert len(data["data"]) == 2
    assert data["data"][0]["name"] == "Test Fund 1"
    assert data["data"][0]["role"] == "OWNER"
    assert data["data"][1]["name"] == "Test Fund 2"
    assert data["data"][1]["role"] == "TRADER"
    
    app.dependency_overrides.pop(get_current_user)


def test_get_funds_empty(client, mock_db_session, mock_current_user):
    """Test GET /api/v1/funds returns empty array when user has no funds"""
    from app.security import get_current_user
    
    # Mock DB returning empty list
    mock_db_session.query.return_value.filter.return_value.all.return_value = []
    
    app = client.app
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    
    response = client.get("/api/v1/funds")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == ResponseStatus.SUCCESS
    assert len(data["data"]) == 0
    
    app.dependency_overrides.pop(get_current_user)


def test_get_fund_by_id_success(client, mock_db_session, mock_current_user):
    """Test GET /api/v1/funds/{fund_id} returns fund details"""
    from app.security import get_current_user
    
    fund_id = uuid.uuid4()
    
    mock_fund = MagicMock(spec=Fund)
    mock_fund.id = fund_id
    mock_fund.name = "Test Fund"
    mock_fund.description = "Test Description"
    mock_fund.strategy_type = "MTF_SMC_BASIC"
    mock_fund.asset_classes = ["FX"]
    mock_fund.max_risk_per_trade = 10.0
    mock_fund.default_lot_size = 0.01
    mock_fund.max_drawdown_threshold = 10.0
    mock_fund.max_portfolio_beta = 0.5
    mock_fund.gross_exposure_limit = 100.0
    mock_fund.net_exposure_limit = 50.0
    mock_fund.position_limit_single = 5.0
    mock_fund.position_limit_sector = 20.0
    
    mock_user_fund = MagicMock(spec=UserFund)
    mock_user_fund.role = MagicMock(value="OWNER")
    
    mock_user = MagicMock(spec=User)
    mock_user.username = "testowner"

    # Mock DB queries
    def query_side_effect(model):
        mock_query = MagicMock()
        if model == UserFund:
            mock_query.filter.return_value.first.return_value = mock_user_fund
        elif model == Fund:
            mock_query.filter.return_value.first.return_value = mock_fund
        elif model == User:
            mock_query.filter.return_value.first.return_value = mock_user
        return mock_query
    
    mock_db_session.query.side_effect = query_side_effect
    
    app = client.app
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    
    response = client.get(f"/api/v1/funds/{fund_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == ResponseStatus.SUCCESS
    assert data["data"]["name"] == "Test Fund"
    assert data["data"]["role"] == "OWNER"
    
    app.dependency_overrides.pop(get_current_user)


def test_get_fund_no_access(client, mock_db_session, mock_current_user):
    """Test GET /api/v1/funds/{fund_id} returns 404 when user has no access"""
    from app.security import get_current_user
    
    fund_id = uuid.uuid4()
    
    # Mock DB returning None (no access)
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    
    app = client.app
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    
    response = client.get(f"/api/v1/funds/{fund_id}")
    
    assert response.status_code == 404
    data = response.json()
    assert data["status"] == ResponseStatus.ERROR
    
    app.dependency_overrides.pop(get_current_user)


def test_get_fund_not_found(client, mock_db_session, mock_current_user):
    """Test GET /api/v1/funds/{fund_id} returns 404 when fund doesn't exist"""
    from app.security import get_current_user
    
    fund_id = uuid.uuid4()
    
    mock_user_fund = MagicMock(spec=UserFund)
    mock_user_fund.role = MagicMock(value="OWNER")
    
    # Mock DB queries - user has access but fund doesn't exist
    def query_side_effect(model):
        mock_query = MagicMock()
        if model == UserFund:
            mock_query.filter.return_value.first.return_value = mock_user_fund
        elif model == Fund:
            mock_query.filter.return_value.first.return_value = None
        return mock_query
    
    mock_db_session.query.side_effect = query_side_effect
    
    app = client.app
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    
    response = client.get(f"/api/v1/funds/{fund_id}")
    
    assert response.status_code == 404
    data = response.json()
    assert data["status"] == ResponseStatus.ERROR
    
    app.dependency_overrides.pop(get_current_user)


def test_create_fund_with_risk_params(client, mock_db_session, mock_current_user):
    """Test POST /api/v1/funds with risk parameters"""
    from app.security import get_current_user
    from app.models.user import UserRole
    
    # Payload with risk params
    payload = {
        "name": "Risk Fund",
        "description": "Fund with risk settings",
        "strategy_type": "MULTI_ASSET",
        "asset_classes": ["FX", "CRYPTO"],
        "max_risk_per_trade": 50.0,
        "default_lot_size": 0.5,
        "max_drawdown_threshold": 10.0,
        "max_portfolio_beta": 0.5
    }
    
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None
    mock_db_session.refresh.return_value = None
    
    app = client.app
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    
    response = client.post("/api/v1/funds", json=payload)
    
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == ResponseStatus.SUCCESS
    assert data["data"]["name"] == "Risk Fund"
    assert data["data"]["strategy_type"] == "MULTI_ASSET"
    assert data["data"]["asset_classes"] == ["FX", "CRYPTO"]
    assert float(data["data"]["max_risk_per_trade"]) == 50.0
    assert float(data["data"]["default_lot_size"]) == 0.5
    assert float(data["data"]["max_portfolio_beta"]) == 0.5
    
    # Verify DB calls
    assert mock_db_session.add.call_count == 2 # Fund + UserFund
    
    # Check that the Fund object was created with correct attributes
    # The first call to add should be the Fund
    fund_arg = mock_db_session.add.call_args_list[0][0][0]
    assert fund_arg.name == "Risk Fund"
    assert fund_arg.max_risk_per_trade == 50.0
    assert fund_arg.strategy_type == "MULTI_ASSET"
    
    app.dependency_overrides.pop(get_current_user)


def test_update_fund_risk_params(client, mock_db_session, mock_current_user):
    """Test PUT /api/v1/funds/{fund_id} updating risk params"""
    from app.security import get_current_user
    from app.models.user import UserRole
    
    fund_id = uuid.uuid4()
    
    # Mock existing fund and user access
    mock_fund = MagicMock(spec=Fund)
    mock_fund.id = fund_id
    mock_fund.name = "Old Name"
    mock_fund.description = "Old Desc"
    mock_fund.max_risk_per_trade = 10.0
    mock_fund.strategy_type = "MTF_SMC_BASIC"
    mock_fund.asset_classes = ["FX"]
    mock_fund.default_lot_size = 0.01
    mock_fund.max_drawdown_threshold = 10.0
    mock_fund.max_portfolio_beta = 0.5
    mock_fund.gross_exposure_limit = 100.0
    mock_fund.net_exposure_limit = 50.0
    mock_fund.position_limit_single = 5.0
    mock_fund.position_limit_sector = 20.0
    
    mock_user_fund = MagicMock(spec=UserFund)
    mock_user_fund.role = UserRole.OWNER 

    def query_side_effect(model):
        mock_query = MagicMock()
        if model == UserFund:
            mock_query.filter.return_value.first.return_value = mock_user_fund
        elif model == Fund:
            mock_query.filter.return_value.first.return_value = mock_fund
        return mock_query
    
    mock_db_session.query.side_effect = query_side_effect
    
    app = client.app
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    
    payload = {
        "max_risk_per_trade": 25.0,
        "default_lot_size": 0.2
    }
    
    response = client.put(f"/api/v1/funds/{fund_id}", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == ResponseStatus.SUCCESS
    
    # Verify mock update
    assert mock_fund.max_risk_per_trade == 25.0
    assert mock_fund.default_lot_size == 0.2
    assert mock_db_session.commit.called
    
    app.dependency_overrides.pop(get_current_user)
