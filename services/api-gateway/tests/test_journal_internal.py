import uuid
from app.schemas.response import ResponseStatus

def test_get_pending_ai_trades_empty(client, mock_db_session):
    # Mocking the subquery and filter logic so that query().filter().order_by().limit().all() returns an empty list
    mock_db_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
    
    response = client.get("/api/v1/journal/internal/memory/pending-trades")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == ResponseStatus.SUCCESS
    assert isinstance(data["data"], list)
    assert len(data["data"]) == 0

def test_save_ai_insight_not_found(client, mock_db_session):
    # Mock Trade not found
    mock_db_session.query.return_value.filter.return_value.first.return_value = None

    payload = {
        "trade_id": str(uuid.uuid4()),
        "ai_insight": "Test insight",
        "game_level": "A_GAME"
    }
    
    response = client.post("/api/v1/journal/internal/memory/save-insight", json=payload)
    
    assert response.status_code == 404
    data = response.json()
    assert data["status"] == ResponseStatus.ERROR
    assert data["detail"] == "Trade not found"
