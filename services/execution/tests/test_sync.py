
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.main import sync_trades, SyncTradesRequest
from app.models import BrokerAccount, Trade
import uuid
from datetime import datetime

@pytest.mark.asyncio
async def test_sync_trades_endpoint():
    # Mock DB
    mock_db = AsyncMock()
    
    # Mock Account
    account_id = uuid.uuid4()
    mock_account = BrokerAccount(
        id=account_id,
        broker_name="MOCK",
        credentials_encrypted={"data": "encrypted"},
        environment="practice",
        is_active=True,
        fund_id=uuid.uuid4()
    )
    
    # Mock Select Result
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_account
    mock_db.execute.return_value = mock_result
    mock_db.get.return_value = None # No existing trade
    
    # Mock Adapter
    with patch("app.main.BrokerFactory.get_adapter") as mock_factory, \
         patch("app.main.decrypt_data", return_value={"api_key": "123"}):
        
        mock_adapter = AsyncMock()
        mock_factory.return_value = mock_adapter
        
        # Mock History Return
        mock_adapter.get_trade_history.return_value = [
            {
                "trade_id": "EXT_123", # External string ID
                "symbol": "XAU_USD",
                "strategy_name": "Manual",
                "signal_timestamp": datetime.now(),
                "status": "CLOSED",
                "direction": "LONG",
                "entry_price": 2000.0,
                "exit_price": 2010.0,
                "lot_size": 1.0,
                "risk_usd": 10.0,
                "pnl_usd": 100.0,
                "exit_timestamp": datetime.now()
            }
        ]
        
        # Request
        req = SyncTradesRequest(broker_account_id=str(account_id), lookback_days=10)
        
        # Call
        response = await sync_trades(req=req, db=mock_db, authenticated="test")
        
        # Assertions
        assert response["status"] == "success"
        assert response["data"]["imported"] == 1
        assert response["data"]["total_fetched"] == 1
        
        # Verify DB Merge
        assert mock_db.merge.called
        args, _ = mock_db.merge.call_args
        added_trade = args[0]
        assert isinstance(added_trade, Trade)
        assert added_trade.symbol == "XAU_USD"
        assert added_trade.pnl_usd == 100.0
        
        # Verify Adapter Call
        assert mock_adapter.get_trade_history.called

