import pytest
import asyncio
from app.runner.live import LiveRunner

@pytest.mark.asyncio
async def test_live_runner_flow():
    from unittest.mock import AsyncMock, MagicMock, patch
    
    # Mock specific heavy dependencies for this test only
    mocks = {
        "vectorbt": MagicMock(),
        "pandas": MagicMock(),
        "app.streaming.subscriber": MagicMock(),
        "app.database": MagicMock()
    }
    
    with patch.dict("sys.modules", mocks):
        # Mock StrategyEngine
        mock_engine = AsyncMock()
        
        # Mock RedisSubscriber
        # We need to patch the class call inside LiveRunner
        with patch("app.runner.live.RedisSubscriber") as MockSubscriber:
            mock_sub_instance = AsyncMock()
            MockSubscriber.return_value = mock_sub_instance
            
            # Init Runner
            runner = LiveRunner(mock_engine)
            
            # Start
            await runner.start()
            
            # Verify subscription to pattern
            mock_sub_instance.psubscribe.assert_awaited_with(["market_data:*"])
            
            # Verify callback integration
            # Get the callback passed to constructor
            args, _ = MockSubscriber.call_args
            callback = args[0]
            
            # Simulate a tick data callback
            data = {"type": "PRICE", "instrument": "EUR_USD", "bid": 1.0, "ask": 1.0}
            await callback("market_data:EUR_USD", data)
            
            # Verify engine called
            mock_engine.on_tick.assert_awaited_with(data)
            
            # Stop
            await runner.stop()
            mock_sub_instance.stop.assert_awaited()
