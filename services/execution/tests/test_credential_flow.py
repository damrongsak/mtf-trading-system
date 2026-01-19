import pytest
from unittest.mock import MagicMock
from app.adapters.factory import BrokerFactory
from app.adapters.oanda_order import OandaOrderAdapter
from app.adapters.ctrader import CTraderOrderAdapter

def test_oanda_credential_mapping():
    """
    Simulates extracting credentials from BrokerAccount (DB) 
    and passing them to BrokerFactory for OANDA.
    """
    # 1. Simulate DB Data
    db_credentials = {
        "api_key": "test_oanda_key",
        "account_id": "test_oanda_account",
        "environment": "practice"
    }
    
    # 2. Call Factory (mimicking main.py logic)
    adapter = BrokerFactory.get_adapter("OANDA", db_credentials)
    
    # 3. Verify Adapter Config
    assert isinstance(adapter, OandaOrderAdapter)
    # Check attributes of the client or adapter to verify values passed correctly
    # Note: OandaOrderAdapter initializes self.account_id
    assert adapter.account_id == "test_oanda_account"
    # The API client is private/internal, but we can assume if it didn't crash it worked,
    # or check accessible properties if any.

def test_ctrader_credential_mapping_legacy():
    """
    Simulates extracting credentials from BrokerAccount (DB) with legacy keys
    """
    db_credentials = {
        "app_id": "test_ct_id_legacy",
        "secret": "test_ct_secret_legacy",
        "account_id": "123456",
        "token": "test_ct_token_legacy",
        "host": "live.ctraderapi.com"
    }
    adapter = BrokerFactory.get_adapter("CTRADER", db_credentials)
    
    assert isinstance(adapter, CTraderOrderAdapter)
    assert adapter.client_id == "test_ct_id_legacy"
    assert adapter.client_secret == "test_ct_secret_legacy"
    assert adapter.host == "live.ctraderapi.com"

def test_ctrader_credential_mapping_new():
    """
    Simulates extracting credentials from BrokerAccount (DB) with new keys (client_id)
    """
    db_credentials = {
        "client_id": "test_ct_id_new",
        "client_secret": "test_ct_secret_new",
        "account_id": "12345",
        "token": "test_ct_token_new" # default demo host
    }
    
    adapter = BrokerFactory.get_adapter("CTRADER", db_credentials)
    
    assert isinstance(adapter, CTraderOrderAdapter)
    assert adapter.client_id == "test_ct_id_new"
    assert adapter.client_secret == "test_ct_secret_new"
    assert adapter.host == "demo.ctraderapi.com" # Default



def test_missing_credentials_validation():
    """
    Verify that the Adapter raises ValueError if keys are missing,
    checking the robustness of the logic.
    """
    # Missing 'secret' for cTrader
    incomplete_creds = {
        "app_id": "test_ct_id",
        # "secret": "MISSING",
        "account_id": "123",
        "token": "tok"
    }
    
    with pytest.raises(ValueError) as excinfo:
        BrokerFactory.get_adapter("CTRADER", incomplete_creds)
    
    assert "CTrader Adapter requires" in str(excinfo.value)
