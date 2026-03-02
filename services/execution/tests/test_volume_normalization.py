import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.adapters.ctrader import CTraderOrderAdapter

@pytest.mark.asyncio
async def test_ctrader_volume_normalization_gold():
    # Setup adapter with mocks
    with patch("app.adapters.ctrader.CTraderConnectionManager") as mock_conn:
        adapter = CTraderOrderAdapter("id", "secret", "123", "token")
        adapter.client = AsyncMock()
        
        # Mock Symbol Metadata (Gold: lotSize = 10,000 cents = 100oz)
        mock_ms = MagicMock()
        mock_ms.details = {"symbolId": 93, "lotSize": 10000}
        
        with patch("app.adapters.ctrader.AsyncSessionLocal") as mock_db_session:
            mock_db = AsyncMock()
            mock_db_session.return_value.__aenter__.return_value = mock_db
            
            mock_result = MagicMock()
            mock_result.scalars.return_value.first.return_value = mock_ms
            mock_db.execute.return_value = mock_result
            
            # Test: 0.01 Lot of Gold = 1000 Universal Units
            # Expectation: 0.01 * 10,000 = 100 cents (1oz)
            units = 1000.0
            await adapter.place_market_order("XAUUSD", units)
            
            # Verify called volume
            call_args = adapter.client.create_order.call_args[1]
            assert call_args["volume"] == 100

@pytest.mark.asyncio
async def test_ctrader_volume_normalization_fx():
    with patch("app.adapters.ctrader.CTraderConnectionManager") as mock_conn:
        adapter = CTraderOrderAdapter("id", "secret", "123", "token")
        adapter.client = AsyncMock()
        
        # Mock Symbol Metadata (FX: lotSize = 10,000,000 cents = 100,000 units)
        mock_ms = MagicMock()
        mock_ms.details = {"symbolId": 1, "lotSize": 10000000}
        
        with patch("app.adapters.ctrader.AsyncSessionLocal") as mock_db_session:
            mock_db = AsyncMock()
            mock_db_session.return_value.__aenter__.return_value = mock_db
            
            mock_result = MagicMock()
            mock_result.scalars.return_value.first.return_value = mock_ms
            mock_db.execute.return_value = mock_result
            
            # Test: 0.01 Lot of FX = 1000 Universal Units
            # Expectation: 0.01 * 10,000,000 = 100,000 cents (1000 units)
            units = 1000.0
            await adapter.place_market_order("EURUSD", units)
            
            call_args = adapter.client.create_order.call_args[1]
            assert call_args["volume"] == 100000

@pytest.mark.asyncio
async def test_ctrader_reverse_normalization():
    # Test get_open_trades reverse normalization
    with patch("app.adapters.ctrader.CTraderConnectionManager") as mock_conn:
        adapter = CTraderOrderAdapter("id", "secret", "123", "token")
        adapter.client = AsyncMock()
        
        # Mock reconcile response
        mock_position = MagicMock()
        mock_position.symbolId = 93
        mock_position.volume = 100 # 1oz of Gold
        mock_position.positionId = 555
        
        mock_reconcile = MagicMock()
        mock_reconcile.position = [mock_position]
        adapter.client.get_reconcile.return_value = mock_reconcile
        
        # Mock DB symbol map
        mock_ms = MagicMock()
        mock_ms.details = {"symbolId": 93, "lotSize": 10000}
        mock_ms.symbol = "XAUUSD"
        
        with patch("app.adapters.ctrader.AsyncSessionLocal") as mock_db_session:
            mock_db = AsyncMock()
            mock_db_session.return_value.__aenter__.return_value = mock_db
            
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [mock_ms]
            mock_db.execute.return_value = mock_result
            
            trades = await adapter.get_open_trades()
            assert len(trades) == 1
            # 100 cents / 10,000 lotSize * 100,000 units = 1000 units
            assert trades[0]["units"] == 1000.0
