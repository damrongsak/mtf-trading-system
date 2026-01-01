import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from app.models.transaction import Transaction, TransactionType
from app.models.user_fund import Fund
import uuid
from datetime import datetime

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

from datetime import datetime, timezone

def test_list_transactions(client, local_mock_db):
    fund_id = uuid.uuid4()
    t1 = MagicMock(spec=Transaction)
    t1.id = uuid.uuid4()
    t1.amount = 100.0
    t1.fund_id = fund_id
    t1.transaction_date = datetime.now(timezone.utc)
    t1.type = TransactionType.DEPOSIT
    t1.currency = "USD"
    t1.status = "COMPLETED"
    t1.reference = "REF123"
    t1.description = "Test Trans"
    t1.payment_method = "Bank"
    t1.trading_account = "ACC1"
    
    q = local_mock_db.query.return_value.filter.return_value
    q.count.return_value = 1
    q.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [t1]
    
    response = client.get(f"/api/v1/transactions?fund_id={fund_id}")
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1

def test_create_transaction(client, local_mock_db):
    fund_id = uuid.uuid4()
    # Mock Fund
    local_mock_db.query.return_value.filter.return_value.first.return_value = MagicMock(spec=Fund)
    
    # Mock Transaction creation return
    def add_effect(obj):
        obj.id = uuid.uuid4()
        obj.transaction_date = datetime.now(timezone.utc)
        obj.status = "COMPLETED"
        obj.reference = ""
        
    local_mock_db.refresh.side_effect = add_effect
    
    payload = {
        "fund_id": str(fund_id),
        "transaction_date": datetime.now(timezone.utc).isoformat(),
        "type": "DEPOSIT",
        "amount": 1000.0,
        "currency": "USD",
        "description": "Test Deposit",
         "status": "COMPLETED",
         "reference": "REF",
         "payment_method": "Bank",
         "trading_account": "ACC"
    }
    
    response = client.post("/api/v1/transactions", json=payload)
    if response.status_code != 201:
        print(f"DEBUG: {response.json()}")
        
    assert response.status_code == 201
    
def test_get_balance(client, local_mock_db):
    fund_id = uuid.uuid4()
    local_mock_db.query.return_value.filter.return_value.first.return_value = MagicMock(spec=Fund)
    
    # Mock scalar() return values in sequence
    mock_scalar = local_mock_db.query.return_value.filter.return_value.scalar
    mock_scalar.side_effect = [5000.0, 2000.0]
    
    response = client.get(f"/api/v1/transactions/balance?fund_id={fund_id}")
    assert response.status_code == 200
    assert response.json()["data"]["balance"] == 3000.0

def test_update_transaction(client, local_mock_db):
    tid = uuid.uuid4()
    t = MagicMock(spec=Transaction)
    t.id = tid
    t.description = "Old"
    t.fund_id = uuid.uuid4()
    t.type = TransactionType.DEPOSIT
    t.amount = 100.0
    t.currency = "USD"
    t.status = "COMPLETED"
    t.reference = "REF"
    t.payment_method = "Bank"
    t.trading_account = "ACC"
    
    local_mock_db.query.return_value.filter.return_value.first.return_value = t
    
    payload = {
        "fund_id": str(t.fund_id),
        "transaction_date": datetime.now(timezone.utc).isoformat(),
        "type": "WITHDRAWAL",
        "amount": 500.0,
        "description": "Updated",
        "currency": "USD",
        "status": "COMPLETED",
        "reference": "REF",
        "payment_method": "Bank",
        "trading_account": "ACC"
    }
    
    response = client.put(f"/api/v1/transactions/{tid}", json=payload)
    assert response.status_code == 200
    assert t.description == "Updated"

def test_delete_transaction(client, local_mock_db):
    tid = uuid.uuid4()
    t = MagicMock(spec=Transaction)
    local_mock_db.query.return_value.filter.return_value.first.return_value = t
    
    response = client.delete(f"/api/v1/transactions/{tid}")
    assert response.status_code == 200
    local_mock_db.delete.assert_called_once_with(t)
