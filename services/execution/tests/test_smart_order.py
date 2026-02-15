from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from app.main import app
from app.models import BrokerAccount
from app.database import get_db
import uuid

client = TestClient(app)

# Mock DB Session
from app.models import BrokerAccount, Fund
from unittest.mock import AsyncMock

async def override_get_db():
    try:
        db = MagicMock()
        db.execute = AsyncMock()
        
        # 1. Mock Objects
        mock_fund_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
        mock_account_id = uuid.UUID("12345678-1234-5678-1234-567812345678")
        
        mock_account = BrokerAccount(
            id=mock_account_id,
            is_active=True, # Required for validation
            broker_name="OANDA",
            credentials_encrypted=b"encrypted_creds", # Correct field name
            account_number="123", # Correct field name is account_number not account_id
            environment="practice", # Correct field
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
        
        # 2. Side Effect for db.execute(select(...))
        # This is tricky because select() returns a complex object.
        # We assume the query structure.
        
        def execute_side_effect(statement):
            # Inspect string representation or compiled structure of statement
            stmt_str = str(statement)
            
            mock_result = MagicMock()
            
            if "broker_account" in stmt_str:
                mock_result.scalars.return_value.first.return_value = mock_account
                mock_result.scalars.return_value.all.return_value = [mock_account]
            elif "fund" in stmt_str:
                mock_result.scalars.return_value.first.return_value = mock_fund
                mock_result.scalars.return_value.all.return_value = [mock_fund]
            else:
                mock_result.scalars.return_value.first.return_value = None
                mock_result.scalars.return_value.all.return_value = []
                
            return mock_result
            
        db.execute.side_effect = execute_side_effect
        
        yield db
    finally:
        pass

app.dependency_overrides[get_db] = override_get_db

@patch("app.services.order_service.BrokerFactory")
@patch("app.services.order_service.decrypt_data")
def test_place_smart_order_dynamic_risk(mock_decrypt, mock_factory):
    # Setup Mock Adapter
    mock_adapter = MagicMock()
    mock_factory.get_adapter.return_value = mock_adapter
    mock_decrypt.return_value = {"api_key": "xyz", "account_id": "123"}
    
    # 1. Mock Live Price (AUD_USD)
    mock_adapter.get_current_price = AsyncMock(return_value=0.7000)
    
    # 2. Mock Order Placement Response
    mock_adapter.place_market_order = AsyncMock(return_value={
        "orderFillTransaction": {
            "id": "555",
            "instrument": "AUD_USD",
            "units": "10", # Checked below
            "price": "0.7000",
            "time": "2024-01-01T12:00:00Z"
        }
    })
    # Mock Summary for Risk Calc
    mock_adapter.get_account_summary = AsyncMock(return_value={"NAV": "1000"})
    # Mock Order Book
    mock_adapter.get_order_book = AsyncMock(return_value={"asks": [], "bids": []})

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
        "reason": "Unit Test",
        "signal_id": "sig-1"
    }
    
    response = client.post("/smart-orders", json=payload)
    
    # 4. Assertions
    assert response.status_code == 200, f"Response: {response.text}"
    resp_json = response.json()
    assert resp_json["data"]["id"] == "555"
    
    # Verify Logic:
    # Dist = |0.7000 - 0.6000| = 0.1
    # Units = 1.0 / 0.1 = 10.0
    # Adapter should receive units=10
    mock_adapter.place_market_order.assert_called_once()
    call_kwargs = mock_adapter.place_market_order.call_args[1]
    assert call_kwargs["units"] == 10 # Integer units
    assert call_kwargs["sl_price"] == 0.6000

@patch("app.services.order_service.BrokerFactory")
@patch("app.services.order_service.decrypt_data")
def test_place_smart_order_default_risk(mock_decrypt, mock_factory):
    # Test fallback to default $10 risk
    mock_adapter = MagicMock()
    mock_factory.get_adapter.return_value = mock_adapter
    mock_decrypt.return_value = {"api_key": "xyz", "account_id": "123"}
    
    mock_adapter.get_account_summary = AsyncMock(return_value={"NAV": "1000"})
    mock_adapter.get_order_book = AsyncMock(return_value={"asks": [], "bids": []})
    mock_adapter.get_current_price = AsyncMock(return_value=0.7000)
    mock_adapter.place_market_order = AsyncMock(return_value={"orderFillTransaction": {"id": "1", "units": "100", "price": "0.7", "instrument": "AUD_USD", "time": "T"}})

    payload = {
        "broker_account_id": "12345678-1234-5678-1234-567812345678",
        "symbol": "AUD_USD",
        "direction": "BULLISH",
        "stop_loss": 0.6000, # Dist=0.10
        # NO risk_usd provided
        "generated_by": "TestStrategy",
        "reason": "Test",
        "signal_id": "sig-2"
    }
    
    response = client.post("/smart-orders", json=payload)
    assert response.status_code == 200, f"Response: {response.text}"
    
    # Logic: Risk $10 (default) / Dist 0.10 = 100 Units
    call_kwargs = mock_adapter.place_market_order.call_args[1]
    assert call_kwargs["units"] == 100

@patch("app.services.order_service.BrokerFactory")
@patch("app.services.order_service.decrypt_data")
def test_place_smart_order_price_fail(mock_decrypt, mock_factory):
    mock_adapter = MagicMock()
    mock_factory.get_adapter.return_value = mock_adapter
    mock_decrypt.return_value = {"api_key": "xyz", "account_id": "123"}
    
    # Mock Price Fetch Failure
    mock_adapter.get_current_price = AsyncMock(side_effect=Exception("API Error"))
    mock_adapter.get_account_summary = AsyncMock(return_value={"NAV": "1000"})

    payload = {
        "broker_account_id": "12345678-1234-5678-1234-567812345678",
        "symbol": "AUD_USD",
        "direction": "BULLISH",
        "stop_loss": 0.6000,
        "generated_by": "TestStrategy",
        "reason": "Fail Test",
        "signal_id": "sig-3"
    }
    
    response = client.post("/smart-orders", json=payload)
    
    # Should be 502 Bad Gateway or 500
    assert response.status_code == 500 # Internal Error
    assert "Failed to fetch live price" in response.json()["detail"]
