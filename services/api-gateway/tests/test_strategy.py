from unittest.mock import MagicMock
from app.models.strategy import Strategy
from app.models.user_fund import Fund
from app.schemas.response import ResponseStatus
import uuid

def test_create_strategy_success(client, mock_db_session):
    fund_id = str(uuid.uuid4())
    payload = {
        "name": "My Strategy",
        "fund_id": fund_id,
        "type": "MOMENTUM",
        "config_json": {"param": 1}
    }
    
    # Mock Fund existence check
    mock_fund = MagicMock(spec=Fund)
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_fund
    
    # Mock OAuth2 token dependency
    headers = {"Authorization": "Bearer fake_token"}
    
    response = client.post("/api/v1/strategies/", json=payload, headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == ResponseStatus.SUCCESS
    assert data["data"]["name"] == "My Strategy"
    
    assert mock_db_session.add.called
    assert mock_db_session.commit.called

def test_create_strategy_fund_not_found(client, mock_db_session):
    fund_id = str(uuid.uuid4())
    payload = {
        "name": "My Strategy",
        "fund_id": fund_id,
        "type": "MOMENTUM",
        "config_json": {"param": 1}
    }
    
    # Mock Fund existence check returning None
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    
    headers = {"Authorization": "Bearer fake_token"}
    response = client.post("/api/v1/strategies/", json=payload, headers=headers)
    
    assert response.status_code == 404
    data = response.json()
    assert data["status"] == ResponseStatus.ERROR

def test_list_strategies(client, mock_db_session):
    fund_id = str(uuid.uuid4())
    
    # Mock pagination query
    mock_query = mock_db_session.query.return_value.filter.return_value
    mock_query.count.return_value = 1
    
    mock_strategy = MagicMock(spec=Strategy)
    mock_strategy.id = uuid.uuid4()
    mock_strategy.name = "Test Strategy"
    mock_strategy.is_active = True
    mock_strategy.type = "MOMENTUM"
    mock_strategy.config_json = {}
    
    mock_query.offset.return_value.limit.return_value.all.return_value = [mock_strategy]
    
    headers = {"Authorization": "Bearer fake_token"}
    response = client.get(f"/api/v1/strategies/?fund_id={fund_id}", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == ResponseStatus.SUCCESS
    assert len(data["data"]) == 1
    assert data["meta"]["total"] == 1