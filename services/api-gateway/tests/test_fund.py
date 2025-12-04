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
    
    mock_fund2 = MagicMock(spec=Fund)
    mock_fund2.id = fund2_id
    mock_fund2.name = "Test Fund 2"
    mock_fund2.description = "Description 2"
    
    mock_user_fund1 = MagicMock(spec=UserFund)
    mock_user_fund1.fund_id = fund1_id
    mock_user_fund1.role = MagicMock(value="OWNER")
    
    mock_user_fund2 = MagicMock(spec=UserFund)
    mock_user_fund2.fund_id = fund2_id
    mock_user_fund2.role = MagicMock(value="TRADER")
    
    # Mock DB queries - create separate mock_query instances
    user_fund_query = MagicMock()
    user_fund_query.filter.return_value.all.return_value = [mock_user_fund1, mock_user_fund2]
    
    fund_query1 = MagicMock()
    fund_query1.filter.return_value.first.return_value = mock_fund1
    
    fund_query2 = MagicMock()
    fund_query2.filter.return_value.first.return_value = mock_fund2
    
    # Setup query side effect to return correct mock based on model type
    query_calls = [user_fund_query, fund_query1, fund_query2]
    mock_db_session.query.side_effect = query_calls
    
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
    
    mock_user_fund = MagicMock(spec=UserFund)
    mock_user_fund.role = MagicMock(value="OWNER")
    
    # Mock DB queries
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
