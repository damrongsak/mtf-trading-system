import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.analytics_service import AnalyticsService
from app.models import AccountHistory

@pytest.mark.asyncio
async def test_capture_all_account_snapshots():
    """
    Integration test for AnalyticsService capturing snapshots.
    """
    # 1. Mock DB Session and Broker Accounts
    mock_db = AsyncMock()
    mock_account = MagicMock()
    mock_account.id = "test-acc-id"
    mock_account.broker_name = "ctrader"
    mock_account.is_active = True
    
    # Mock Select Result
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [mock_account]
    
    # Use a non-Async mock for the result object
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars
    
    # But db.execute itself IS awaited, so it must return an awaitable.
    # We use AsyncMock for the session method.
    mock_db.execute = AsyncMock(return_value=mock_result)
    
    # 2. Mock Adapter and Account Summary
    mock_summary = {
        "balance": 10000.0,
        "equity": 10500.0,
        "used_margin": 500.0,
        "free_margin": 10000.0,
        "margin_level": 2100.0,
        "unrealized_gross": 500.0,
        "unrealized_net": 480.0
    }
    
    with patch("app.services.analytics_service.AsyncSessionLocal", return_value=mock_db), \
         patch("app.adapters.factory.BrokerFactory.get_adapter") as mock_factory:
        
        mock_adapter = AsyncMock()
        mock_adapter.get_account_summary.return_value = mock_summary
        mock_factory.return_value = mock_adapter
        
        # 3. Call Service
        await AnalyticsService.capture_all_account_snapshots()
        
        # 4. Verify DB Insert
        # In capture_all_account_snapshots, it adds a new AccountHistory object
        mock_db.add.assert_called()
        inserted_obj = mock_db.add.call_args[0][0]
        assert isinstance(inserted_obj, AccountHistory)
        assert inserted_obj.balance == 10000.0
        assert inserted_obj.unrealized_net == 480.0
        mock_db.commit.assert_called()
        print("✅ Account Snapshot Test Passed")
