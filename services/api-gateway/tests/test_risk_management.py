from unittest.mock import patch, MagicMock, AsyncMock
from app.schemas.response import ResponseStatus
import uuid
from app.security import get_current_user

def test_get_fund_risk_config_success(client):
    fund_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    
    mock_fund = MagicMock()
    mock_fund.id = uuid.UUID(fund_id)
    mock_fund.max_drawdown_threshold = 5.0
    mock_fund.gross_exposure_limit = 100.0
    mock_fund.net_exposure_limit = 15.0
    
    mock_user_fund = MagicMock()
    mock_user_fund.role = "OWNER"
    
    mock_user = MagicMock()
    mock_user.id = uuid.UUID(user_id)
    
    with patch("app.routers.risk.get_redis_client", new_callable=AsyncMock) as mock_get_redis:
        mock_db = MagicMock()
        
        # Mock db.query(UserFund).filter(...).first()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.side_effect = [mock_user_fund, mock_fund]
        
        mock_redis = AsyncMock()
        mock_redis.get.return_value = "0"
        mock_get_redis.return_value = mock_redis
        
        from app.database import get_db
        app = client.app
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        response = client.get(f"/api/v1/risk/fund/{fund_id}/config")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == ResponseStatus.SUCCESS
        assert data["data"]["fund_id"] == fund_id
        # Use float comparison for Numeric fields
        assert float(data["data"]["max_drawdown_threshold"]) == 5.0
        
        app.dependency_overrides.clear()

def test_update_fund_risk_config_success(client):
    fund_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    
    mock_fund = MagicMock()
    mock_fund.id = uuid.UUID(fund_id)
    mock_fund.max_drawdown_threshold = 5.0
    mock_fund.gross_exposure_limit = 100.0
    mock_fund.net_exposure_limit = 15.0
    
    mock_user_fund = MagicMock()
    mock_user_fund.role = "OWNER"
    
    mock_user = MagicMock()
    mock_user.id = uuid.UUID(user_id)
    
    payload = {
        "max_drawdown_threshold": 7.5,
        "gross_exposure_limit": 120.0
    }
    
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_db.query.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.first.side_effect = [mock_user_fund, mock_fund]
    
    from app.database import get_db
    app = client.app
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user
    
    response = client.patch(f"/api/v1/risk/fund/{fund_id}/config", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == ResponseStatus.SUCCESS
    assert mock_fund.max_drawdown_threshold == 7.5
    
    app.dependency_overrides.clear()

def test_toggle_kill_switch_success(client):
    fund_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    
    mock_user_fund = MagicMock()
    mock_user_fund.role = "OWNER"
    
    mock_user = MagicMock()
    mock_user.id = uuid.UUID(user_id)
    
    payload = {
        "active": True,
        "reason": "Emergency testing"
    }
    
    with patch("app.routers.risk.get_redis_client", new_callable=AsyncMock) as mock_get_redis:
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_user_fund
        
        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis
        
        from app.database import get_db
        app = client.app
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        response = client.post(f"/api/v1/risk/fund/{fund_id}/kill-switch", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == ResponseStatus.SUCCESS
        
        mock_redis.set.assert_called_with(f"fund:{fund_id}:halted", "1")
        
        app.dependency_overrides.clear()
