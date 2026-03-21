import asyncio
import json
import uuid
import logging
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from decimal import Decimal

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_twap_execution():
    """
    Simulates the flow of a TWAP order from OrderService to AlgoManager to TwapAlgorithm.
    """
    logger.info("🚀 Starting Phase 12 Verification (TWAP Algorithm)...")

    # 1. Mock Request Data (Institutional TWAP Order)
    broker_acc_id = str(uuid.uuid4())
    order_req = {
        "broker_account_id": broker_acc_id,
        "symbol": "XAU_USD",
        "direction": "BULLISH",
        "units": 1000.0,
        "entry_price": 2300.0,
        "stop_loss": 2290.0,
        "take_profit": 2320.0,
        "execution_algo": "TWAP",
        "algo_params": {
            "duration": 60, # 60 seconds
            "slices": 4 # 4 slices
        },
        "generated_by": "SMC_H1_OB",
        "client_order_id": f"twap_test_{uuid.uuid4().hex[:8]}"
    }

    # 2. Mock DB & Redis
    mock_db = MagicMock() # Base as MagicMock to allow sync add
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock() # Awaited
    mock_db.refresh = AsyncMock() # Awaited
    mock_db.close = AsyncMock() # Awaited
    
    mock_redis = AsyncMock()
    
    # Mock Fund & BrokerAccount retrieval
    mock_fund = MagicMock()
    mock_fund.id = uuid.uuid4()
    mock_fund.risk_per_trade_percent = 1.0
    mock_fund.scale_factor = 1.0
    mock_fund.max_risk_per_trade = 100.0
    mock_fund.risk_percentage = 1.0
    mock_fund.max_drawdown_threshold = 5.0
    mock_fund.asset_risk_caps = {}

    mock_account = MagicMock()
    mock_account.id = uuid.UUID(broker_acc_id)
    mock_account.fund_id = mock_fund.id
    mock_account.broker_name = "CTRADER"
    mock_account.is_active = True

    # Mock DB Query Results
    from app.models import BrokerAccount, Fund
    def mock_query(model):
        q = MagicMock()
        if model == BrokerAccount:
            q.filter.return_value.first.return_value = mock_account
        elif model == Fund:
            q.filter.return_value.first.return_value = mock_fund
        else:
            q.filter.return_value.first.return_value = None
        return q

    mock_db.query.side_effect = mock_query

    # Mock Symbol Cache
    mock_symbol_details = {
        "symbol": "XAU_USD",
        "lot_size": 100000.0,
        "pipPosition": 1,
        "digits": 2,
        "minLot": 0.01,
        "maxLot": 100.0,
        "step_volume": 0.01
    }
    from app.services.order_service import OrderService
    OrderService._symbol_cache = {
        broker_acc_id: {
            "XAU_USD": mock_symbol_details
        }
    }

    # Monkey-patch execution_cache
    from app.services.order_service import execution_cache
    
    mock_account_cache = {
        "id": broker_acc_id,
        "fund_id": str(mock_fund.id),
        "is_active": True,
        "broker_name": "CTRADER",
        "encrypted_credentials": "{}",
        "risk_settings": {}
    }
    mock_fund_cache = {
        "id": str(mock_fund.id),
        "max_risk_per_trade": 100.0,
        "risk_percentage": 1.0,
        "max_drawdown_threshold": 5.0,
        "scale_factor": 1.0,
        "asset_risk_caps": {}
    }

    execution_cache.get_account = AsyncMock(return_value=mock_account_cache)
    execution_cache.get_credentials = AsyncMock(return_value="{}")
    execution_cache.get_fund = AsyncMock(return_value=mock_fund_cache)
    execution_cache.get_risk_filters = AsyncMock(return_value=[])

    # 3. Patch Dependencies
    with patch("app.services.order_service.BrokerFactory.get_adapter") as mock_factory, \
         patch("app.services.order_service.UnitConverter") as mock_conv, \
         patch("app.algorithms.manager.get_redis_client", return_value=mock_redis), \
         patch("app.utils.redis_client.get_redis_client", return_value=mock_redis), \
         patch("app.algorithms.twap.asyncio.create_task") as mock_task:
        
        mock_conv.calculate_size_from_risk.return_value = 1000.0
        mock_conv.calculate_risk_usd.return_value = 10.0
        
        mock_adapter = AsyncMock()
        mock_adapter.get_market_price.return_value = {"bid": 2300.0, "ask": 2300.1}
        mock_adapter._resolve_symbol_id_and_lot_size.return_value = ("1", 100000.0, 1, 2)
        mock_factory.return_value = mock_adapter

        # 4. Trigger Execution
        logger.info(f"Incoming Request: {order_req['execution_algo']} over {order_req['algo_params']['duration']}s")
        
        try:
            # OrderService.execute_smart_order takes AsyncSession, but we pass MagicMock for sync parts
            result = await OrderService.execute_smart_order(order_req, mock_db)
            logger.info(f"Verification Result: {result}")
        except Exception as e:
            logger.error(f"Execution Failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise e
        
        # 5. Assertions
        assert result["status"] == "ALGO_STARTED"
        assert result["algo"] == "TWAP"
        
        # Verify Parent Trade was saved
        assert mock_db.add.called
        parent_trade = mock_db.add.call_args[0][0]
        assert parent_trade.execution_algo == "TWAP"
        assert parent_trade.algo_status == "RUNNING"
        
        # Verify Redis command was sent to queue:execution:algo
        assert mock_redis.lpush.called
        algo_calls = [call for call in mock_redis.lpush.call_args_list if "queue:execution:algo" in call[0]]
        logger.info(f"Algo Queue Calls: {len(algo_calls)}")
        assert len(algo_calls) >= 1
        
        algo_cmd = json.loads(algo_calls[0][0][1])
        assert algo_cmd["type"] == "ALGO_START"
        assert algo_cmd["algo_name"] == "TWAP"
        
        # Verify TwapAlgorithm was triggered
        from app.algorithms.twap import TwapAlgorithm
        await TwapAlgorithm.execute(mock_redis, mock_db, parent_id=str(parent_trade.trade_id), req_data=order_req)
        
        # Verify Slices (1 immediate lpush, num_slices-1 scheduled tasks)
        priority_calls = [call for call in mock_redis.lpush.call_args_list if "queue:execution:priority" in call[0]]
        logger.info(f"Priority Queue Calls (Immediate Slices): {len(priority_calls)}")
        assert len(priority_calls) >= 1
        
        logger.info(f"Scheduled Slices (asyncio tasks): {mock_task.call_count}")
        assert mock_task.call_count == (order_req["algo_params"]["slices"] - 1)
        
        logger.info("✅ Phase 12 Verification Passed: TWAP sliced correctly.")

if __name__ == "__main__":
    asyncio.run(test_twap_execution())
