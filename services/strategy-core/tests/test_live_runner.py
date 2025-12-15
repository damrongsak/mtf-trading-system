import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Mock database module before imports to avoid connection errors
sys.modules["app.database"] = MagicMock()
sys.modules["app.database"].SessionLocal = MagicMock()

import pytest
import asyncio
from app.runner.live import LiveRunner

@pytest.mark.asyncio
async def test_live_runner_flow():
    # Mock StrategyEngine
    mock_engine = AsyncMock()
    
    # Mock PriceStreamer
    mock_queue = asyncio.Queue()
    mock_streamer = MagicMock()
    # subscribe is async, so we need AsyncMock
    mock_streamer.subscribe = AsyncMock(return_value=mock_queue)
    
    # Init Runner
    runner = LiveRunner(mock_engine, mock_streamer)
    
    # Start
    await runner.start()
    
    # Give the loop a chance to run
    await asyncio.sleep(0.1)
    
    # Verify subscription
    mock_streamer.start_streaming.assert_called()
    mock_streamer.subscribe.assert_called()
    
    # Push Data
    data = {"type": "PRICE", "instrument": "EUR_USD", "bid": 1.0, "ask": 1.0, "time": "2023-01-01"}
    await mock_queue.put(data)
    
    # Wait a bit for loop to process
    await asyncio.sleep(0.1)
    
    # Verify Forwarding
    mock_engine.on_tick.assert_called_with(data)
    
    # Stop
    await runner.stop()
    
    # Verify Unsubscription
    # unsubscribe is sync
    mock_streamer.unsubscribe.assert_called_with(mock_queue)
