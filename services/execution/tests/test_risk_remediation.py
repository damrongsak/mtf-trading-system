
import pytest
import uuid
import json
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime
from app.services.equity_guardian import EquityGuardian
from app.worker import FillTradeConsumer, CloseTradeConsumer
from app.models import BrokerAccount, Fund

@pytest.mark.asyncio
async def test_equity_guardian_percentage_drawdown():
    mock_redis = AsyncMock()
    guardian = EquityGuardian(mock_redis)
    
    account_id = str(uuid.uuid4())
    fund_id = uuid.uuid4()
    
    # Mock Metrics from _calculate_metrics
    # Case: Start balance 10,000. Total PnL +1,000. Peak relative +1,500. Max DD -300.
    # start_balance = 10,000 - 1,000 = 9,000
    # peak_absolute = 9,000 + 1,500 = 10,500
    # drawdown % = (300 / 10,500) * 100 = 2.857%
    
    metrics = {
        "total_pnl": 1000.0,
        "max_drawdown_usd": -300.0,
        "peak_relative_usd": 1500.0
    }
    
    mock_fund = Fund(
        id=fund_id,
        max_drawdown_threshold=3.0 # 3%
    )
    mock_account = BrokerAccount(
        id=uuid.UUID(account_id),
        fund_id=fund_id,
        balance_snapshot=10000.0
    )
    
    # Mock DB interaction
    with patch("app.services.equity_guardian.AsyncSessionLocal") as mock_session_factory:
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        
        mock_result = MagicMock()
        mock_result.first.return_value = (mock_fund, mock_account)
        mock_session.execute.return_value = mock_result
        
        # We need to mock _trigger_hard_stop to ensure it's NOT called for 2.85%
        with patch.object(guardian, "_trigger_hard_stop", AsyncMock()) as mock_stop:
            await guardian._check_risk_breach(account_id, metrics)
            mock_stop.assert_not_called()
            
            # Now trigger a breach: DD -500 -> (500 / 10,500) * 100 = 4.76%
            metrics["max_drawdown_usd"] = -500.0
            await guardian._check_risk_breach(account_id, metrics)
            mock_stop.assert_called_once()

@pytest.mark.asyncio
async def test_redis_stats_updates_fill():
    mock_redis = AsyncMock()
    consumer = FillTradeConsumer()
    consumer.redis = mock_redis
    
    account_id = uuid.uuid4()
    mock_account = BrokerAccount(id=account_id)
    
    # Mock process_fill internal logic to get past DB stuff
    with patch("app.worker.AsyncSessionLocal") as mock_session_factory, \
         patch("app.models.Trade"), \
         patch("app.models.SignalLog"), \
         patch("app.services.cache_service.execution_cache.get_order_context", AsyncMock(return_value={"symbol": "XAU_USD", "signal_id": "sig1"})):
        
        # Mock session execute to return account
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = mock_account
        mock_session.execute.return_value = mock_res
        
        # Mock scalar to return account first, then None for existing trade
        mock_session.scalar.side_effect = [mock_account, None]
        
        fields = {"data": json.dumps({
            "account_id": "123", 
            "order_id": "ord1", 
            "fill_volume": 1000, 
            "fill_price": 2000.0, 
            "instrument": "XAU_USD"
        })}
        
        with patch("app.worker.uuid.UUID", return_value=account_id), \
             patch("app.services.cache_service.execution_cache.get_broker_account_id_by_ctid", AsyncMock(return_value=str(account_id))):
            
            await consumer._process_fill("msg1", fields)
            
            # Check Redis incr call
            mock_redis.incr.assert_called_with(f"account_stats:trades_today:{account_id}")

@pytest.mark.asyncio
async def test_redis_stats_updates_close():
    mock_redis = AsyncMock()
    consumer = CloseTradeConsumer()
    consumer.redis = mock_redis
    
    account_id = str(uuid.uuid4())
    
    fields = {"data": json.dumps({
        "account_id": "123",
        "pnl": -150.0,
        "instrument": "XAU_USD"
    })}
    
    with patch("app.services.cache_service.execution_cache.get_broker_account_id_by_ctid", AsyncMock(return_value=account_id)), \
         patch("app.worker.AsyncSessionLocal") as mock_session_factory, \
         patch("sqlalchemy.select"):
        
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        
        await consumer._process_close("msg1", fields)
        
        # Check PnL update
        mock_redis.incrbyfloat.assert_called_with(f"account_stats:daily_pnl:{account_id}", -150.0)
        # Check Consecutive Losses (pnl < 0)
        mock_redis.incr.assert_called_with(f"account_stats:consecutive_losses:{account_id}")
        
        # Test recovery (pnl > 0)
        fields = {"data": json.dumps({"account_id": "123", "pnl": 50.0})}
        await consumer._process_close("msg2", fields)
        mock_redis.set.assert_called_with(f"account_stats:consecutive_losses:{account_id}", "0")
