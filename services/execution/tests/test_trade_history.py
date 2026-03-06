import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, AsyncMock
from app.adapters.oanda_order import OandaOrderAdapter
from app.adapters.ctrader import CTraderOrderAdapter
from app.models import TradeStatus, TradeDirection

@pytest.mark.asyncio
async def test_oanda_trade_history_normalization():
    adapter = OandaOrderAdapter(api_key="key", account_id="123")
    
    # Mock OANDA TradesList response
    mock_response = {
        "trades": [
            {
                "id": "1001",
                "instrument": "XAU_USD",
                "initialUnits": "1000",
                "price": "2000.0",
                "averageClosePrice": "2010.0",
                "realizedPL": "100.0",
                "openTime": "2024-03-05T10:00:00.000Z",
                "closeTime": "2024-03-05T12:00:00.000Z",
                "state": "CLOSED"
            }
        ]
    }
    
    with patch("oandapyV20.endpoints.trades.TradesList") as mock_list:
        mock_list.return_value.response = mock_response
        with patch("app.adapters.oanda_order.run_in_threadpool", AsyncMock()) as mock_run:
            start = datetime(2024, 3, 1, tzinfo=timezone.utc)
            end = datetime(2024, 3, 31, tzinfo=timezone.utc)
            
            history = await adapter.get_trade_history(start, end)
            
            assert len(history) == 1
            trade = history[0]
            assert trade["trade_id"] == "1001"
            # 1000 units / 100,000 = 0.01 Standard Lots
            assert trade["lot_size"] == 0.01
            assert trade["signal_timestamp"].tzinfo == timezone.utc
            assert trade["exit_timestamp"].tzinfo == timezone.utc
            assert trade["status"] == TradeStatus.CLOSED

@pytest.mark.asyncio
async def test_ctrader_trade_history_normalization():
    adapter = CTraderOrderAdapter(client_id="id", client_secret="secret", account_id="12345", token="token")
    
    # Mock cTrader Deal List response
    from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOADeal, ProtoOATradeSide, ProtoOAClosePositionDetail
    
    mock_deal = MagicMock()
    mock_deal.dealId = 5001
    mock_deal.symbolId = 1
    mock_deal.volume = 100000 # 1000 units in cents
    mock_deal.tradeSide = 2 # SELL (to close long)
    mock_deal.executionPrice = 2010.0
    mock_deal.createTimestamp = 1709632800000 # 2024-03-05 10:00:00 UTC
    mock_deal.executionTimestamp = 1709640000000 # 2024-03-05 12:00:00 UTC
    
    mock_detail = MagicMock()
    mock_detail.entryPrice = 2000.0
    mock_detail.grossProfit = 10000 # $100.00 in cents
    mock_deal.closePositionDetail = mock_detail
    
    adapter.client = AsyncMock()
    adapter.client.get_deal_list.return_value = [mock_deal]
    adapter._resolve_name_from_id_cache = MagicMock(return_value=("XAU_USD", 10000000))
    adapter._populate_symbol_cache = AsyncMock()

    start = datetime(2024, 3, 1, tzinfo=timezone.utc)
    end = datetime(2024, 3, 31, tzinfo=timezone.utc)
    
    history = await adapter.get_trade_history(start, end)
    
    assert len(history) == 1
    trade = history[0]
    assert trade["trade_id"] == "5001"
    # 1000 units (from 100000 cents) / 100,000 = 0.01 Standard Lots
    assert trade["lot_size"] == 0.01
    assert trade["pnl_usd"] == 100.0
    assert trade["signal_timestamp"].tzinfo == timezone.utc
    assert trade["exit_timestamp"].tzinfo == timezone.utc
