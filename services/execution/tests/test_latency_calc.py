import pytest
import time
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.order_service import OrderService
import uuid

@pytest.mark.asyncio
async def test_latency_calculation_with_ns_precision():
    # Mocking dependencies
    db = AsyncMock()
    
    # Current time in nanoseconds
    now_ns = time.time_ns()
    # 50ms ago
    signal_ts_ns = now_ns - (50 * 1_000_000)
    
    order_data = {
        "broker_account_id": str(uuid.uuid4()),
        "symbol": "XAU_USD",
        "direction": "BULLISH",
        "stop_loss": 2000.0,
        "risk_usd": 100.0,
        "generated_by": "TestStrategy",
        "signal_id": "sig-123",
        "signal_timestamp_ns": signal_ts_ns
    }
    
    with patch("app.services.order_service.execution_cache") as mock_cache, \
         patch("app.services.order_service.BrokerFactory") as mock_factory, \
         patch("app.services.order_service.decrypt_data") as mock_decrypt, \
         patch("app.services.order_service.MinimaxService") as mock_minimax, \
         patch("app.services.order_service.price_service") as mock_price, \
         patch("app.services.order_service.RiskLimitsAgent") as mock_risk_agent, \
         patch("app.utils.redis_client.get_redis_client") as mock_redis:
        
        # Setup cache mocks
        mock_cache.get_account.return_value = {
            "is_active": True,
            "broker_name": "OANDA",
            "credentials_encrypted": b"test",
            "environment": "practice",
            "fund_id": str(uuid.uuid4()),
            "risk_settings": {},
            "id": order_data["broker_account_id"]
        }
        mock_cache.get_credentials.return_value = {"api_key": "test"}
        mock_cache.get_fund.return_value = {
            "max_risk_per_trade": 1000.0,
            "risk_percentage": 0.01
        }
        mock_cache.get_risk_filters.return_value = []
        
        # Setup adapter mock
        mock_adapter = AsyncMock()
        mock_factory.get_adapter.return_value = mock_adapter
        mock_price.get_latest_price.return_value = (2010.0, None)
        mock_adapter.get_account_summary.return_value = {"NAV": "10000"}
        mock_adapter.place_market_order.return_value = {
            "orderFillTransaction": {"id": "fill_123", "time": "now"}
        }
        
        mock_minimax.calculate_regret.return_value = (True, 0.0, "OK")
        mock_risk_agent.check_order_size = AsyncMock(return_value=True)
        mock_risk_agent.check_limits = AsyncMock(return_value=True)
        mock_risk_agent.check_margin = AsyncMock(return_value=True)
        
        # Execute
        result = await OrderService.execute_smart_order(order_data, db)
        
        # Verify latency exists and is >= 50ms (since we said it started 50ms ago)
        # Note: the test itself adds some computation time, so it should be > 50ms.
        assert "latency_ms" in result
        assert result["latency_ms"] >= 50.0
        assert result["signal_timestamp_ns"] == signal_ts_ns
        print(f"Verified Latency: {result['latency_ms']}ms")
