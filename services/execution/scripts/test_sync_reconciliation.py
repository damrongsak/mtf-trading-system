import asyncio
import json
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock
import sys
import os

# Add current directory to path to allow imports from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

async def test_ghost_trade_detection():
    print("Testing Ghost Trade Detection...")
    
    # We delay imports until after path is set
    from app.services.sync_service import SyncService
    from app.models import BrokerAccount, Trade, TradeStatus

    # 1. Setup Mock Data
    account_id = uuid.uuid4()
    fund_id = uuid.uuid4()
    
    # Mock Account
    mock_account = MagicMock(spec=BrokerAccount)
    mock_account.id = account_id
    mock_account.fund_id = fund_id
    mock_account.broker_name = "CTRADER"
    mock_account.account_name = "Test Account"
    mock_account.is_active = True
    mock_account.credentials_encrypted = {"dummy": "data"}
    mock_account.environment = "demo"

    # Mock DB Session
    mock_db = AsyncMock()
    
    # Mock result for BrokerAccount query
    mock_acc_result = MagicMock()
    mock_acc_result.scalars.return_value.all.return_value = [mock_account]
    
    # Mock result for Trade query (returns empty list -> all broker trades are ghosts)
    mock_trade_result = MagicMock()
    mock_trade_result.scalars.return_value.all.return_value = []
    
    mock_db.execute.side_effect = [mock_acc_result, mock_trade_result]

    # Mock Adapter
    mock_adapter = AsyncMock()
    # Return one open trade from broker
    mock_adapter.get_open_trades.return_value = [
        {"id": "BRK_123", "symbol": "XAUUSD", "units": 100}
    ]

    # 2. Patching
    # Note: Using string path to patch where the import is used in sync_service.py
    with patch("app.services.sync_service.AsyncSessionLocal") as mock_session_factory:
        mock_session_factory.return_value.__aenter__.return_value = mock_db
        with patch("app.services.sync_service.BrokerFactory.get_adapter", return_value=mock_adapter):
            with patch("app.services.sync_service.decrypt_data", return_value={}):
                with patch("redis.asyncio.from_url") as mock_redis_factory:
                    mock_redis = AsyncMock()
                    mock_redis_factory.return_value = mock_redis
                    
                    # 3. Execution
                    await SyncService.reconcile_all_funds()
                    
                    # 4. Assertions
                    # Verify XADD was called for Ghost Trade
                    calls = mock_redis.xadd.call_args_list
                    found_ghost = False
                    for call in calls:
                        # xadd args: stream_name, fields_dict
                        stream = call.args[0]
                        payload_dict = call.args[1]
                        if stream == "system.alerts.drift":
                            payload = json.loads(payload_dict["payload"])
                            if payload["type"] == "GHOST_TRADE" and payload["broker_trade_id"] == "BRK_123":
                                found_ghost = True
                                print(f"✅ Success: Ghost Trade detected: {payload['broker_trade_id']}")
                                print(f"   Reason: {payload}")
                    
                    if not found_ghost:
                        print("❌ Failure: Ghost Trade NOT detected.")
                        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_ghost_trade_detection())
