import pytest
from unittest.mock import MagicMock, call
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
import uuid
from datetime import datetime

# Import models to use as spec
from app.models.market import MarketSymbol, MarketCategory
from app.models.candle import Candle
from app.models.data_source import DataSource

@pytest.fixture
def local_mock_db():
    return MagicMock()

@pytest.fixture(autouse=True)
def override_dependency(local_mock_db):
    app.dependency_overrides[get_db] = lambda: local_mock_db
    yield
    app.dependency_overrides = {}

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

# --- Market Data (Categories/Symbols) ---

def test_get_categories(client, local_mock_db):
    cat1 = MagicMock(spec=MarketCategory)
    cat1.id = uuid.uuid4()
    cat1.name = "Forex"
    cat1.order_index = 0 # Fix Pydantic
    cat1.items = [] # symbols
    
    local_mock_db.query.return_value.filter.return_value.options.return_value.order_by.return_value.all.return_value = [cat1]
    
    response = client.get("/api/v1/market/categories")
    assert response.status_code == 200
    assert response.json()[0]["name"] == "Forex"

def test_create_category_success(client, local_mock_db):
    # Determine result of finding existing
    local_mock_db.query.return_value.filter.return_value.first.return_value = None
    
    def add_effect(c):
        c.id = uuid.uuid4()
        c.order_index = 0 # Fix Pydantic
        c.items = [] # for serialization
    local_mock_db.refresh.side_effect = add_effect
    
    response = client.post("/api/v1/market/categories", json={"name": "Crypto"})
    assert response.status_code == 200
    assert response.json()["name"] == "Crypto"
    local_mock_db.add.assert_called_once()

def test_create_category_duplicate(client, local_mock_db):
    existing = MagicMock(spec=MarketCategory)
    local_mock_db.query.return_value.filter.return_value.first.return_value = existing
    
    response = client.post("/api/v1/market/categories", json={"name": "Crypto"})
    assert response.status_code == 400

def test_add_symbol(client, local_mock_db):
    cat_id = uuid.uuid4()
    cat = MagicMock(spec=MarketCategory)
    cat.id = cat_id
    local_mock_db.query.return_value.filter.return_value.first.return_value = cat
    
    def add_effect(s):
        s.id = uuid.uuid4()
        s.category_id = cat_id
        s.order_index = 0 # Fix Pydantic
        # s.broker = None # handled by schema default
    local_mock_db.refresh.side_effect = add_effect

    payload = {"symbol": "BTC/USD", "display_name": "Bitcoin"}
    response = client.post(f"/api/v1/market/categories/{cat_id}/symbols", json=payload)
    if response.status_code != 200:
        print(f"DEBUG SYMBOL: {response.json()}")
    assert response.status_code == 200
    assert response.json()["symbol"] == "BTC/USD"

def test_add_symbol_cat_not_found(client, local_mock_db):
    local_mock_db.query.return_value.filter.return_value.first.return_value = None
    response = client.post(f"/api/v1/market/categories/{uuid.uuid4()}/symbols", json={"symbol": "A"})
    assert response.status_code == 404

# --- Market (Candles) ---

def test_get_candles_empty(client, local_mock_db):
    # Mock MarketSymbol lookup fail
    local_mock_db.query.return_value.join.return_value.filter.return_value.first.return_value = None
    
    response = client.get("/api/v1/market/candles?symbol=EUR_USD&timeframe=H1") # Fix path
    assert response.status_code == 200
    assert response.json()["data"] == []

def test_get_candles_success(client, local_mock_db):
    # Mock MarketSymbol
    ms = MagicMock(spec=MarketSymbol)
    ms.id = uuid.uuid4()
    
    # query(MarketSymbol).join...
    q_ms = local_mock_db.query.return_value.join.return_value.filter.return_value
    q_ms.first.return_value = ms
    
    c1 = MagicMock(spec=Candle)
    c1.timestamp = datetime(2023, 1, 1, 10, 0)
    c1.open = 1.1
    c1.high = 1.2
    c1.low = 1.0
    c1.close = 1.15
    c1.volume = 100
    
    q_ms.first.return_value = ms
    
    local_mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [c1]
    
    response = client.get("/api/v1/market/candles?symbol=EUR_USD&timeframe=H1") # Fix path
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1
    assert response.json()["data"][0]["close"] == 1.15

