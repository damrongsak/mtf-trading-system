import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.adapters.ctrader import CTraderOrderAdapter

@pytest.mark.asyncio
async def test_ctrader_amend_order():
    with patch("app.adapters.ctrader.CTraderConnectionManager") as mock_conn:
        adapter = CTraderOrderAdapter("id", "secret", "123", "token")
        adapter.client = AsyncMock()
        
        # Mock get_pending_orders to provide symbol for normalization
        # 1000 units = 0.01 lot for Gold (lotSize=10000)
        adapter.get_pending_orders = AsyncMock(return_value=[
            {"id": "555", "instrument": "XAUUSD", "units": 1000.0}
        ])
        
        # Mock Symbol Metadata
        mock_ms = MagicMock()
        mock_ms.details = {"symbolId": 93, "lotSize": 10000}
        
        with patch("app.adapters.ctrader.AsyncSessionLocal") as mock_db_session:
            mock_db = AsyncMock()
            mock_db_session.return_value.__aenter__.return_value = mock_db
            mock_result = MagicMock()
            mock_result.scalars.return_value.first.return_value = mock_ms
            mock_db.execute.return_value = mock_result
            
            # Amend: Change units to 2000 (0.02 lot) and price
            await adapter.amend_order(order_id="555", units=2000.0, price=2350.0)
            
            # Verify client call
            call_args = adapter.client.amend_order.call_args[1]
            assert call_args["order_id"] == 555
            # (2000 / 100000) * 10000 = 200 cents
            assert call_args["volume"] == 200
            assert call_args["price"] == 2350.0

@pytest.mark.asyncio
async def test_ctrader_amend_position():
    with patch("app.adapters.ctrader.CTraderConnectionManager") as mock_conn:
        adapter = CTraderOrderAdapter("id", "secret", "123", "token")
        adapter.client = AsyncMock()
        
        await adapter.amend_position(broker_trade_id="777", sl_price=2300.0, tp_price=2400.0)
        
        call_args = adapter.client.amend_position_sltp.call_args[1]
        assert call_args["position_id"] == 777
        assert call_args["sl"] == 2300.0
        assert call_args["tp"] == 2400.0
