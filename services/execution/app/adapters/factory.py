from typing import Dict, Any, Optional
from app.adapters.base import BrokerAdapter
from app.adapters.oanda_order import OandaOrderAdapter

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
        # Add other brokers here
        # elif broker_name == "BINANCE":
        #     return BinanceAdapter(...)
            
        else:
            raise ValueError(f"Unsupported broker: {broker_name}")
