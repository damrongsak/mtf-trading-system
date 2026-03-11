import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock
import sys
import os

# Add current directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

async def test_drift_detection():
    print("Testing Cross-Broker Drift Detection...")
    
    from app.services.sync_service import SyncService
    
    # 1. Setup Mock Data
    oanda_trades = [
        {"instrument": "XAU_USD", "currentUnits": 1.0} # Long 1.0
    ]
    ctrader_trades = [
        {"symbol": "XAUUSD", "units": 0.5} # Long 0.5 -> Drift 0.5
    ]

    # 2. Patching
    with patch("redis.asyncio.from_url") as mock_redis_factory:
        mock_redis = AsyncMock()
        mock_redis_factory.return_value = mock_redis
        
        # 3. Execution (static method call)
        await SyncService._check_cross_broker_drift(oanda_trades, ctrader_trades)
        
        # 4. Assertions
        calls = mock_redis.xadd.call_args_list
        found_drift = False
        for call in calls:
            stream = call.args[0]
            payload_dict = call.args[1]
            if stream == "system.alerts.drift":
                payload = json.loads(payload_dict["payload"])
                if payload["type"] == "BROKER_DRIFT" and payload["symbol"] == "XAUUSD":
                    found_drift = True
                    print(f"✅ Success: Exposure Drift detected for {payload['symbol']}")
                    print(f"   Drift: {payload['drift']} units")
        
        if not found_drift:
            print("❌ Failure: Exposure Drift NOT detected.")
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_drift_detection())
