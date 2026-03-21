import asyncio
import json
import uuid
import logging
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_vwap_execution():
    """
    Simulates the flow of a VWAP order and verifies volume-weighted slicing.
    """
    logger.info("📊 Starting Phase 13 Verification (VWAP Algorithm)...")

    # 1. Mock Request Data (Institutional VWAP Order)
    broker_acc_id = str(uuid.uuid4())
    order_req = {
        "broker_account_id": broker_acc_id,
        "symbol": "XAU_USD",
        "direction": "BULLISH",
        "units": 1000.0,
        "entry_price": 2300.0,
        "stop_loss": 2290.0,
        "take_profit": 2320.0,
        "execution_algo": "VWAP",
        "algo_params": {
            "duration": 60,
            "slices": 4 # U-shape profile will be applied
        },
        "generated_by": "SMC_H1_VWAP",
        "client_order_id": f"vwap_test_{uuid.uuid4().hex[:8]}"
    }

    # 2. Mock DB & Redis
    mock_db = MagicMock()
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    
    mock_redis = AsyncMock()
    
    mock_fund = MagicMock()
    mock_fund.id = uuid.uuid4()
    mock_fund.max_risk_per_trade = 1000.0
    mock_fund.risk_percentage = 1.0
    mock_fund.max_drawdown_threshold = 5.0
    mock_fund.scale_factor = 1.0
    mock_fund.asset_risk_caps = {}

    mock_account = MagicMock()
    mock_account.id = uuid.UUID(broker_acc_id)
    mock_account.fund_id = mock_fund.id
    mock_account.is_active = True
    mock_account.broker_name = "CTRADER"

    from app.models import BrokerAccount, Fund
    def mock_query(model):
        q = MagicMock()
        if model == BrokerAccount:
            q.filter.return_value.first.return_value = mock_account
        elif model == Fund:
            q.filter.return_value.first.return_value = mock_fund
        return q
    mock_db.query.side_effect = mock_query

    # Mock Services
    from app.services.order_service import OrderService, execution_cache
    OrderService._symbol_cache = {broker_acc_id: {"XAU_USD": {"lot_size": 100000.0}}}
    
    execution_cache.get_account = AsyncMock(return_value={
        "id": broker_acc_id, 
        "is_active": True,
        "broker_name": "CTRADER",
        "fund_id": str(mock_fund.id),
        "risk_settings": {}
    })
    execution_cache.get_credentials = AsyncMock(return_value="{}")
    execution_cache.get_fund = AsyncMock(return_value={
        "id": str(mock_fund.id), 
        "max_risk_per_trade": 1000.0, 
        "risk_percentage": 1.0, 
        "max_drawdown_threshold": 5.0,
        "scale_factor": 1.0,
        "asset_risk_caps": {}
    })
    execution_cache.get_risk_filters = AsyncMock(return_value=[])

    # 3. Patch Dependencies
    with patch("app.services.order_service.BrokerFactory.get_adapter") as mock_factory, \
         patch("app.services.order_service.UnitConverter") as mock_conv, \
         patch("app.algorithms.manager.get_redis_client", return_value=mock_redis), \
         patch("app.utils.redis_client.get_redis_client", return_value=mock_redis), \
         patch("app.algorithms.vwap.asyncio.create_task") as mock_task:
        
        mock_conv.calculate_size_from_risk.return_value = 1000.0
        mock_conv.calculate_risk_usd.return_value = 10.0
        
        mock_adapter = AsyncMock()
        mock_adapter.get_market_price.return_value = {"bid": 2300.0, "ask": 2300.1}
        mock_adapter._resolve_symbol_id_and_lot_size.return_value = ("1", 100000.0, 1, 2)
        mock_factory.return_value = mock_adapter

        # 4. Trigger Execution
        result = await OrderService.execute_smart_order(order_req, mock_db)
        logger.info(f"Execution Result Header: {result}")
        assert result["status"] == "ALGO_STARTED"
        assert result["algo"] == "VWAP"

        # Verify Parent Trade
        parent_trade = mock_db.add.call_args[0][0]
        parent_id = str(parent_trade.trade_id)

        # 5. Execute VwapAlgorithm manually
        from app.algorithms.vwap import VwapAlgorithm
        await VwapAlgorithm.execute(mock_redis, mock_db, parent_id, order_req)

        # Verify Slices (U-Shape: i=0 and i=num_slices-1 should be larger)
        priority_calls = [call for call in mock_redis.lpush.call_args_list if "queue:execution:priority" in call[0]]
        logger.info(f"Total slices processed/scheduled: {len(priority_calls) + mock_task.call_count}")
        assert len(priority_calls) == 1 # First slice immediate
        assert mock_task.call_count == 3 # Remaining scheduled
        
        # Analyze Weights from VwapAlgorithm._get_volume_profile
        weights = VwapAlgorithm._get_volume_profile(order_req["algo_params"]["slices"])
        logger.info(f"Applied Volume Weights: {weights}")
        
        # Verify U-Shape: first and last should be equal and larger than middle
        assert weights[0] == weights[-1]
        assert weights[0] > weights[1]
        assert weights[-1] > weights[2]
        assert sum(weights) == 1.0 or abs(sum(weights) - 1.0) < 0.0001
        
        logger.info("✅ Phase 13 Verification Passed: VWAP volume-weighted slicing correct.")

if __name__ == "__main__":
    asyncio.run(test_vwap_execution())
