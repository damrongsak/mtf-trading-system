import pytest
from unittest.mock import MagicMock, patch
from app.schemas.response import ResponseStatus
from datetime import datetime
import uuid

@pytest.mark.asyncio
async def test_get_latency_heatmap(client, mock_db_session):
    # Mock data
    mock_row = MagicMock()
    mock_row.hour = 10
    mock_row.symbol = "XAU_USD"
    mock_row.avg_latency = 45.5
    mock_row.min_latency = 30.0
    mock_row.max_latency = 60.0
    mock_row.count = 5

    # mock_db_session is already injected by the 'client' fixture via dependency_overrides
    mock_db_session.query.return_value.filter.return_value.group_by.return_value.all.return_value = [mock_row]
    
    response = client.get("/api/v1/analytics/latency/heatmap")
        
    assert response.status_code == 200
    data = response.json()
    assert len(data["buckets"]) == 1
    assert data["buckets"][0]["hour"] == 10
    assert data["buckets"][0]["symbol"] == "XAU_USD"
    assert data["buckets"][0]["avg_latency_ms"] == 45.5

@pytest.mark.asyncio
async def test_get_performance_comparison(client, mock_db_session):
    sig_id = str(uuid.uuid4())
    mock_res = MagicMock()
    mock_res.signal_id = sig_id
    mock_res.symbol = "XAU_USD"
    mock_res.shadow_pnl = 100.0
    mock_res.live_pnl = 95.0
    mock_res.shadow_latency = 10.0
    mock_res.live_latency = 15.0

    # mock_db_session.execute().all()
    mock_db_session.execute.return_value.all.return_value = [mock_res]
    
    response = client.get("/api/v1/analytics/performance/comparison")
        
    assert response.status_code == 200
    data = response.json()
    assert len(data["comparisons"]) == 1
    item = data["comparisons"][0]
    assert item["signal_id"] == sig_id
    assert item["slippage_usd"] == -5.0 # 95.0 - 100.0
    assert item["latency_gap_ms"] == 5.0 # 15.0 - 10.0

@pytest.mark.asyncio
async def test_get_execution_rejections(client, mock_db_session):
    mock_rej = MagicMock()
    mock_rej.reason = "RISK_LIMIT_EXCEEDED"
    mock_rej.count = 3
    mock_rej.latest_at = datetime.utcnow()

    mock_db_session.query.return_value.filter.return_value.group_by.return_value.all.return_value = [mock_rej]
    
    response = client.get("/api/v1/analytics/execution/rejections")
        
    assert response.status_code == 200
    data = response.json()
    assert data["total_rejections"] == 3
    assert data["rejections"][0]["reason"] == "RISK_LIMIT_EXCEEDED"
