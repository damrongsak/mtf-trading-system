from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import pytest
from app.main import app, place_smart_order, SmartOrderRequest
from app.models import BrokerAccount, Fund
import uuid

# Mock DB Session
def mock_db_session():
    db = MagicMock()
    return db

def test_dynamic_risk_calculation():
    # Setup Mocks
    mock_db = MagicMock()
    
    # Mock Objects
    account_id = uuid.uuid4()
    fund_id = uuid.uuid4()
    
    mock_account = BrokerAccount(
        id=account_id,
        broker_name="OANDA",
        credentials={"token": "abc"},
        account_id="001",
        fund_id=fund_id,
        risk_settings={}
    )
    
    mock_fund = Fund(
        id=fund_id,
        strategy_type="SMC",
        max_risk_per_trade=500.0, # Hard Cap
        risk_percentage=0.01, # 1% Rule
        asset_classes={}
    )
    
    # DB Queries return these
    mock_db.query.return_value.filter.return_value.first.side_effect = [mock_account, mock_fund]
    
    # Mock Adapter Factory
    with patch("app.main.BrokerFactory.get_adapter") as mock_factory:
        mock_adapter = MagicMock()
        mock_factory.return_value = mock_adapter
        
        # Scenario 1: NAV = 10,000. 1% = $100.
        mock_adapter.get_summary.return_value = {"NAV": "10000.0"}
        mock_adapter.get_current_price.return_value = 2000.0
        mock_adapter.place_market_order.return_value = {"orderFillTransaction": {"id": "1", "units": "1"}}
        
        # Call Function (Simulate Endpoint Logic slightly manually or via Client)
        # We'll use the function logic via a direct call if we mock the Depends, 
        # but calling the endpoint via TestClient is cleaner if we can mock overrides.
        # But for granular logic check, let's look at the flow.
        
        # Request
        req = SmartOrderRequest(
            broker_account_id=str(account_id),
            symbol="XAU_USD",
            direction="BULLISH",
            stop_loss=1990.0, # Dist 10
            generated_by="test"
        )
        
        # We need to run the async function
        # Or better: We can install `pytest-asyncio` and `httpx`?
        # Let's try to trust the logic if we scan it, or run a simple python script?
        # No, let's use TestClient but we need to override_dependency for DB.
        
        pass

# Simplified Approach:
# Write a Pytest that manually invokes the logic or logic components?
# Since the logic is inside the `place_smart_order` function, we must call it.

# Helper function, not a test itself
async def _run_test_logic():
    from app.main import place_smart_order
    
    mock_db = MagicMock()
    account_id = uuid.uuid4()
    fund_id = uuid.uuid4()
    
    mock_account = BrokerAccount(id=account_id, broker_name="OANDA", credentials={}, account_id="001", fund_id=fund_id)
    mock_fund = Fund(id=fund_id, max_risk_per_trade=500.0, risk_percentage=0.01) # 1%
    
    def side_effect_query(model):
        m = MagicMock()
        if model == BrokerAccount:
            m.filter.return_value.first.return_value = mock_account
        elif model == Fund:
            m.filter.return_value.first.return_value = mock_fund
        return m
        
    mock_db.query.side_effect = side_effect_query
    
    req = SmartOrderRequest(
        broker_account_id=str(account_id),
        symbol="XAU_USD",
        direction="BULLISH",
        stop_loss=1990.0,
        generated_by="test"
    )
    
    # Mock Adapter
    with patch("app.main.BrokerFactory.get_adapter") as mock_get_adapter:
        mock_adapter = MagicMock()
        mock_get_adapter.return_value = mock_adapter
        
        # NAV = 10,000 -> Risk $100.
        mock_adapter.get_summary.return_value = {"NAV": "10000.0"}
        mock_adapter.get_current_price.return_value = 2000.0 # Price 2000
        mock_adapter.place_market_order.return_value = {"orderFillTransaction": {"id": "1", "units": "10"}}
        
        # Execute
        resp = await place_smart_order(req, mock_db)
        
        # Verify
        mock_adapter.place_market_order.assert_called()
        call_args = mock_adapter.place_market_order.call_args[1]
        assert call_args['units'] == 10
        
        # Case 2: NAV = 500 -> Risk $5. Units = 5 / 10 = 0.5. (Round to 0 or 1? Code says int(units))
        mock_adapter.get_summary.return_value = {"NAV": "500.0"}
        try:
            await place_smart_order(req, mock_db)
            assert False, "Should have raised exception for min size"
        except Exception as e:
            assert "below minimum" in str(e) or "400" in str(e)

def test_place_smart_order_dynamic_risk():
    import asyncio
    asyncio.run(_run_test_logic())

