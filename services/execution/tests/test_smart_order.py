from unittest.mock import MagicMock, patch, AsyncMock
import pytest
import uuid
from app.models import BrokerAccount, Fund
from fastapi import HTTPException

@pytest.fixture
def override_price():
    """Setup price service mock."""
    with patch("app.services.order_service.price_service") as mock_price:
        # Default for FX (EUR_USD)
        mock_price.get_latest_price = AsyncMock(return_value=(1.0800, None))
        yield mock_price

@pytest.fixture(autouse=True)
def mock_minimax_global():
    """Globally mock MinimaxService to be safe by default."""
    with patch("app.services.order_service.MinimaxService") as mock_m:
        mock_m.calculate_regret.return_value = (True, 0.0, "Safe")
        mock_m.get_signal_confidence = AsyncMock(return_value=0.8)
        yield mock_m

def get_base_account_mock(account_id, fund_id="fund-1", broker="OANDA"):
    return {
        "id": account_id,
        "is_active": True,
        "broker_name": broker,
        "credentials_encrypted": b"encrypted-blob",
        "fund_id": fund_id,
        "risk_settings": {"max_risk_per_trade": 100.0},
        "account_number": "123",
        "leverage": 30,
        "currency": "USD",
        "environment": "practice",
        "balance_snapshot": 10000.0
    }

def get_base_fund_mock(fund_id="fund-1"):
    return {
        "id": fund_id,
        "max_risk_per_trade": 100.0,
        "risk_percentage": 0.01,
        "max_slippage": 1.0, # Target 1.0 for slippage rejection
        "default_lot_size": 0.01,
        "risk_parity_enabled": False,
        "max_drawdown_threshold": 1000.0,
        "daily_loss_limit": 500.0,
        "max_open_orders": 10,
        "max_spread_pips": 5.0,
        "volatility_threshold": 2.0,
        "asset_risk_caps": {},
        "session_enabled": True,
        "news_enabled": True
    }

def setup_adapter_mocks(mock_adapter, price=1.0800):
    mock_adapter.get_current_price = AsyncMock(return_value=price)
    mock_adapter.get_account_summary = AsyncMock(return_value={"NAV": "10000"})
    mock_adapter.place_order = AsyncMock(return_value={"order_id": "ord-123", "status": "PENDING"})
    mock_adapter.place_market_order = AsyncMock(return_value={"orderFillTransaction": {"id": "fill-123"}})
    mock_adapter.place_limit_order = AsyncMock(return_value={"orderCreateTransaction": {"id": "limit-123"}})
    mock_adapter._resolve_symbol_id_and_lot_size = AsyncMock(return_value=("1", 100000, 4, 5))
    mock_adapter.get_open_positions = AsyncMock(return_value=[])

@patch("app.services.order_service.BrokerFactory")
@patch("app.services.order_service.decrypt_data")
def test_place_smart_order_dynamic_risk(mock_decrypt, mock_factory, test_client, mock_db, override_price, global_cache_mock, mock_minimax_global):
    mock_cache = global_cache_mock
    mock_adapter = MagicMock()
    mock_factory.get_adapter.return_value = mock_adapter
    mock_decrypt.return_value = {"api_key": "xyz", "account_id": "123"}
    setup_adapter_mocks(mock_adapter, price=1.0800)
    override_price.get_latest_price.return_value = (1.0800, None)
    
    account_id = str(uuid.uuid4())
    mock_cache.get_account.return_value = get_base_account_mock(account_id)
    mock_cache.get_credentials.return_value = {"api_key": "xyz", "account_id": "123"}
    mock_cache.get_fund.return_value = get_base_fund_mock()
    mock_cache.get_risk_filters.return_value = []
    
    payload = {
        "broker_account_id": account_id,
        "symbol": "EUR_USD",
        "direction": "BULLISH",
        "stop_loss": 1.0700,
        "generated_by": "TestStrategy",
        "signal_id": "sig-123"
    }
    
    response = test_client.post("/smart-orders", json=payload, headers={"X-Internal-API-Key": "test-key"})
    assert response.status_code == 200

@patch("app.services.order_service.BrokerFactory")
@patch("app.services.order_service.decrypt_data")
def test_place_smart_order_default_risk(mock_decrypt, mock_factory, test_client, mock_db, override_price, global_cache_mock, mock_minimax_global):
    mock_cache = global_cache_mock
    mock_adapter = MagicMock()
    mock_factory.get_adapter.return_value = mock_adapter
    mock_decrypt.return_value = {"api_key": "xyz", "account_id": "123"}
    setup_adapter_mocks(mock_adapter, price=1.0800)
    override_price.get_latest_price.return_value = (1.0800, None)

    account_id = str(uuid.uuid4())
    mock_cache.get_account.return_value = get_base_account_mock(account_id, fund_id="fund-2")
    mock_cache.get_credentials.return_value = {"api_key": "xyz", "account_id": "123"}
    mock_cache.get_fund.return_value = get_base_fund_mock(fund_id="fund-2")
    mock_cache.get_risk_filters.return_value = []
    
    payload = {
        "broker_account_id": account_id,
        "symbol": "EUR_USD",
        "direction": "BULLISH",
        "stop_loss": 1.0700,
        "generated_by": "TestStrategy",
        "signal_id": "sig-default"
    }
    
    response = test_client.post("/smart-orders", json=payload, headers={"X-Internal-API-Key": "test-key"})
    assert response.status_code == 200

@patch("app.services.order_service.BrokerFactory")
@patch("app.services.order_service.decrypt_data")
def test_place_smart_order_price_fail(mock_decrypt, mock_factory, test_client, mock_db, override_price, global_cache_mock, mock_minimax_global):
    mock_cache = global_cache_mock
    mock_adapter = MagicMock()
    mock_factory.get_adapter.return_value = mock_adapter
    mock_decrypt.return_value = {"api_key": "xyz", "account_id": "123"}
    setup_adapter_mocks(mock_adapter)

    override_price.get_latest_price.return_value = (0.0, "Service Down")
    mock_adapter.get_current_price.side_effect = Exception("API Error")
    
    account_id = str(uuid.uuid4())
    mock_cache.get_account.return_value = get_base_account_mock(account_id, fund_id="fund-fail")
    mock_cache.get_fund.return_value = get_base_fund_mock(fund_id="fund-fail")
    mock_cache.get_risk_filters.return_value = []
    
    payload = {
        "broker_account_id": account_id,
        "symbol": "EUR_USD",
        "direction": "BULLISH",
        "stop_loss": 1.0600,
        "generated_by": "TestStrategy",
        "signal_id": "sig-fail"
    }
    
    response = test_client.post("/smart-orders", json=payload, headers={"X-Internal-API-Key": "test-key"})
    assert response.status_code == 500

@patch("app.services.order_service.BrokerFactory")
@patch("app.services.order_service.decrypt_data")
def test_place_smart_order_slippage_rejection(mock_decrypt, mock_factory, test_client, override_price, global_cache_mock, mock_minimax_global):
    mock_cache = global_cache_mock
    mock_adapter = MagicMock()
    mock_factory.get_adapter.return_value = mock_adapter
    mock_decrypt.return_value = {"api_key": "xyz"}
    setup_adapter_mocks(mock_adapter, price=2010.0)
    override_price.get_latest_price.return_value = (2010.0, None)
    
    account_id = str(uuid.uuid4())
    mock_cache.get_account.return_value = get_base_account_mock(account_id, fund_id="fund-slip", broker="cTrader")
    mock_cache.get_fund.return_value = get_base_fund_mock(fund_id="fund-slip")
    mock_cache.get_credentials.return_value = {"api_key": "xyz"}
    mock_cache.get_risk_filters.return_value = []
    
    payload = {
        "broker_account_id": account_id,
        "symbol": "XAU_USD",
        "direction": "BULLISH",
        "stop_loss": 1990.0,
        "signal_price": 2000.0, # Slippage 10.0 > 1.0
        "generated_by": "TestStrategy",
        "signal_id": "sig-slip"
    }
    
    response = test_client.post("/smart-orders", json=payload, headers={"X-Internal-API-Key": "test-key"})
    assert response.status_code == 400
    assert "Max Slippage Exceeded" in response.text

@patch("app.services.order_service.BrokerFactory")
@patch("app.services.order_service.decrypt_data")
@patch("app.utils.redis_client.get_redis_client")
def test_place_smart_order_macro_vix_halt(mock_redis_factory, mock_decrypt, mock_factory, test_client, override_price, global_cache_mock, mock_minimax_global):
    mock_cache = global_cache_mock
    mock_redis = AsyncMock()
    mock_redis_factory.return_value = mock_redis
    
    # Mock global kill switch
    mock_redis.get.side_effect = lambda k: "1" if k == "system:kill_switch" else None
    
    mock_adapter = MagicMock()
    mock_factory.get_adapter.return_value = mock_adapter
    mock_decrypt.return_value = {"api_key": "xyz"}
    setup_adapter_mocks(mock_adapter, price=2000.0)
    override_price.get_latest_price.return_value = (2000.0, None)
    
    account_id = str(uuid.uuid4())
    mock_cache.get_account.return_value = get_base_account_mock(account_id, fund_id="fund-vix", broker="cTrader")
    mock_cache.get_credentials.return_value = {"api_key": "xyz"}
    mock_cache.get_fund.return_value = get_base_fund_mock(fund_id="fund-vix")
    mock_cache.get_risk_filters.return_value = []
    
    payload = {
        "broker_account_id": account_id,
        "symbol": "XAU_USD",
        "direction": "BULLISH",
        "stop_loss": 1990.0,
        "generated_by": "TestStrategy",
        "signal_id": "sig-vix"
    }
    
    response = test_client.post("/smart-orders", json=payload, headers={"X-Internal-API-Key": "test-key"})
    assert response.status_code == 503 # Global Kill Switch returns 503
    assert "System is currently halted" in response.text
