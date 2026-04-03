import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import MagicMock
from app.main import app
from app.security import get_current_user
from datetime import datetime, timezone

@pytest.fixture
def override_auth(mock_current_user):
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)

def test_get_edge_optimization_endpoint(client, mock_db_session, mock_current_user, override_auth):
    # Setup mock return for DB
    mock_query = mock_db_session.query.return_value
    mock_filter1 = mock_query.filter.return_value
    mock_filter2 = mock_filter1.filter.return_value
    mock_filter3 = mock_filter2.filter.return_value
    mock_group = mock_filter3.group_by.return_value
    
    mock_result = MagicMock()
    mock_result.hour = 10
    mock_result.dow = 1
    mock_result.total_pnl = 100.0
    mock_result.trade_count = 1
    mock_result.avg_pnl = 100.0
    
    mock_group.all.return_value = [mock_result]

    response = client.get("/api/v1/analysis/metrics/edge-optimization")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "matrix" in data["data"]
    assert "summary" in data["data"]
