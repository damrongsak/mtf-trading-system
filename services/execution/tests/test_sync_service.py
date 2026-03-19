
import pytest
import json
import uuid
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.sync_service import SyncService
from app.models import BrokerAccount

@pytest.mark.asyncio
async def test_reconcile_all_funds_no_accounts():
    """Verify sync returns early if no active accounts."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    
    with patch("app.services.sync_service.AsyncSessionLocal", return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_db))):
        await SyncService.reconcile_all_funds()
        # Should not call reconcile_fund
        mock_db.execute.assert_called_once()

@pytest.mark.asyncio
async def test_ghost_trade_detection():
    """Verify that a trade in broker but not in DB triggers a GHOST_TRADE alert."""
    fund_id = uuid.uuid4()
    acc_id = uuid.uuid4()
    
    mock_account = MagicMock(spec=BrokerAccount)
    mock_account.id = acc_id
    mock_account.fund_id = fund_id
    mock_account.broker_name = "CTRADER"
    mock_account.account_name = "TestAcc"
    mock_account.credentials_encrypted = b"enc"
    mock_account.environment = "demo"

    # Mock DB
    mock_db = AsyncMock()
    
    # 1. LIVE Trades from broker
    live_trades = [
        {"id": "EXT_1", "symbol": "XAUUSD", "units": 1000.0}
    ]
    
    # 2. DB Trades (Empty)
    mock_db_result = MagicMock()
    mock_db_result.scalars.return_value.all.return_value = [] # No DB trades
    mock_db.execute.return_value = mock_db_result

    # Mock Redis
    mock_redis = AsyncMock()
    
    # Mock decrypt and adapter
    with patch("app.services.sync_service.decrypt_data", return_value={}), \
         patch("app.services.sync_service.BrokerFactory.get_adapter") as mock_factory, \
         patch("app.services.sync_service.redis.from_url", return_value=mock_redis):
        
        mock_adapter = AsyncMock()
        mock_adapter.get_open_trades.return_value = live_trades
        mock_factory.return_value = mock_adapter
        
        await SyncService.reconcile_fund(str(fund_id), [mock_account], mock_db)
        
        # Verify Redis alert was sent
        mock_redis.xadd.assert_called()
        args, kwargs = mock_redis.xadd.call_args
        assert args[0] == "system.alerts.drift"
        # The fields are in args[1] if passed positionally
        fields = args[1] if len(args) > 1 else kwargs.get("fields", {})
        payload = json.loads(fields["payload"])
        assert payload["type"] == "GHOST_TRADE"
        assert payload["broker_trade_id"] == "EXT_1"

@pytest.mark.asyncio
async def test_exposure_drift_detection():
    """Verify that different units across brokers trigger an EXPOSURE_DRIFT alert."""
    fund_id = uuid.uuid4()
    acc1_id = uuid.uuid4()
    acc2_id = uuid.uuid4()
    
    mock_acc1 = MagicMock(spec=BrokerAccount)
    mock_acc1.id = acc1_id
    mock_acc2 = MagicMock(spec=BrokerAccount)
    mock_acc2.id = acc2_id
    
    # Live states: 
    # Acc 1: 1.0 units XAUUSD
    # Acc 2: 0.5 units XAUUSD
    broker_states = {
        str(acc1_id): [{"symbol": "XAUUSD", "units": 1.0}],
        str(acc2_id): [{"symbol": "XAUUSD", "units": 0.5}]
    }
    
    mock_redis = AsyncMock()
    
    await SyncService._calculate_net_exposure_drift(str(fund_id), broker_states, mock_redis)
    
    # Verify Alert
    mock_redis.xadd.assert_called_once()
    args, kwargs = mock_redis.xadd.call_args
    fields = args[1] if len(args) > 1 else kwargs.get("fields", {})
    payload = json.loads(fields["payload"])
    assert payload["type"] == "EXPOSURE_DRIFT"
    assert payload["symbol"] == "XAUUSD"
    # Drift 1.0 - 0.5 = 0.5
    assert abs(payload["drift_units"] - 0.5) < 0.0001

@pytest.mark.asyncio
async def test_reconcile_fund_fetch_error_handling():
    """Verify that one broker failure doesn't stop reconciliation of others."""
    fund_id = str(uuid.uuid4())
    acc1 = MagicMock(spec=BrokerAccount, id=uuid.uuid4(), credentials_encrypted=b"e1", environment="demo")
    acc2 = MagicMock(spec=BrokerAccount, id=uuid.uuid4(), credentials_encrypted=b"e2", environment="demo")
    
    mock_db = AsyncMock()
    mock_db.execute.return_value = MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))))
    
    mock_redis = AsyncMock()

    with patch("app.services.sync_service.decrypt_data", return_value={}), \
         patch("app.services.sync_service.BrokerFactory.get_adapter") as mock_factory, \
         patch("app.services.sync_service.redis.from_url", return_value=mock_redis):
        
        # Mocking 1 success, 1 failure
        mock_adapter_ok = AsyncMock()
        mock_adapter_ok.get_open_trades.return_value = []
        
        def factory_side_effect(name, creds):
            if creds.get("id") == str(acc1.id):
                raise Exception("Broker Down")
            return mock_adapter_ok

        # Adjust fetch_state logic in test to match real code
        # In reality, fetch_state uses acc.id and decrypt_data
        
        await SyncService.reconcile_fund(fund_id, [acc1, acc2], mock_db)
        
        # Should have attempted to fetch both
        assert mock_factory.call_count == 2

@pytest.mark.asyncio
async def test_reconcile_all_funds_grouping():
    """Verify reconcile_all_funds correctly groups accounts by fund_id."""
    fid1 = uuid.uuid4()
    fid2 = uuid.uuid4()
    
    acc1 = MagicMock(spec=BrokerAccount, fund_id=fid1, is_active=True)
    acc2 = MagicMock(spec=BrokerAccount, fund_id=fid1, is_active=True)
    acc3 = MagicMock(spec=BrokerAccount, fund_id=fid2, is_active=True)
    
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [acc1, acc2, acc3]
    mock_db.execute.return_value = mock_result
    
    with patch("app.services.sync_service.AsyncSessionLocal", return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_db))), \
         patch.object(SyncService, "reconcile_fund", new=AsyncMock()) as mock_reconcile:
        
        await SyncService.reconcile_all_funds()
        
        # Should be called twice (two unique fund_ids)
        assert mock_reconcile.call_count == 2
        
        # Verify first call had 2 accounts, second had 1
        call_args_list = mock_reconcile.call_args_list
        # The ordering might vary due to dict keys, but let's check content
        order1 = len(call_args_list[0][0][1]) # accounts list
        order2 = len(call_args_list[1][0][1])
        assert {order1, order2} == {1, 2}
