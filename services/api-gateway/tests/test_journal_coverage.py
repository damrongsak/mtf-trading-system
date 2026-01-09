import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from app.security import get_current_user
from app.models.journal import JournalEntry, MentalState, RootCauseAnalysis, TimelineEvent
from app.models.user import User
from app.models.trade import Trade, TradeDirection
import uuid

@pytest.fixture
def local_mock_db():
    return MagicMock()

@pytest.fixture(autouse=True)
def override_dependency(local_mock_db):
    app.dependency_overrides[get_db] = lambda: local_mock_db
    yield
    app.dependency_overrides = {}

@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = str(uuid.uuid4())
    user.username = "testuser"
    return user

@pytest.fixture
def client(mock_user):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides[get_current_user] = None

def test_update_journal_entry_nested_create(client, local_mock_db, mock_user):
    entry_id = str(uuid.uuid4())
    mock_entry = MagicMock(spec=JournalEntry)
    mock_entry.id = entry_id
    mock_entry.user_id = mock_user.id
    mock_entry.symbol = "AAPL"
    mock_entry.direction = "LONG"
    mock_entry.session = "New York"
    mock_entry.game_level = None
    mock_entry.mental_state = None
    mock_entry.root_cause = None
    
    # Specific query return
    local_mock_db.query.return_value.filter.return_value.first.return_value = mock_entry
    
    payload = {
        "symbol": "AAPL",
        "direction": "LONG", # Required
        "mental_state": {"mood": "Happy", "energy": 5},
        "root_cause": {"problem": "FOMO", "flaw": "Impatience"}
    }
    
    response = client.put(f"/api/v1/journal/{entry_id}", json=payload)
    if response.status_code != 200:
        print(response.json())
    assert response.status_code == 200

def test_update_journal_entry_nested_update(client, local_mock_db, mock_user):
    entry_id = str(uuid.uuid4())
    mock_entry = MagicMock(spec=JournalEntry)
    mock_entry.id = entry_id
    mock_entry.user_id = mock_user.id
    mock_entry.symbol = "AAPL"
    mock_entry.direction = "SHORT"
    mock_entry.session = "London"
    mock_entry.game_level = None
    
    # Existing nested objects with valid fields
    mock_mental = MagicMock(spec=MentalState)
    mock_mental.greed_level = 0
    mock_mental.fear_level = 0
    mock_mental.tilt_level = 0
    mock_mental.confidence_level = 0
    mock_mental.discipline_level = 0
    mock_entry.mental_state = mock_mental
    
    mock_root = MagicMock(spec=RootCauseAnalysis)
    mock_root.problem = "Legacy Problem"
    mock_root.why_exist = ""
    mock_root.flaw = "Greed"
    mock_root.correction = ""
    mock_root.logic = ""
    mock_entry.root_cause = mock_root
    
    local_mock_db.query.return_value.filter.return_value.first.return_value = mock_entry
    
    payload = {
        "symbol": "AAPL",
        "direction": "short", # Required
        "mental_state": {"mood": "Sad"}, # update
        "root_cause": {"flaw": "Greed"} # update
    }
    
    response = client.put(f"/api/v1/journal/{entry_id}", json=payload)
    assert response.status_code == 200
    
    # setattr should have been called on mocks

def test_delete_journal_entry(client, local_mock_db, mock_user):
    entry_id = str(uuid.uuid4())
    mock_entry = MagicMock(spec=JournalEntry)
    mock_entry.id = entry_id
    
    # When filter is called, return the query obj which returns mock_entry on first()
    local_mock_db.query.return_value.filter.return_value.first.return_value = mock_entry
    
    response = client.delete(f"/api/v1/journal/{entry_id}")
    assert response.status_code == 204
    local_mock_db.delete.assert_called()
    local_mock_db.commit.assert_called()

def test_import_trades(client, local_mock_db, mock_user):
    # Setup mocks for different models
    # 1. JournalEntry query (for duplicates) -> returns []
    # 2. Trade query (for fetching) -> returns [trade]
    
    mock_trade = MagicMock(spec=Trade)
    mock_trade.trade_id = uuid.uuid4()
    mock_trade.symbol = "XAU/USD"
    mock_trade.direction = TradeDirection.LONG
    mock_trade.risk_usd = 10.0
    mock_trade.pnl_usd = 20.0
    mock_trade.entry_price = 2000.0
    
    def side_effect(model):
        m = MagicMock()
        if model == JournalEntry or (isinstance(model, MagicMock) and model == JournalEntry): 
             # Check attribute access usually (model.trade_id)
             # But here query(JournalEntry.trade_id)
             pass
        # Simplification: check args or just return different mocks for sequential calls if we can't distinguish easy
        return m

    # Better: assign return values dynamically based on what's expected
    # First call is query(JournalEntry.trade_id)
    # Second call is query(Trade)
    
    q1 = MagicMock()
    q1.filter.return_value.all.return_value = [] # No existing
    
    q2 = MagicMock()
    q2.filter.return_value.all.return_value = [mock_trade]
    
    local_mock_db.query.side_effect = [q1, q2] 
    
    payload = {"trade_ids": [str(mock_trade.trade_id)]}
    
    response = client.post("/api/v1/journal/import", json=payload)
    if response.status_code != 200:
        print(response.json())

    assert response.status_code == 200
    data = response.json()
    assert data["data"]["imported_count"] == 1
    assert data["data"]["skipped_count"] == 0
    local_mock_db.add.assert_called()
