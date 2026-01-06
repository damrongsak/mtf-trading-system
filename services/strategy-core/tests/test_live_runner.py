import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Mock database module before imports to avoid connection errors
sys.modules["app.database"] = MagicMock()
sys.modules["app.database"].SessionLocal = MagicMock()

# Mock other heavy modules
sys.modules["app.engine"] = MagicMock()
sys.modules["vectorbt"] = MagicMock()
sys.modules["pandas"] = MagicMock()
sys.modules["app.streaming.subscriber"] = MagicMock() # We patch it in test, but good to mock module just in case

import pytest
import asyncio
# from app.runner.live import LiveRunner 
# Importing LiveRunner will imply importing app.engine if not careful? 
# app.runner.live does: from app.engine import StrategyEngine
# Since app.engine is in sys.modules, it gets the Mock.
from app.runner.live import LiveRunner

@pytest.mark.asyncio
async def test_live_runner_flow():
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
