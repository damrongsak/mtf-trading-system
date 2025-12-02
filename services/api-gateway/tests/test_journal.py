from unittest.mock import MagicMock
from app.models.journal import JournalEntry
from app.schemas.response import ResponseStatus
import uuid

def test_create_journal_entry(client, mock_db_session, mock_current_user):
    from app.security import get_current_user
    app = client.app
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    
    payload = {
        "symbol": "XAUUSD",
        "direction": "LONG",
        "entry_price": 2000.0,
        "stop_loss_price": 1990.0,
        "take_profit_price": 2020.0,
        "session": "LONDON",
        "context_score": 8,
        "game_level": "B_GAME"
    }
    
    response = client.post("/api/v1/journal/", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == ResponseStatus.SUCCESS
    assert data["data"]["symbol"] == "XAUUSD"
    
    assert mock_db_session.add.called
    assert mock_db_session.commit.called
    
    app.dependency_overrides.pop(get_current_user)

def test_list_journal_entries(client, mock_db_session, mock_current_user):
    from app.security import get_current_user
    app = client.app
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    
    # Mock pagination query
    mock_query = mock_db_session.query.return_value.filter.return_value
    mock_query.count.return_value = 1
    
    mock_entry = MagicMock(spec=JournalEntry)
    mock_entry.id = uuid.uuid4()
    mock_entry.symbol = "BTCUSD"
    mock_entry.user_id = mock_current_user.id
    mock_entry.direction = "LONG"
    mock_entry.session = "LONDON"
    mock_entry.game_level = "B_GAME"
    mock_entry.mental_state = None
    mock_entry.root_cause = None
    mock_entry.timeline_events = []
    
    mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [mock_entry]
    
    response = client.get("/api/v1/journal/?page=1&per_page=10")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == ResponseStatus.SUCCESS
    assert len(data["data"]) == 1
    assert data["meta"]["total"] == 1
    
    app.dependency_overrides.pop(get_current_user)

def test_get_journal_entry_found(client, mock_db_session, mock_current_user):
    from app.security import get_current_user
    app = client.app
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    
    entry_id = str(uuid.uuid4())
    mock_entry = MagicMock(spec=JournalEntry)
    mock_entry.id = uuid.UUID(entry_id)
    mock_entry.symbol = "BTCUSD"
    mock_entry.user_id = mock_current_user.id
    mock_entry.direction = "LONG"
    mock_entry.session = "LONDON"
    mock_entry.game_level = "B_GAME"
    mock_entry.mental_state = None
    mock_entry.root_cause = None
    mock_entry.timeline_events = []
    
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_entry
    
    response = client.get(f"/api/v1/journal/{entry_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == ResponseStatus.SUCCESS
    assert data["data"]["id"] == entry_id
    
    app.dependency_overrides.pop(get_current_user)

def test_get_journal_entry_not_found(client, mock_db_session, mock_current_user):
    from app.security import get_current_user
    app = client.app
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    
    entry_id = str(uuid.uuid4())
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    
    response = client.get(f"/api/v1/journal/{entry_id}")
    
    assert response.status_code == 404
    data = response.json()
    assert data["status"] == ResponseStatus.ERROR
    
    app.dependency_overrides.pop(get_current_user)