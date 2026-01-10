from typing import Dict, Any, Optional
from app.adapters.base import BrokerAdapter
from app.adapters.oanda_order import OandaOrderAdapter
from app.adapters.binance_adapter import BinanceAdapter

class BrokerFactory:
    """
    Factory to create broker adapters based on configuration.
    """
    
    @staticmethod
    def get_adapter(broker_name: str, credentials: Dict[str, Any]) -> BrokerAdapter:
        broker_name = broker_name.upper()
        
        if broker_name == "OANDA":
            return OandaOrderAdapter(
                api_key=credentials.get("api_key"),
                account_id=credentials.get("account_id"),
                environment=credentials.get("environment", "practice")
            )
        elif broker_name == "BINANCE":
            return BinanceAdapter(
                api_key=credentials.get("api_key"),
                secret_key=credentials.get("secret_key"),
                is_live=(credentials.get("environment") == "live")
            )
        elif broker_name == "MOCK":
            from app.adapters.mock_adapter import MockAdapter
            return MockAdapter()
            
        else:
            raise ValueError(f"Unsupported broker: {broker_name}")
