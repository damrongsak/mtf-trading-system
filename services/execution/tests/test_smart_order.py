from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from app.main import app
from app.models import BrokerAccount
from app.database import get_db
import uuid

client = TestClient(app)

# Mock DB Session
from app.models import BrokerAccount, Fund

def override_get_db():
    try:
        db = MagicMock()
        
        # 1. Mock Objects
        mock_fund_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
        mock_account_id = uuid.UUID("12345678-1234-5678-1234-567812345678")
        
        mock_account = BrokerAccount(
            id=mock_account_id,
            broker_name="OANDA",
            credentials={"api_key": "xyz", "account_id": "123"},
            account_id="123",
            fund_id=mock_fund_id, # Link to Fund
            supported_symbols=["AUD_USD", "XAU_USD"] # Whitelist for strict check
        )
        
        mock_fund = Fund(
            id=mock_fund_id,
            strategy_type="MACD", # Required
            max_risk_per_trade=10.0,
            risk_percentage=0.01,
            asset_classes=["Forex"], # Required
            default_lot_size=0.01   # Required
        )
        
        # 2. Side Effect for db.query(Model)
        def query_side_effect(model):
            query_mock = MagicMock()
            if model == BrokerAccount:
                query_mock.filter.return_value.first.return_value = mock_account
            elif model == Fund:
                query_mock.filter.return_value.first.return_value = mock_fund
            return query_mock
            
        db.query.side_effect = query_side_effect
        
        yield db
    finally:
        pass

app.dependency_overrides[get_db] = override_get_db

@patch("app.main.BrokerFactory")
def test_place_smart_order_dynamic_risk(mock_factory):
    # Setup Mock Adapter
    mock_adapter = MagicMock()
    mock_factory.get_adapter.return_value = mock_adapter
    
    # 1. Mock Live Price (AUD_USD)
    mock_adapter.get_current_price.return_value = 0.7000
    
    # 2. Mock Order Placement Response
    mock_adapter.place_market_order.return_value = {
        "orderFillTransaction": {
            "id": "555",
            "instrument": "AUD_USD",
            "units": "10", # Checked below
            "price": "0.7000",
            "time": "2024-01-01T12:00:00Z"
        }
    }
    # Mock Summary for Risk Calc
    mock_adapter.get_summary.return_value = {"NAV": "1000"}
    # Mock Order Book
    mock_adapter.get_order_book.return_value = {"asks": [], "bids": []}

    # 3. Request
    # We want Units = 10.
    # Risk = 1.0 USD (Small risk for testing)
    # Dist = 0.1000 (1000 pips) -> |0.7000 - 0.6000|
    # Units = 1.0 / 0.1 = 10.0
    payload = {
        "broker_account_id": "12345678-1234-5678-1234-567812345678",
        "symbol": "AUD_USD",
        "direction": "BULLISH",
        "stop_loss": 0.6000, 
        "risk_usd": 1.0,    
        "generated_by": "TestStrategy",
        "reason": "Unit Test"
    }
    
    response = client.post("/smart-orders", json=payload)
    
    # 4. Assertions
    assert response.status_code == 200, f"Response: {response.text}"
    data = response.json()
    assert data["id"] == "555"
    
    # Verify Logic:
    # Dist = |0.7000 - 0.6000| = 0.1
    # Units = 1.0 / 0.1 = 10.0
    # Adapter should receive units=10
    mock_adapter.place_market_order.assert_called_once()
    call_kwargs = mock_adapter.place_market_order.call_args[1]
    assert call_kwargs["units"] == 10 # Integer units
    assert call_kwargs["sl_price"] == 0.6000

@patch("app.main.BrokerFactory")
def test_place_smart_order_default_risk(mock_factory):
    # Test fallback to default $10 risk
    mock_adapter = MagicMock()
    mock_factory.get_adapter.return_value = mock_adapter
    mock_adapter.get_summary.return_value = {"NAV": "1000"}
    mock_adapter.get_order_book.return_value = {"asks": [], "bids": []}
    mock_adapter.get_current_price.return_value = 0.7000
    mock_adapter.place_market_order.return_value = {"orderFillTransaction": {"id": "1", "units": "100", "price": "0.7", "instrument": "AUD_USD", "time": "T"}}

    payload = {
        "broker_account_id": "12345678-1234-5678-1234-567812345678",
        "symbol": "AUD_USD",
        "direction": "BULLISH",
        "stop_loss": 0.6000, # Dist=0.10
        # NO risk_usd provided
        "generated_by": "TestStrategy",
        "reason": "Test"
    }
    
    response = client.post("/smart-orders", json=payload)
    assert response.status_code == 200
    
    # Logic: Risk $10 (default) / Dist 0.10 = 100 Units
    call_kwargs = mock_adapter.place_market_order.call_args[1]
    assert call_kwargs["units"] == 100

@patch("app.main.BrokerFactory")
def test_place_smart_order_price_fail(mock_factory):
    mock_adapter = MagicMock()
    mock_factory.get_adapter.return_value = mock_adapter
    
    # Mock Price Fetch Failure
    mock_adapter.get_current_price.side_effect = Exception("API Error")
    mock_adapter.get_summary.return_value = {"NAV": "1000"}

    payload = {
        "broker_account_id": "12345678-1234-5678-1234-567812345678",
        "symbol": "AUD_USD",
        "direction": "BULLISH",
        "stop_loss": 0.6000,
        "generated_by": "TestStrategy",
        "reason": "Fail Test"
    }
    
    response = client.post("/smart-orders", json=payload)
    
    # Should be 502 Bad Gateway or 500
    assert response.status_code == 502
    assert "Failed to fetch live price" in response.json()["detail"]
